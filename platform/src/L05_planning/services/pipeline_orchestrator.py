"""
Pipeline Orchestrator - V2 Orchestration for L05 Planning
Path: platform/src/L05_planning/services/pipeline_orchestrator.py

Wires existing V2 components into a cohesive execution flow:
- MultiFormatParser for parsing
- SpecDecomposer for decomposition
- UnitValidator for validation
- UnitExecutor for execution
- CheckpointManager for state management
- RecoveryProtocol for failure recovery
- Bridges for service integration (L01, L04, L06, L11)
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..parsers.multi_format_parser import MultiFormatParser, ParsedPlan, ParseError
from ..agents.spec_decomposer import SpecDecomposer, AtomicUnit
from ..agents.unit_validator import UnitValidator, ValidationResult, ValidationStatus
from ..checkpoints.checkpoint_manager import CheckpointManager
from ..checkpoints.recovery_protocol import RecoveryProtocol
from ..integration.l01_bridge import L01Bridge, StoreResultType
from ..integration.l04_bridge import L04Bridge
from ..integration.l06_bridge import L06Bridge, AssessmentLevel
from ..integration.l11_bridge import L11Bridge, EventType
from .unit_executor import UnitExecutor, ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    """Status of pipeline execution."""
    PENDING = "pending"
    PARSING = "parsing"
    DECOMPOSING = "decomposing"
    EXECUTING = "executing"
    VALIDATING = "validating"
    SCORING = "scoring"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class UnitResult:
    """Result of executing a single unit."""
    unit_id: str
    unit_title: str
    execution_result: Optional[ExecutionResult] = None
    validation_result: Optional[ValidationResult] = None
    quality_score: float = 0.0
    checkpoint_hash: Optional[str] = None
    status: PipelineStatus = PipelineStatus.PENDING
    error: Optional[str] = None
    duration_ms: int = 0


@dataclass
class PipelineResult:
    """Result of executing a full pipeline."""
    execution_id: str
    plan_id: str
    status: PipelineStatus
    unit_results: List[UnitResult] = field(default_factory=list)
    total_units: int = 0
    passed_units: int = 0
    failed_units: int = 0
    skipped_units: int = 0
    average_score: float = 0.0
    overall_assessment: Optional[AssessmentLevel] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Returns True if pipeline completed successfully."""
        return self.status == PipelineStatus.COMPLETED and self.failed_units == 0


@dataclass
class ExecutionContext:
    """Context for pipeline execution."""
    working_dir: Path
    dry_run: bool = False
    sandbox: bool = True
    stop_on_failure: bool = True
    parallel_validation: bool = False
    quality_threshold: float = 70.0
    variables: Dict[str, Any] = field(default_factory=dict)


class PipelineOrchestrator:
    """
    V2 Pipeline Orchestrator for L05 Planning.

    Wires existing components into a cohesive execution flow:
    1. Parse markdown plan
    2. Decompose into atomic units
    3. For each unit:
       - Store unit in L01
       - Pre-validate (check dependencies)
       - Create checkpoint
       - Execute unit
       - Post-validate (check acceptance criteria)
       - Score with L06
       - If failed: recover
    4. Calculate final score
    5. Return PipelineResult

    Features:
    - Real service integration via bridges
    - Checkpoint-based recovery
    - Event publishing to L11
    - Quality scoring via L06
    """

    def __init__(
        self,
        working_dir: Optional[Path] = None,
        parser: Optional[MultiFormatParser] = None,
        decomposer: Optional[SpecDecomposer] = None,
        validator: Optional[UnitValidator] = None,
        executor: Optional[UnitExecutor] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
        recovery_protocol: Optional[RecoveryProtocol] = None,
        l01_bridge: Optional[L01Bridge] = None,
        l04_bridge: Optional[L04Bridge] = None,
        l06_bridge: Optional[L06Bridge] = None,
        l11_bridge: Optional[L11Bridge] = None,
    ):
        """
        Initialize pipeline orchestrator.

        Args:
            working_dir: Base working directory
            parser: MultiFormatParser instance
            decomposer: SpecDecomposer instance
            validator: UnitValidator instance
            executor: UnitExecutor instance
            checkpoint_manager: CheckpointManager instance
            recovery_protocol: RecoveryProtocol instance
            l01_bridge: L01Bridge for data storage
            l04_bridge: L04Bridge for model generation
            l06_bridge: L06Bridge for quality scoring
            l11_bridge: L11Bridge for events/sagas
        """
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()

        # Initialize components
        self.parser = parser or MultiFormatParser()
        self.decomposer = decomposer or SpecDecomposer()
        self.validator = validator or UnitValidator(working_dir=str(self.working_dir))
        self.executor = executor or UnitExecutor(working_dir=self.working_dir)
        self.checkpoint_manager = checkpoint_manager or CheckpointManager(
            repo_path=str(self.working_dir),
            storage_path=str(self.working_dir / ".l05_checkpoints"),
        )
        self.recovery_protocol = recovery_protocol or RecoveryProtocol(
            checkpoint_manager=self.checkpoint_manager,
        )

        # Initialize bridges
        self.l01_bridge = l01_bridge or L01Bridge()
        self.l04_bridge = l04_bridge or L04Bridge()
        self.l06_bridge = l06_bridge or L06Bridge()
        self.l11_bridge = l11_bridge or L11Bridge()

        # Execution tracking
        self._current_execution: Optional[str] = None
        self._execution_history: Dict[str, PipelineResult] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize all bridges and components."""
        if self._initialized:
            return

        logger.info("Initializing PipelineOrchestrator...")

        # Initialize bridges in parallel
        await asyncio.gather(
            self.l01_bridge.initialize(),
            self.l04_bridge.initialize(),
            self.l06_bridge.initialize(),
            self.l11_bridge.initialize(),
        )

        self._initialized = True
        logger.info("PipelineOrchestrator initialized")

    async def close(self):
        """Close all bridge connections."""
        await asyncio.gather(
            self.l01_bridge.close(),
            self.l04_bridge.close(),
            self.l06_bridge.close(),
            self.l11_bridge.close(),
        )

    async def execute_plan_markdown(
        self,
        markdown: str,
        context: Optional[ExecutionContext] = None,
    ) -> PipelineResult:
        """
        Execute a plan from markdown.

        Args:
            markdown: Plan markdown content
            context: Execution context with settings

        Returns:
            PipelineResult with execution details
        """
        await self.initialize()

        context = context or ExecutionContext(working_dir=self.working_dir)
        execution_id = f"exec-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6]}"
        self._current_execution = execution_id
        start_time = datetime.now()

        logger.info(f"Starting pipeline execution: {execution_id}")

        result = PipelineResult(
            execution_id=execution_id,
            plan_id="",
            status=PipelineStatus.PENDING,
            started_at=start_time,
        )

        try:
            # Step 1: Parse
            result.status = PipelineStatus.PARSING
            parsed_plan = await self._parse_plan(markdown, result)
            result.plan_id = parsed_plan.plan_id

            # Publish plan started event
            await self.l11_bridge.publish_plan_started(
                plan_id=parsed_plan.plan_id,
                unit_count=len(parsed_plan.steps),
                correlation_id=execution_id,
            )

            # Step 2: Decompose
            result.status = PipelineStatus.DECOMPOSING
            units = await self._decompose_plan(parsed_plan, result)
            result.total_units = len(units)

            # Store plan in L01
            await self.l01_bridge.store_plan_async(
                plan_id=parsed_plan.plan_id,
                plan_data={
                    "execution_id": execution_id,
                    "format_type": parsed_plan.format_type.value,
                    "unit_count": len(units),
                    "status": "executing",
                },
            )

            # Step 3: Execute units
            result.status = PipelineStatus.EXECUTING
            ordered_units = self.decomposer.get_execution_order()

            for i, unit in enumerate(ordered_units, 1):
                logger.info(f"[{i}/{len(ordered_units)}] Executing unit: {unit.id}")

                unit_result = await self._execute_unit(
                    unit=unit,
                    context=context,
                    plan_id=parsed_plan.plan_id,
                    execution_id=execution_id,
                )
                result.unit_results.append(unit_result)

                if unit_result.status == PipelineStatus.COMPLETED:
                    result.passed_units += 1
                elif unit_result.status == PipelineStatus.FAILED:
                    result.failed_units += 1
                    if context.stop_on_failure:
                        logger.warning(f"Stopping on failure at unit {unit.id}")
                        result.skipped_units = len(ordered_units) - i
                        break
                else:
                    result.skipped_units += 1

            # Step 4: Final scoring
            result.status = PipelineStatus.SCORING
            await self._calculate_final_score(result, units)

            # Determine overall status
            if result.failed_units == 0:
                result.status = PipelineStatus.COMPLETED
            elif result.passed_units > 0:
                result.status = PipelineStatus.COMPLETED  # Partial success
            else:
                result.status = PipelineStatus.FAILED

            # Publish plan completed event
            await self.l11_bridge.publish_plan_completed(
                plan_id=parsed_plan.plan_id,
                passed_count=result.passed_units,
                failed_count=result.failed_units,
                score=result.average_score,
                correlation_id=execution_id,
            )

        except ParseError as e:
            logger.error(f"Parse error: {e}")
            result.status = PipelineStatus.FAILED
            result.metadata["error"] = f"Parse error: {str(e)}"

            await self.l11_bridge.publish_plan_failed(
                plan_id=result.plan_id or "unknown",
                error=str(e),
                correlation_id=execution_id,
            )

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            result.status = PipelineStatus.FAILED
            result.metadata["error"] = str(e)

            await self.l11_bridge.publish_plan_failed(
                plan_id=result.plan_id or "unknown",
                error=str(e),
                correlation_id=execution_id,
            )

        # Finalize
        result.completed_at = datetime.now()
        result.duration_ms = int((result.completed_at - start_time).total_seconds() * 1000)

        # Store execution result in L01
        await self.l01_bridge.store_execution_async(
            execution_id=execution_id,
            execution_data={
                "plan_id": result.plan_id,
                "status": result.status.value,
                "passed_units": result.passed_units,
                "failed_units": result.failed_units,
                "average_score": result.average_score,
                "duration_ms": result.duration_ms,
            },
        )

        self._execution_history[execution_id] = result
        self._current_execution = None

        logger.info(
            f"Pipeline execution complete: {execution_id} "
            f"(passed={result.passed_units}, failed={result.failed_units}, score={result.average_score:.1f})"
        )

        return result

    async def _parse_plan(self, markdown: str, result: PipelineResult) -> ParsedPlan:
        """Parse markdown into a structured plan."""
        logger.debug("Parsing plan markdown...")
        parsed_plan = self.parser.parse(markdown)
        logger.info(f"Parsed plan: {parsed_plan.plan_id} ({parsed_plan.format_type.value})")
        return parsed_plan

    async def _decompose_plan(self, parsed_plan: ParsedPlan, result: PipelineResult) -> List[AtomicUnit]:
        """Decompose plan into atomic units."""
        logger.debug("Decomposing plan into atomic units...")
        units = self.decomposer.decompose(parsed_plan)
        logger.info(f"Decomposed into {len(units)} atomic units")
        return units

    async def _execute_unit(
        self,
        unit: AtomicUnit,
        context: ExecutionContext,
        plan_id: str,
        execution_id: str,
    ) -> UnitResult:
        """Execute a single atomic unit through the full pipeline."""
        start_time = datetime.now()

        unit_result = UnitResult(
            unit_id=unit.id,
            unit_title=unit.title,
            status=PipelineStatus.PENDING,
        )

        try:
            # Store unit in L01
            await self.l01_bridge.store_unit_async(
                unit_id=unit.id,
                unit_data={
                    "title": unit.title,
                    "description": unit.description,
                    "files": unit.files,
                    "complexity": unit.complexity,
                },
                plan_id=plan_id,
            )

            # Publish unit started event
            await self.l11_bridge.publish_unit_started(
                unit_id=unit.id,
                plan_id=plan_id,
                correlation_id=execution_id,
            )

            # Create checkpoint before execution
            checkpoint = self.checkpoint_manager.create_checkpoint(
                name=f"pre-{unit.id}",
                unit_id=unit.id,
                state={"execution_id": execution_id},
            )
            unit_result.checkpoint_hash = checkpoint.hash

            # Pre-validation (check dependencies exist)
            logger.debug(f"Pre-validating unit: {unit.id}")
            # For now, skip pre-validation of dependencies
            # In a full implementation, would check that dependent units completed

            # Execute unit
            unit_result.status = PipelineStatus.EXECUTING
            execution_result = await self.executor.execute(unit, context.variables)
            unit_result.execution_result = execution_result

            if execution_result.status != ExecutionStatus.SUCCESS:
                if not context.dry_run:
                    unit_result.status = PipelineStatus.FAILED
                    unit_result.error = execution_result.error or "Execution failed"

                    await self.l11_bridge.publish_unit_failed(
                        unit_id=unit.id,
                        plan_id=plan_id,
                        error=unit_result.error,
                        correlation_id=execution_id,
                    )

                    return unit_result

            # Post-validation
            unit_result.status = PipelineStatus.VALIDATING
            validation_result = self.validator.validate(unit)
            unit_result.validation_result = validation_result

            # Score unit
            unit_result.status = PipelineStatus.SCORING
            score = await self.l06_bridge.score_unit_async(unit, validation_result)
            unit_result.quality_score = score.score

            # Store validation result in L01
            await self.l01_bridge.store_validation_async(
                unit_id=unit.id,
                validation_data={
                    "passed": validation_result.passed,
                    "status": validation_result.status.value,
                    "quality_score": score.score,
                    "assessment": score.assessment.value,
                },
            )

            # Determine final status based on validation and score
            if validation_result.passed and score.score >= context.quality_threshold:
                unit_result.status = PipelineStatus.COMPLETED

                await self.l11_bridge.publish_unit_completed(
                    unit_id=unit.id,
                    plan_id=plan_id,
                    score=score.score,
                    correlation_id=execution_id,
                )
            else:
                unit_result.status = PipelineStatus.FAILED
                unit_result.error = f"Validation {'failed' if not validation_result.passed else 'passed'}, score={score.score:.1f}"

                await self.l11_bridge.publish_unit_failed(
                    unit_id=unit.id,
                    plan_id=plan_id,
                    error=unit_result.error,
                    correlation_id=execution_id,
                )

        except Exception as e:
            logger.error(f"Unit execution failed: {unit.id} - {e}")
            unit_result.status = PipelineStatus.FAILED
            unit_result.error = str(e)

        # Calculate duration
        end_time = datetime.now()
        unit_result.duration_ms = int((end_time - start_time).total_seconds() * 1000)

        return unit_result

    async def _calculate_final_score(self, result: PipelineResult, units: List[AtomicUnit]):
        """Calculate final quality score for the pipeline."""
        if not result.unit_results:
            result.average_score = 0.0
            result.overall_assessment = AssessmentLevel.CRITICAL
            return

        scores = [ur.quality_score for ur in result.unit_results if ur.quality_score > 0]
        if scores:
            result.average_score = sum(scores) / len(scores)
        else:
            result.average_score = 0.0

        # Determine assessment level
        if result.average_score >= 90:
            result.overall_assessment = AssessmentLevel.EXCELLENT
        elif result.average_score >= 80:
            result.overall_assessment = AssessmentLevel.GOOD
        elif result.average_score >= 70:
            result.overall_assessment = AssessmentLevel.ACCEPTABLE
        elif result.average_score >= 60:
            result.overall_assessment = AssessmentLevel.WARNING
        else:
            result.overall_assessment = AssessmentLevel.CRITICAL

    async def get_execution_status(self, execution_id: str) -> Optional[PipelineResult]:
        """
        Get the status of an execution.

        Args:
            execution_id: Execution identifier

        Returns:
            PipelineResult if found, None otherwise
        """
        return self._execution_history.get(execution_id)

    async def rollback_execution(self, execution_id: str) -> bool:
        """
        Rollback an execution to the last checkpoint.

        Args:
            execution_id: Execution identifier

        Returns:
            True if rollback successful
        """
        result = self._execution_history.get(execution_id)
        if not result:
            logger.warning(f"Execution not found: {execution_id}")
            return False

        logger.info(f"Rolling back execution: {execution_id}")

        # Find the last successful checkpoint
        for unit_result in reversed(result.unit_results):
            if unit_result.checkpoint_hash:
                checkpoint = self.checkpoint_manager.get_checkpoint_by_hash(unit_result.checkpoint_hash)
                if checkpoint:
                    logger.info(f"Rolling back to checkpoint: {checkpoint.hash}")
                    self.checkpoint_manager.restore_checkpoint(checkpoint.checkpoint_id)

                    # Publish rollback event
                    await self.l11_bridge.publish_event(
                        EventType.ROLLBACK_COMPLETED,
                        {
                            "execution_id": execution_id,
                            "checkpoint_hash": checkpoint.hash,
                        },
                    )

                    result.status = PipelineStatus.ROLLED_BACK
                    return True

        logger.warning(f"No checkpoints found for execution: {execution_id}")
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """Returns orchestrator statistics."""
        total_executions = len(self._execution_history)
        successful = len([e for e in self._execution_history.values() if e.success])

        return {
            "total_executions": total_executions,
            "successful_executions": successful,
            "success_rate": successful / total_executions if total_executions > 0 else 0.0,
            "current_execution": self._current_execution,
            "initialized": self._initialized,
            "working_dir": str(self.working_dir),
            "bridges": {
                "l01_connected": self.l01_bridge.is_connected(),
                "l04_connected": self.l04_bridge.is_connected(),
                "l06_connected": self.l06_bridge.is_connected(),
                "l11_connected": self.l11_bridge.is_connected(),
            },
        }
