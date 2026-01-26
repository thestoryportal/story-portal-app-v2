#!/usr/bin/env python3
"""
L05 Import Validation Script

Validates that all L05 services and adapters can be successfully imported.
This catches missing dependencies, circular imports, and syntax errors early.

Usage:
    python scripts/validate_imports.py
"""

import sys
import importlib
from pathlib import Path

# Add platform to path
PLATFORM_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PLATFORM_DIR))


def validate_imports():
    """Validate all L05 module imports."""

    errors = []
    warnings = []
    success = []

    # Core L05 modules to validate
    modules = [
        # Models
        ("src.L05_planning.models", "Core models (Goal, ExecutionPlan, Task)"),

        # Services
        ("src.L05_planning.services.planning_service", "PlanningService"),
        ("src.L05_planning.services.plan_cache", "PlanCache"),
        ("src.L05_planning.services.execution_monitor", "ExecutionMonitor"),
        ("src.L05_planning.services.dependency_resolver", "DependencyResolver"),
        ("src.L05_planning.services.plan_validator", "PlanValidator"),
        ("src.L05_planning.services.resource_estimator", "ResourceEstimator"),
        ("src.L05_planning.services.context_injector", "ContextInjector"),
        ("src.L05_planning.services.goal_decomposer", "GoalDecomposer"),
        ("src.L05_planning.services.task_orchestrator", "TaskOrchestrator"),

        # Adapters
        ("src.L05_planning.adapters", "CLI Plan Adapters"),
        ("src.L05_planning.adapters.cli_plan_adapter", "CLIPlanAdapter"),

        # Parsers
        ("src.L05_planning.parsers", "Plan Parsers"),
        ("src.L05_planning.parsers.multi_format_parser", "MultiFormatParser"),
        ("src.L05_planning.parsers.format_detector", "FormatDetector"),
    ]

    print("=" * 60)
    print("L05 Import Validation")
    print("=" * 60)
    print()

    for module_path, description in modules:
        try:
            module = importlib.import_module(module_path)
            success.append((module_path, description))
            print(f"  [OK] {module_path}")
            print(f"       {description}")
        except ImportError as e:
            errors.append((module_path, description, str(e)))
            print(f"  [FAIL] {module_path}")
            print(f"         {description}")
            print(f"         Error: {e}")
        except Exception as e:
            warnings.append((module_path, description, str(e)))
            print(f"  [WARN] {module_path}")
            print(f"         {description}")
            print(f"         Warning: {e}")
        print()

    # Validate critical classes exist
    print("-" * 60)
    print("Validating Critical Classes")
    print("-" * 60)
    print()

    critical_classes = [
        ("src.L05_planning.models", "Goal", "Goal model for plan creation"),
        ("src.L05_planning.models", "ExecutionPlan", "ExecutionPlan with to_dict/from_dict"),
        ("src.L05_planning.models", "Task", "Task model for execution"),
        ("src.L05_planning.services.planning_service", "PlanningService", "Main planning service"),
        ("src.L05_planning.adapters.cli_plan_adapter", "CLIPlanAdapter", "CLI plan adapter"),
        ("src.L05_planning.adapters", "CLIPlanModeHook", "CLI plan mode hook"),
    ]

    for module_path, class_name, description in critical_classes:
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            success.append((f"{module_path}.{class_name}", description))
            print(f"  [OK] {module_path}.{class_name}")
            print(f"       {description}")
        except AttributeError:
            errors.append((f"{module_path}.{class_name}", description, f"Class {class_name} not found"))
            print(f"  [FAIL] {module_path}.{class_name}")
            print(f"         Class not found in module")
        except Exception as e:
            errors.append((f"{module_path}.{class_name}", description, str(e)))
            print(f"  [FAIL] {module_path}.{class_name}")
            print(f"         Error: {e}")
        print()

    # Validate critical methods exist
    print("-" * 60)
    print("Validating Critical Methods")
    print("-" * 60)
    print()

    critical_methods = [
        ("src.L05_planning.services.planning_service", "PlanningService", "execute_plan_direct"),
        ("src.L05_planning.models", "ExecutionPlan", "to_dict"),
        ("src.L05_planning.models", "ExecutionPlan", "from_dict"),
        ("src.L05_planning.models", "Goal", "to_dict"),
        ("src.L05_planning.models", "Goal", "from_dict"),
    ]

    for module_path, class_name, method_name in critical_methods:
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            method = getattr(cls, method_name)
            success.append((f"{class_name}.{method_name}", f"Method {method_name} on {class_name}"))
            print(f"  [OK] {class_name}.{method_name}")
        except AttributeError:
            errors.append((f"{class_name}.{method_name}", f"Method not found", ""))
            print(f"  [FAIL] {class_name}.{method_name}")
            print(f"         Method not found on class")
        except Exception as e:
            errors.append((f"{class_name}.{method_name}", str(e), ""))
            print(f"  [FAIL] {class_name}.{method_name}")
            print(f"         Error: {e}")
        print()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print()
    print(f"  Passed: {len(success)}")
    print(f"  Warnings: {len(warnings)}")
    print(f"  Errors: {len(errors)}")
    print()

    if errors:
        print("VALIDATION FAILED")
        print()
        print("Errors:")
        for item, desc, err in errors:
            print(f"  - {item}: {err}")
        return 1

    if warnings:
        print("VALIDATION PASSED WITH WARNINGS")
        return 0

    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(validate_imports())
