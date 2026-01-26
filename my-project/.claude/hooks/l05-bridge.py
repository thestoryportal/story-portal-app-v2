#!/usr/bin/env python3
"""
L05 Plan Mode Bridge Script

Invoked by the plan-mode-l05-hook.cjs to process approved plans
and return Gate 2 options.

CRITICAL: This bridge now returns the FULL serialized ExecutionPlan and Goal
objects to enable execute_plan_direct() to work without cache lookup.

Usage:
    python3 l05-bridge.py <plan_file_path> <platform_dir>
"""

import sys
import json
import os

def main():
    if len(sys.argv) < 3:
        print(json.dumps({
            'success': False,
            'error': 'Usage: l05-bridge.py <plan_file_path> <platform_dir>'
        }))
        sys.exit(1)

    plan_path = sys.argv[1]
    platform_dir = sys.argv[2]

    # Add platform to path
    sys.path.insert(0, platform_dir)

    try:
        from src.L05_planning.adapters import CLIPlanAdapter, CLIPlanModeHook

        # Read plan file
        with open(plan_path, 'r') as f:
            plan_markdown = f.read()

        # Initialize adapter
        adapter = CLIPlanAdapter()
        hook = CLIPlanModeHook(adapter)

        # Process plan
        response = hook.on_plan_approved(plan_markdown)

        # CRITICAL: Serialize full ExecutionPlan and Goal for execute_plan_direct
        # This ensures the full plan survives the Gate 2 boundary
        execution_plan_dict = response.execution_plan.to_dict()
        goal_dict = response.goal.to_dict()

        # Build result with FULL plan objects
        result = {
            'success': True,
            'goal': response.parsed_plan.goal,
            'total_steps': response.analysis.total_steps,
            'parallel_phases': response.analysis.parallel_phases,
            'estimated_speedup': response.analysis.estimated_speedup,
            'capabilities': response.analysis.inferred_capabilities,
            'recommended': response.recommended_choice.value,
            'options': [
                {
                    'id': opt.id.value,
                    'label': opt.label,
                    'description': opt.description
                }
                for opt in response.options
            ],
            'prompt': hook.format_gate2_prompt(response),
            'plan_id': response.execution_plan.plan_id,
            'goal_id': response.goal.goal_id,

            # CRITICAL: Full serialized objects for execute_plan_direct
            'execution_plan': execution_plan_dict,
            'goal_object': goal_dict,

            # Also store the plan markdown path for fallback
            'plan_markdown_path': plan_path,
        }

        print(json.dumps(result))

    except Exception as e:
        import traceback
        print(json.dumps({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
