"""L07 Learning Layer - Training Example Models."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
import hashlib
import json
import uuid


class ExampleSource(Enum):
    """Source type for training examples."""
    EXECUTION_TRACE = "execution_trace"
    PLANNING_TRACE = "planning_trace"
    QUALITY_FEEDBACK = "quality_feedback"
    SYNTHETIC = "synthetic"
    HUMAN_ANNOTATED = "human_annotated"


class ExampleLabel(Enum):
    """Label classification for training examples."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL_SUCCESS = "partial_success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CONSTRAINT_VIOLATION = "constraint_violation"


class TaskType(Enum):
    """Task complexity classification."""
    SINGLE_STEP = "single_step"
    MULTI_STEP = "multi_step"
    REASONING = "reasoning"
    PLANNING = "planning"
    CODE_GENERATION = "code_generation"


@dataclass
class TrainingExample:
    """Structured training example extracted from execution trace.

    A training example represents a single input-output pair suitable for
    supervised fine-tuning or reinforcement learning. Each example includes
    quality scores from L06, metadata for tracking, and structured content
    for model training.
    """

    # Identifiers
    example_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_id: Optional[str] = None

    # Source metadata
    source_type: ExampleSource = ExampleSource.EXECUTION_TRACE
    source_trace_hash: Optional[str] = None

    # Input portion (what the model receives)
    input_text: str = ""
    input_structured: Dict[str, Any] = field(default_factory=dict)

    # Output portion (expected behavior/answer)
    output_text: str = ""
    expected_actions: List[Dict[str, Any]] = field(default_factory=list)
    final_answer: str = ""

    # Quality signals from L06
    quality_score: float = 0.0  # 0-100 scale
    confidence: float = 0.0  # 0-1 scale

    # Classification
    labels: List[str] = field(default_factory=list)
    domain: str = "general"
    task_type: TaskType = TaskType.SINGLE_STEP

    # Computed metadata
    difficulty: float = 0.5  # 0-1 scale

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    extracted_by: str = "TrainingDataExtractor v1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert training example to dictionary."""
        data = asdict(self)
        data['source_type'] = self.source_type.value
        data['task_type'] = self.task_type.value
        data['created_at'] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrainingExample':
        """Create training example from dictionary."""
        if 'source_type' in data and isinstance(data['source_type'], str):
            data['source_type'] = ExampleSource(data['source_type'])
        if 'task_type' in data and isinstance(data['task_type'], str):
            data['task_type'] = TaskType(data['task_type'])
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)

    @classmethod
    def from_execution_trace(
        cls,
        trace: Dict[str, Any],
        execution_id: str,
        quality_score: float,
        confidence: float
    ) -> 'TrainingExample':
        """Create training example from execution trace and quality score.

        Args:
            trace: Execution trace from L02
            execution_id: Unique execution identifier
            quality_score: Quality score from L06 (0-100)
            confidence: Confidence in quality score (0-1)

        Returns:
            TrainingExample instance
        """
        # Extract task metadata
        task_id = trace.get('task_id', '')
        agent_id = trace.get('agent_id', '')

        # Extract input (initial task/goal)
        input_text = trace.get('task_description', '')
        input_structured = trace.get('task_context', {})

        # Extract action sequence from trace steps
        expected_actions = []
        for step in trace.get('steps', []):
            if step.get('action_type') == 'tool_call':
                expected_actions.append({
                    'type': 'tool_call',
                    'tool': step.get('tool_name', ''),
                    'params': step.get('parameters', {}),
                    'reasoning': step.get('reasoning', ''),
                })

        # Extract final answer
        final_answer = trace.get('final_answer', '')
        output_text = trace.get('output', final_answer)

        # Classify task type
        num_steps = len(expected_actions)
        if num_steps == 0:
            task_type = TaskType.SINGLE_STEP
        elif num_steps <= 3:
            task_type = TaskType.MULTI_STEP
        else:
            task_type = TaskType.REASONING

        # Estimate difficulty
        difficulty = cls._estimate_difficulty(
            num_steps,
            len(set(a.get('tool', '') for a in expected_actions if a.get('type') == 'tool_call')),
            quality_score
        )

        # Classify domain
        domain = cls._classify_domain(input_text, trace.get('domain', 'general'))

        # Create source trace hash for audit trail
        trace_json = json.dumps(trace, sort_keys=True)
        source_trace_hash = hashlib.sha256(trace_json.encode()).hexdigest()

        return cls(
            execution_id=execution_id,
            task_id=task_id,
            agent_id=agent_id,
            source_type=ExampleSource.EXECUTION_TRACE,
            source_trace_hash=source_trace_hash,
            input_text=input_text,
            input_structured=input_structured,
            output_text=output_text,
            expected_actions=expected_actions,
            final_answer=final_answer,
            quality_score=quality_score,
            confidence=confidence,
            difficulty=difficulty,
            domain=domain,
            task_type=task_type,
            metadata={
                'num_steps': num_steps,
                'trace_version': trace.get('version', '1.0')
            }
        )

    @staticmethod
    def _estimate_difficulty(
        num_steps: int,
        num_unique_tools: int,
        quality_score: float
    ) -> float:
        """Estimate difficulty on scale 0-1.

        Args:
            num_steps: Number of execution steps
            num_unique_tools: Number of unique tools used
            quality_score: Quality score from L06

        Returns:
            Difficulty score 0-1 (higher = more difficult)
        """
        # Complexity component (0-1)
        complexity = min(num_steps / 10, 1.0) * 0.3  # Max 10 steps

        # Tool diversity component (0-1)
        tool_diversity = min(num_unique_tools / 5, 1.0) * 0.3  # Max 5 tools

        # Inverse quality component (harder if lower quality)
        quality_difficulty = (1 - quality_score / 100) * 0.4

        return min(1.0, max(0.0, complexity + tool_diversity + quality_difficulty))

    @staticmethod
    def _classify_domain(task_text: str, hint: str = '') -> str:
        """Classify task domain from text.

        Args:
            task_text: Task description text
            hint: Optional domain hint

        Returns:
            Domain classification string
        """
        domains = {
            'travel': ['flight', 'hotel', 'booking', 'trip', 'destination'],
            'coding': ['code', 'program', 'debug', 'algorithm', 'function'],
            'qa': ['question', 'answer', 'know', 'research', 'fact'],
            'planning': ['schedule', 'plan', 'organize', 'timeline', 'event'],
            'data': ['analyze', 'data', 'chart', 'graph', 'statistics'],
        }

        text_lower = task_text.lower()

        for domain, keywords in domains.items():
            if any(kw in text_lower for kw in keywords):
                return domain

        return hint if hint else 'general'

    def validate(self) -> bool:
        """Validate training example has required fields.

        Returns:
            True if valid, False otherwise
        """
        if not self.input_text:
            return False
        if not (self.output_text or self.final_answer):
            return False
        if self.quality_score < 0 or self.quality_score > 100:
            return False
        if self.confidence < 0 or self.confidence > 1:
            return False
        return True


@dataclass
class DatasetStatistics:
    """Statistics for a training dataset."""

    total_examples: int = 0
    quality_score_mean: float = 0.0
    quality_score_std: float = 0.0
    confidence_mean: float = 0.0
    confidence_std: float = 0.0
    difficulty_distribution: Dict[str, int] = field(default_factory=dict)
    domain_distribution: Dict[str, int] = field(default_factory=dict)
    task_type_distribution: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary."""
        return asdict(self)
