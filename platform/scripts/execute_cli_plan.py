#!/usr/bin/env python3
"""
Execute CLI Plan via L05 Planning Stack.

Usage:
    python scripts/execute_cli_plan.py --plan-file <path> [--dry-run]
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from L05_planning.adapters.cli_plan_adapter import CLIPlanAdapter
from L05_planning.services.planning_service import PlanningService
from L05_planning.services.goal_decomposer import GoalDecomposer


async def main():
    parser = argparse.ArgumentParser(description="Execute CLI plan via L05")
    parser.add_argument("--plan-file", required=True, help="Path to plan markdown file")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only, don't execute")
    parser.add_argument("--output", help="Output file for results (JSON)")
    args = parser.parse_args()

    # Read plan file
    plan_path = Path(args.plan_file).expanduser()
    if not plan_path.exists():
        print(f"Error: Plan file not found: {plan_path}", file=sys.stderr)
        sys.exit(1)

    plan_markdown = plan_path.read_text()
    print(f"Loaded plan from: {plan_path}")
    print(f"Plan size: {len(plan_markdown)} characters")

    # Initialize services
    try:
        goal_decomposer = GoalDecomposer()
        planning_service = PlanningService()
        adapter = CLIPlanAdapter(
            goal_decomposer=goal_decomposer,
            planning_service=planning_service,
            enrich_with_decomposer=True,
        )
        print("L05 services initialized")
    except Exception as e:
        print(f"Warning: Could not initialize full L05 stack: {e}")
        print("Running in parse-only mode...")
        adapter = CLIPlanAdapter()

    # Parse and analyze
    print("\n--- Parsing Plan ---")
    parsed = adapter.parse_plan_markdown(plan_markdown)
    print(f"Goal: {parsed.goal}")
    print(f"Steps: {len(parsed.steps)}")
    print(f"Session ID: {parsed.session_id}")

    # Show steps
    print("\n--- Steps ---")
    for i, step in enumerate(parsed.steps, 1):
        print(f"  {i}. {step.title}")
        if step.file_targets:
            print(f"     Files: {', '.join(step.file_targets[:3])}{'...' if len(step.file_targets) > 3 else ''}")
        if step.dependencies:
            print(f"     Depends: {', '.join(step.dependencies)}")

    # Analyze
    print("\n--- Analysis ---")
    execution_plan = adapter.to_execution_plan(parsed)
    analysis = adapter.analyze_plan(parsed, execution_plan)

    print(f"Total steps: {analysis['total_steps']}")
    print(f"Parallel phases: {analysis['parallel_phases']}")
    print(f"Estimated speedup: {analysis['estimated_speedup']:.1f}x")
    print(f"Capabilities required: {', '.join(analysis['inferred_capabilities'])}")

    # Build result
    result = {
        "status": "parsed",
        "goal": parsed.goal,
        "session_id": parsed.session_id,
        "analysis": analysis,
        "steps": [s.to_dict() for s in parsed.steps],
        "plan": execution_plan.to_dict() if execution_plan else None,
    }

    if args.dry_run:
        print("\n--- Dry Run Complete ---")
        result["status"] = "dry_run"
    else:
        print("\n--- Execution ---")
        if adapter.planning_service:
            try:
                exec_result = await adapter.execute(plan_markdown, dry_run=False)
                result["status"] = "executed"
                result["execution_result"] = exec_result
                print("Plan submitted to L05 for execution")
            except Exception as e:
                print(f"Execution error: {e}")
                result["status"] = "error"
                result["error"] = str(e)
        else:
            print("PlanningService not available - plan parsed but not executed")
            result["status"] = "parsed_only"

    # Output results
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(result, indent=2, default=str))
        print(f"\nResults written to: {output_path}")
    else:
        print("\n--- Result Summary ---")
        print(json.dumps({k: v for k, v in result.items() if k != "steps"}, indent=2, default=str))

    return result


if __name__ == "__main__":
    asyncio.run(main())
