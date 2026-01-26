#!/usr/bin/env python3
"""
L05 Catalog Validation Script

Compares Python L05 services to the MCP service catalog to ensure
all services and methods are properly exposed.

Usage:
    python scripts/validate_catalog.py
"""

import sys
import json
import inspect
import importlib
from pathlib import Path

# Add platform to path
PLATFORM_DIR = Path(__file__).parent.parent
PROJECT_DIR = PLATFORM_DIR.parent / "my-project"
sys.path.insert(0, str(PLATFORM_DIR))


def load_catalog():
    """Load the MCP service catalog."""
    catalog_path = PROJECT_DIR / "L12_nl_interface" / "data" / "service_catalog.json"

    if not catalog_path.exists():
        print(f"ERROR: Catalog not found at {catalog_path}")
        return None

    with open(catalog_path) as f:
        return json.load(f)


def get_python_services():
    """Get actual Python service classes and their methods."""

    services = {}

    service_modules = [
        ("PlanningService", "src.L05_planning.services.planning_service", "PlanningService"),
        ("PlanCache", "src.L05_planning.services.plan_cache", "PlanCache"),
        ("ExecutionMonitor", "src.L05_planning.services.execution_monitor", "ExecutionMonitor"),
        ("DependencyResolver", "src.L05_planning.services.dependency_resolver", "DependencyResolver"),
        ("PlanValidator", "src.L05_planning.services.plan_validator", "PlanValidator"),
        ("ResourceEstimator", "src.L05_planning.services.resource_estimator", "ResourceEstimator"),
        ("ContextInjector", "src.L05_planning.services.context_injector", "ContextInjector"),
        ("GoalDecomposer", "src.L05_planning.services.goal_decomposer", "GoalDecomposer"),
        ("TaskOrchestrator", "src.L05_planning.services.task_orchestrator", "TaskOrchestrator"),
    ]

    for service_name, module_path, class_name in service_modules:
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)

            # Get public methods (not starting with _)
            methods = []
            for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
                if not name.startswith('_'):
                    methods.append({
                        'name': name,
                        'is_async': inspect.iscoroutinefunction(method),
                    })

            # Also check for async methods via __dict__
            for name in dir(cls):
                if not name.startswith('_'):
                    attr = getattr(cls, name, None)
                    if attr and inspect.iscoroutinefunction(attr):
                        if not any(m['name'] == name for m in methods):
                            methods.append({
                                'name': name,
                                'is_async': True,
                            })

            services[service_name] = {
                'module_path': module_path,
                'class_name': class_name,
                'methods': methods,
            }
        except Exception as e:
            print(f"WARNING: Could not load {service_name}: {e}")

    return services


def validate_catalog():
    """Validate catalog against Python services."""

    print("=" * 60)
    print("L05 Catalog Validation")
    print("=" * 60)
    print()

    # Load catalog
    catalog = load_catalog()
    if not catalog:
        return 1

    print(f"Catalog version: {catalog.get('version', 'unknown')}")
    print()

    # Get Python services
    python_services = get_python_services()

    # Get catalog L05 services
    catalog_services = {
        s['service_name']: s
        for s in catalog.get('services', [])
        if s.get('layer') == 'L05'
    }

    errors = []
    warnings = []

    # Check required L05 services are in catalog
    print("-" * 60)
    print("Service Presence Check")
    print("-" * 60)
    print()

    required_services = {
        'PlanningService',
        'PlanCache',
        'ExecutionMonitor',
        'DependencyResolver',
        'PlanValidator',
        'ResourceEstimator',
        'ContextInjector',
    }

    for service_name in required_services:
        if service_name in catalog_services:
            print(f"  [OK] {service_name} in catalog")
        else:
            errors.append(f"Required service {service_name} missing from catalog")
            print(f"  [FAIL] {service_name} NOT in catalog")
    print()

    # Check critical methods
    print("-" * 60)
    print("Critical Method Check")
    print("-" * 60)
    print()

    critical_methods = {
        'PlanningService': ['create_plan', 'execute_plan', 'execute_plan_direct'],
        'PlanCache': ['store', 'retrieve', 'invalidate'],
        'ExecutionMonitor': ['start_monitoring', 'stop_monitoring', 'get_status'],
        'DependencyResolver': ['resolve', 'get_ready_tasks'],
        'PlanValidator': ['validate'],
        'ResourceEstimator': ['estimate'],
        'ContextInjector': ['inject'],
    }

    for service_name, methods in critical_methods.items():
        if service_name not in catalog_services:
            continue

        catalog_methods = {m['name'] for m in catalog_services[service_name].get('methods', [])}

        for method_name in methods:
            if method_name in catalog_methods:
                print(f"  [OK] {service_name}.{method_name}")
            else:
                errors.append(f"{service_name}.{method_name} missing from catalog")
                print(f"  [FAIL] {service_name}.{method_name} NOT in catalog")
    print()

    # Check execute_plan_direct specifically (critical for E5002 fix)
    print("-" * 60)
    print("E5002 Fix Validation (execute_plan_direct)")
    print("-" * 60)
    print()

    if 'PlanningService' in catalog_services:
        catalog_methods = {m['name'] for m in catalog_services['PlanningService'].get('methods', [])}

        if 'execute_plan_direct' in catalog_methods:
            print("  [OK] execute_plan_direct is in catalog")

            # Check method signature
            method_def = next(
                (m for m in catalog_services['PlanningService']['methods']
                 if m['name'] == 'execute_plan_direct'),
                None
            )

            if method_def:
                params = {p['name'] for p in method_def.get('parameters', [])}
                if 'execution_plan' in params:
                    print("  [OK] execute_plan_direct has execution_plan parameter")
                else:
                    errors.append("execute_plan_direct missing execution_plan parameter")
                    print("  [FAIL] execute_plan_direct missing execution_plan parameter")

                if method_def.get('async_method'):
                    print("  [OK] execute_plan_direct is marked async")
                else:
                    warnings.append("execute_plan_direct should be async")
                    print("  [WARN] execute_plan_direct should be marked async")
        else:
            errors.append("CRITICAL: execute_plan_direct missing from PlanningService")
            print("  [FAIL] CRITICAL: execute_plan_direct NOT in catalog")
    else:
        errors.append("CRITICAL: PlanningService missing from catalog")
        print("  [FAIL] CRITICAL: PlanningService NOT in catalog")
    print()

    # Check Python service methods are exposed
    print("-" * 60)
    print("Python-to-Catalog Method Coverage")
    print("-" * 60)
    print()

    for service_name, service_info in python_services.items():
        if service_name not in catalog_services:
            continue

        catalog_methods = {m['name'] for m in catalog_services[service_name].get('methods', [])}
        python_methods = {m['name'] for m in service_info['methods']}

        # Methods in Python but not catalog (potential gaps)
        missing_in_catalog = python_methods - catalog_methods - {'__init__', 'get_stats'}

        if missing_in_catalog:
            for method in missing_in_catalog:
                warnings.append(f"{service_name}.{method} in Python but not catalog")
            print(f"  [INFO] {service_name}: {len(missing_in_catalog)} methods not exposed")
            print(f"         {', '.join(sorted(missing_in_catalog))}")
        else:
            print(f"  [OK] {service_name}: all public methods exposed")
    print()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print()
    print(f"  L05 Services in catalog: {len(catalog_services)}")
    print(f"  Errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")
    print()

    if errors:
        print("VALIDATION FAILED")
        print()
        print("Errors:")
        for err in errors:
            print(f"  - {err}")
        return 1

    if warnings:
        print("VALIDATION PASSED WITH WARNINGS")
        print()
        print("Warnings:")
        for warn in warnings:
            print(f"  - {warn}")
        return 0

    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(validate_catalog())
