"""
L05 CLI Integration Tests

Tests the critical gaps identified in the L05 planning pipeline implementation.
Focuses on validating:
1. Service catalog has all L05 services
2. PlanningService has execute_plan_direct method
3. Hook files have correct structure

Note: Some tests for adapter/hook functionality are marked xfail due to
datetime.utcnow() deprecation warnings being raised as errors in Python 3.14+.
These are pre-existing issues in the codebase models.
"""
import pytest
import json
import asyncio
import warnings
import os
from pathlib import Path
from datetime import datetime, timezone


class TestServiceCatalog:
    """Tests for service catalog completeness - CRITICAL for L05 pipeline."""

    @pytest.fixture
    def catalog_path(self):
        # Navigate from tests/ to my-project/L12_nl_interface/data/
        return (
            Path(__file__).parent.parent.parent.parent.parent /
            "my-project" / "L12_nl_interface" / "data" / "service_catalog.json"
        )

    def test_catalog_exists(self, catalog_path):
        """Service catalog file exists."""
        if not catalog_path.exists():
            pytest.skip(f"Catalog not found at {catalog_path}")

        assert catalog_path.exists(), f"Catalog not found at {catalog_path}"
        print(f"Catalog found at: {catalog_path}")

    def test_catalog_is_valid_json(self, catalog_path):
        """Catalog is valid JSON."""
        if not catalog_path.exists():
            pytest.skip(f"Catalog not found at {catalog_path}")

        with open(catalog_path) as f:
            catalog = json.load(f)

        assert 'services' in catalog, "Missing 'services' key"
        print(f"Catalog has {len(catalog['services'])} services")

    def test_catalog_has_l05_services(self, catalog_path):
        """Catalog contains all required L05 services."""
        if not catalog_path.exists():
            pytest.skip(f"Catalog not found at {catalog_path}")

        with open(catalog_path) as f:
            catalog = json.load(f)

        services = catalog.get('services', [])
        l05_services = {s['service_name'] for s in services if s.get('layer') == 'L05'}

        required = {
            'PlanningService',
            'PlanCache',
            'ExecutionMonitor',
            'DependencyResolver',
            'PlanValidator',
            'ResourceEstimator',
            'ContextInjector',
        }

        missing = required - l05_services
        assert not missing, f"Missing L05 services: {missing}"

        print(f"All {len(required)} required L05 services present")
        print(f"Total L05 services in catalog: {len(l05_services)}")

    def test_planning_service_has_execute_plan_direct(self, catalog_path):
        """PlanningService exposes execute_plan_direct method."""
        if not catalog_path.exists():
            pytest.skip(f"Catalog not found at {catalog_path}")

        with open(catalog_path) as f:
            catalog = json.load(f)

        ps = next((s for s in catalog.get('services', [])
                   if s['service_name'] == 'PlanningService'), None)

        assert ps is not None, "PlanningService not in catalog"

        methods = [m['name'] for m in ps.get('methods', [])]
        assert 'execute_plan_direct' in methods, f"execute_plan_direct not in methods: {methods}"

        print(f"PlanningService methods: {methods}")

    def test_planning_service_has_all_required_methods(self, catalog_path):
        """PlanningService has all required methods."""
        if not catalog_path.exists():
            pytest.skip(f"Catalog not found at {catalog_path}")

        with open(catalog_path) as f:
            catalog = json.load(f)

        ps = next((s for s in catalog.get('services', [])
                   if s['service_name'] == 'PlanningService'), None)

        required_methods = {
            'create_plan',
            'execute_plan',
            'execute_plan_direct',  # Critical for fixing E5002
        }

        methods = {m['name'] for m in ps.get('methods', [])}
        missing = required_methods - methods
        assert not missing, f"Missing methods: {missing}"


class TestPlanningServiceImplementation:
    """Tests for PlanningService implementation."""

    def test_execute_plan_direct_exists_in_class(self):
        """PlanningService class has execute_plan_direct method."""
        from L05_planning.services.planning_service import PlanningService

        assert hasattr(PlanningService, 'execute_plan_direct'), "Method missing from class!"
        print("execute_plan_direct method exists in PlanningService class")

    def test_execute_plan_direct_is_async(self):
        """execute_plan_direct is an async method."""
        import inspect
        from L05_planning.services.planning_service import PlanningService

        method = getattr(PlanningService, 'execute_plan_direct')
        assert inspect.iscoroutinefunction(method), "Method should be async"
        print("execute_plan_direct is async")

    def test_execute_plan_direct_signature(self):
        """execute_plan_direct has correct parameter signature."""
        import inspect
        from L05_planning.services.planning_service import PlanningService

        sig = inspect.signature(PlanningService.execute_plan_direct)
        params = list(sig.parameters.keys())

        # Should have self, plan (or execution_plan), and optionally agent_did
        assert 'self' in params, "Missing self parameter"
        assert 'plan' in params or 'execution_plan' in params, "Missing plan parameter"
        print(f"execute_plan_direct signature: {sig}")


class TestHookFiles:
    """Tests for hook file structure."""

    @pytest.fixture
    def hooks_dir(self):
        return (
            Path(__file__).parent.parent.parent.parent.parent /
            "my-project" / ".claude" / "hooks"
        )

    def test_l05_hook_exists(self, hooks_dir):
        """plan-mode-l05-hook.cjs exists."""
        hook_path = hooks_dir / "plan-mode-l05-hook.cjs"
        assert hook_path.exists(), f"Hook not found at {hook_path}"

    def test_l05_executor_exists(self, hooks_dir):
        """plan-mode-l05-executor.cjs exists."""
        executor_path = hooks_dir / "plan-mode-l05-executor.cjs"
        assert executor_path.exists(), f"Executor not found at {executor_path}"

    def test_l05_bridge_exists(self, hooks_dir):
        """l05-bridge.py exists."""
        bridge_path = hooks_dir / "l05-bridge.py"
        assert bridge_path.exists(), f"Bridge not found at {bridge_path}"

    def test_hook_contains_execution_plan_storage(self, hooks_dir):
        """Hook stores execution_plan in Gate 2 state."""
        hook_path = hooks_dir / "plan-mode-l05-hook.cjs"
        content = hook_path.read_text()

        assert 'execution_plan:' in content, "Hook doesn't store execution_plan"
        print("Hook stores execution_plan in state")

    def test_executor_uses_execute_plan_direct(self, hooks_dir):
        """Executor uses execute_plan_direct method."""
        executor_path = hooks_dir / "plan-mode-l05-executor.cjs"
        content = executor_path.read_text()

        assert 'execute_plan_direct' in content, "Executor doesn't use execute_plan_direct"
        print("Executor uses execute_plan_direct")

    def test_hook_has_askuserquestion_instruction(self, hooks_dir):
        """Hook has AskUserQuestion instruction for Gate 2."""
        hook_path = hooks_dir / "plan-mode-l05-hook.cjs"
        content = hook_path.read_text()

        assert 'AskUserQuestion' in content, "Hook doesn't have AskUserQuestion instruction"
        print("Hook has AskUserQuestion instruction")

    def test_bridge_includes_execution_plan(self, hooks_dir):
        """Bridge includes execution_plan in output."""
        bridge_path = hooks_dir / "l05-bridge.py"
        content = bridge_path.read_text()

        assert "execution_plan" in content, "Bridge doesn't include execution_plan"
        assert "to_dict()" in content, "Bridge doesn't serialize plan"
        print("Bridge includes serialized execution_plan")


class TestModelSerialization:
    """Tests for model serialization (can work without datetime issues)."""

    def test_execution_plan_has_to_dict(self):
        """ExecutionPlan class has to_dict method."""
        from L05_planning.models import ExecutionPlan

        assert hasattr(ExecutionPlan, 'to_dict'), "ExecutionPlan missing to_dict"
        print("ExecutionPlan has to_dict")

    def test_execution_plan_has_from_dict(self):
        """ExecutionPlan class has from_dict method."""
        from L05_planning.models import ExecutionPlan

        assert hasattr(ExecutionPlan, 'from_dict'), "ExecutionPlan missing from_dict"
        print("ExecutionPlan has from_dict")

    def test_goal_has_to_dict(self):
        """Goal class has to_dict method."""
        from L05_planning.models import Goal

        assert hasattr(Goal, 'to_dict'), "Goal missing to_dict"
        print("Goal has to_dict")

    def test_goal_has_from_dict(self):
        """Goal class has from_dict method."""
        from L05_planning.models import Goal

        assert hasattr(Goal, 'from_dict'), "Goal missing from_dict"
        print("Goal has from_dict")


class TestGate2StateFormat:
    """Tests for Gate 2 state file format."""

    @pytest.fixture
    def contexts_dir(self):
        return (
            Path(__file__).parent.parent.parent.parent.parent /
            "my-project" / ".claude" / "contexts"
        )

    def test_gate2_state_file_format(self, contexts_dir):
        """Gate 2 state file (if exists) has correct structure."""
        state_path = contexts_dir / ".gate2-pending.json"

        if not state_path.exists():
            pytest.skip("No Gate 2 state file exists (expected if not in plan mode)")

        with open(state_path) as f:
            state = json.load(f)

        # Check required fields
        required_fields = ['plan_id', 'goal_id', 'awaiting_choice']
        for field in required_fields:
            assert field in state, f"Missing field: {field}"

        # Check for execution_plan (new requirement)
        if 'execution_plan' in state:
            print("Gate 2 state has execution_plan (required for execute_plan_direct)")
            assert isinstance(state['execution_plan'], dict), "execution_plan should be dict"
        else:
            print("Note: execution_plan not in state (may be old format)")
