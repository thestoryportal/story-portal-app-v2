#!/usr/bin/env python3
"""
V2 Pipeline Runner - Bootstrapping Script
Manually orchestrates existing V2 components to execute the L05 enhancement plan.
Path: platform/src/L05_planning/scripts/run_v2_pipeline.py
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from L05_planning.parsers.multi_format_parser import MultiFormatParser, ParseError
from L05_planning.agents.spec_decomposer import SpecDecomposer, AtomicUnit
from L05_planning.agents.unit_validator import UnitValidator, ValidationStatus
from L05_planning.checkpoints.checkpoint_manager import CheckpointManager
from L05_planning.integration.l01_bridge import L01Bridge, StoreResultType
from L05_planning.integration.l06_bridge import L06Bridge


class V2PipelineRunner:
    """
    Manual orchestration of V2 components.
    This is the bootstrap implementation before PipelineOrchestrator exists.
    """

    def __init__(self, working_dir: Path):
        self.working_dir = working_dir
        self.parser = MultiFormatParser()
        self.decomposer = SpecDecomposer()
        self.validator = UnitValidator(working_dir=str(working_dir))
        self.checkpoint_manager = CheckpointManager(
            repo_path=str(working_dir),
            storage_path=str(working_dir / ".l05_checkpoints")
        )
        self.l01_bridge = L01Bridge()
        self.l06_bridge = L06Bridge()

        self.execution_id = f"exec-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.results = []

    async def run(self, plan_markdown: str) -> dict:
        """Execute plan through V2 pipeline."""
        print(f"\n{'='*60}")
        print(f"V2 PIPELINE EXECUTION: {self.execution_id}")
        print(f"{'='*60}\n")

        # Step 1: Parse
        print("STEP 1: Parsing plan markdown...")
        try:
            parsed_plan = self.parser.parse(plan_markdown)
            print(f"  ✓ Detected format: {parsed_plan.format_type.value}")
            print(f"  ✓ Extracted {len(parsed_plan.steps)} steps")
        except ParseError as e:
            print(f"  ✗ Parse failed: {e}")
            return {"success": False, "error": str(e), "stage": "parse"}

        # Store parsed plan
        self.l01_bridge.store_plan(
            plan_id=parsed_plan.plan_id,
            plan_data={
                "format_type": parsed_plan.format_type.value,
                "step_count": len(parsed_plan.steps),
                "execution_id": self.execution_id,
            }
        )

        # Step 2: Decompose
        print("\nSTEP 2: Decomposing into atomic units...")
        units = self.decomposer.decompose(parsed_plan)
        print(f"  ✓ Created {len(units)} atomic units")

        for unit in units:
            print(f"    - {unit.id}: {unit.title} [{unit.complexity}]")
            self.l01_bridge.store_unit(
                unit_id=unit.id,
                unit_data={
                    "title": unit.title,
                    "description": unit.description,
                    "files": unit.files,
                    "complexity": unit.complexity,
                    "acceptance_criteria": [c.description for c in unit.acceptance_criteria],
                },
                plan_id=parsed_plan.plan_id
            )

        # Step 3: Get execution order
        print("\nSTEP 3: Computing execution order...")
        ordered_units = self.decomposer.get_execution_order()
        print(f"  ✓ Execution order determined")

        # Step 4: Execute each unit
        print("\nSTEP 4: Executing units...")
        total_units = len(ordered_units)
        passed_units = 0
        failed_units = 0

        for i, unit in enumerate(ordered_units, 1):
            print(f"\n  [{i}/{total_units}] Unit: {unit.id}")
            print(f"      Title: {unit.title}")

            # Create checkpoint before execution
            checkpoint = self.checkpoint_manager.create_checkpoint(
                name=f"pre-{unit.id}",
                unit_id=unit.id,
                state={"unit_index": i, "total": total_units}
            )
            print(f"      ✓ Checkpoint: {checkpoint.hash}")

            # Pre-validate (check dependencies exist)
            print(f"      → Pre-validating...")

            # Execute unit (placeholder - actual execution will be done by Claude)
            print(f"      → Executing... (requires implementation)")

            # Post-validate using acceptance criteria
            print(f"      → Post-validating...")
            validation_result = self.validator.validate(unit)

            if validation_result.passed:
                passed_units += 1
                print(f"      ✓ PASSED ({len(validation_result.passed_criteria)}/{len(unit.acceptance_criteria)} criteria)")
            else:
                failed_units += 1
                print(f"      ✗ FAILED ({len(validation_result.failed_criteria)} criteria failed)")
                for failed in validation_result.failed_criteria:
                    print(f"        - {failed.criterion_id}: {failed.error or failed.output}")

            # Score unit
            score = self.l06_bridge.score_unit(unit, validation_result)
            print(f"      → Quality score: {score.score:.1f}/100 [{score.assessment.value}]")

            # Store validation result
            self.l01_bridge.store_validation(
                unit_id=unit.id,
                validation_data={
                    "passed": validation_result.passed,
                    "status": validation_result.status.value,
                    "quality_score": score.score,
                    "assessment": score.assessment.value,
                }
            )

            self.results.append({
                "unit_id": unit.id,
                "passed": validation_result.passed,
                "score": score.score,
            })

        # Step 5: Final summary
        print(f"\n{'='*60}")
        print("EXECUTION SUMMARY")
        print(f"{'='*60}")
        print(f"  Total units: {total_units}")
        print(f"  Passed: {passed_units}")
        print(f"  Failed: {failed_units}")

        avg_score = sum(r["score"] for r in self.results) / len(self.results) if self.results else 0
        print(f"  Average quality score: {avg_score:.1f}/100")

        success = failed_units == 0
        print(f"\n  Overall: {'SUCCESS ✓' if success else 'NEEDS ATTENTION ⚠'}")

        return {
            "success": success,
            "execution_id": self.execution_id,
            "total_units": total_units,
            "passed_units": passed_units,
            "failed_units": failed_units,
            "average_score": avg_score,
            "results": self.results,
        }


async def main():
    """Main entry point."""
    # Load plan from file
    plan_path = Path(__file__).parent.parent.parent.parent.parent.parent / ".claude/plans/starry-hugging-quail.md"

    if not plan_path.exists():
        print(f"Plan file not found: {plan_path}")
        return

    plan_markdown = plan_path.read_text()

    # Determine working directory (project root)
    working_dir = Path(__file__).parent.parent.parent.parent.parent

    # Run pipeline
    runner = V2PipelineRunner(working_dir)
    result = await runner.run(plan_markdown)

    # Output JSON result
    print(f"\n{'='*60}")
    print("JSON RESULT:")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
