"""L07 Learning Layer - Training Data Extractor Service.

Extracts training examples from execution traces, planning traces, and quality signals.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from ..models.training_example import TrainingExample, ExampleSource, DatasetStatistics
from ..models.error_codes import (
    LearningErrorCode,
    TrainingDataExtractionError
)

logger = logging.getLogger(__name__)


class TrainingDataExtractor:
    """Extract training examples from execution traces.

    This service parses execution events from L02, planning traces from L05,
    and quality scores from L06 to create structured training examples suitable
    for fine-tuning.
    """

    def __init__(
        self,
        min_quality_score: float = 0.0,
        min_confidence: float = 0.0,
        max_workers: int = 8
    ):
        """Initialize Training Data Extractor.

        Args:
            min_quality_score: Minimum quality score to extract (0-100)
            min_confidence: Minimum confidence to extract (0-1)
            max_workers: Maximum parallel extraction workers
        """
        self.min_quality_score = min_quality_score
        self.min_confidence = min_confidence
        self.max_workers = max_workers
        self.extraction_count = 0
        self.error_count = 0

        logger.info(
            f"Initialized TrainingDataExtractor: "
            f"min_quality={min_quality_score}, "
            f"min_confidence={min_confidence}"
        )

    async def extract_from_event(
        self,
        event: Dict[str, Any]
    ) -> Optional[TrainingExample]:
        """Extract training example from a single CloudEvent.

        Args:
            event: CloudEvent dictionary from L01 event stream

        Returns:
            TrainingExample if successful, None if failed or filtered

        Raises:
            TrainingDataExtractionError: If extraction fails critically
        """
        try:
            event_type = event.get('type', '')

            if event_type == 'execution.completed':
                return await self._extract_from_execution(event)
            elif event_type == 'planning.completed':
                return await self._extract_from_planning(event)
            elif event_type == 'evaluation.completed':
                # Quality scores are joined with execution traces
                return None
            else:
                logger.debug(f"Skipping event type: {event_type}")
                return None

        except Exception as e:
            self.error_count += 1
            logger.error(f"Failed to extract from event: {e}")
            if self.error_count > 100:
                raise TrainingDataExtractionError(
                    LearningErrorCode.E7000,
                    f"Too many extraction errors: {self.error_count}"
                )
            return None

    async def _extract_from_execution(
        self,
        event: Dict[str, Any]
    ) -> Optional[TrainingExample]:
        """Extract training example from execution event.

        Args:
            event: Execution completed event

        Returns:
            TrainingExample or None
        """
        data = event.get('data', {})
        execution_id = data.get('execution_id', '')
        trace = data.get('trace', {})

        if not execution_id or not trace:
            logger.warning(
                f"Malformed execution event: missing execution_id or trace",
                extra={'error_code': LearningErrorCode.E7001.name}
            )
            return None

        # Get quality score (would normally fetch from L06)
        quality_score = data.get('quality_score', 50.0)
        confidence = data.get('confidence', 0.5)

        # Filter by minimum thresholds
        if quality_score < self.min_quality_score:
            return None
        if confidence < self.min_confidence:
            return None

        # Create training example
        try:
            example = TrainingExample.from_execution_trace(
                trace=trace,
                execution_id=execution_id,
                quality_score=quality_score,
                confidence=confidence
            )

            if not example.validate():
                logger.warning(f"Invalid training example: {example.example_id}")
                return None

            self.extraction_count += 1
            logger.debug(f"Extracted example {example.example_id} from {execution_id}")
            return example

        except Exception as e:
            logger.error(f"Failed to create training example: {e}")
            return None

    async def _extract_from_planning(
        self,
        event: Dict[str, Any]
    ) -> Optional[TrainingExample]:
        """Extract training example from planning event.

        Args:
            event: Planning completed event

        Returns:
            TrainingExample or None
        """
        data = event.get('data', {})
        plan_id = data.get('plan_id', '')
        plan = data.get('plan', {})

        if not plan_id or not plan:
            return None

        # Get quality score
        quality_score = data.get('quality_score', 50.0)
        confidence = data.get('confidence', 0.5)

        if quality_score < self.min_quality_score:
            return None
        if confidence < self.min_confidence:
            return None

        # Create training example from planning trace
        example = TrainingExample(
            execution_id=plan_id,
            task_id=plan.get('task_id', ''),
            agent_id=plan.get('agent_id', ''),
            source_type=ExampleSource.PLANNING_TRACE,
            input_text=plan.get('task_description', ''),
            input_structured=plan.get('context', {}),
            output_text=str(plan.get('steps', [])),
            expected_actions=plan.get('steps', []),
            final_answer=plan.get('expected_outcome', ''),
            quality_score=quality_score,
            confidence=confidence,
            domain=plan.get('domain', 'planning'),
        )

        if not example.validate():
            return None

        self.extraction_count += 1
        return example

    async def extract_batch(
        self,
        events: List[Dict[str, Any]]
    ) -> List[TrainingExample]:
        """Extract training examples from multiple events in parallel.

        Args:
            events: List of CloudEvent dictionaries

        Returns:
            List of successfully extracted training examples
        """
        logger.info(f"Extracting from batch of {len(events)} events")

        # Process events in parallel
        tasks = [self.extract_from_event(event) for event in events]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None and exceptions
        examples = [
            r for r in results
            if r is not None and not isinstance(r, Exception)
        ]

        logger.info(
            f"Extracted {len(examples)}/{len(events)} examples "
            f"({self.error_count} errors)"
        )

        return examples

    async def extract_from_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        event_source: Any = None
    ) -> List[TrainingExample]:
        """Extract training examples from date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            event_source: Optional event source client

        Returns:
            List of extracted training examples
        """
        # This would fetch events from L01 event stream
        # For now, return empty list as stub
        logger.info(f"Extracting from {start_date} to {end_date}")
        return []

    def get_statistics(self) -> Dict[str, Any]:
        """Get extraction statistics.

        Returns:
            Dictionary of statistics
        """
        return {
            'total_extracted': self.extraction_count,
            'total_errors': self.error_count,
            'error_rate': self.error_count / max(1, self.extraction_count + self.error_count)
        }

    async def validate_trace_completeness(
        self,
        trace: Dict[str, Any]
    ) -> bool:
        """Validate that trace has required fields.

        Args:
            trace: Execution trace

        Returns:
            True if complete, False otherwise
        """
        required_fields = ['task_id', 'task_description', 'steps']
        return all(field in trace for field in required_fields)

    async def handle_malformed_trace(
        self,
        trace: Dict[str, Any],
        error: str
    ) -> None:
        """Handle malformed trace gracefully.

        Args:
            trace: Malformed trace
            error: Error description
        """
        logger.warning(
            f"Malformed trace: {error}",
            extra={
                'trace_id': trace.get('trace_id', 'unknown'),
                'error_code': LearningErrorCode.E7001.name
            }
        )
        self.error_count += 1
