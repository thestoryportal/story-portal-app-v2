"""
Failure Learner - Learn from failures
Path: platform/src/L05_planning/services/failure_learner.py

Features:
- Record failure patterns
- Find similar past failures
- Suggest preventions
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
import hashlib
import re

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of failures."""
    PARSE_ERROR = "parse_error"
    VALIDATION_ERROR = "validation_error"
    EXECUTION_ERROR = "execution_error"
    TIMEOUT = "timeout"
    DEPENDENCY_MISSING = "dependency_missing"
    PERMISSION_DENIED = "permission_denied"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    NETWORK_ERROR = "network_error"
    TEST_FAILURE = "test_failure"
    ROLLBACK_FAILURE = "rollback_failure"
    UNKNOWN = "unknown"


@dataclass
class FailureRecord:
    """A recorded failure for learning."""
    failure_id: str
    execution_id: str
    unit_id: Optional[str]
    failure_type: FailureType
    error_message: str
    error_signature: str  # Normalized signature for matching
    timestamp: datetime

    # Context
    unit_type: Optional[str] = None
    operation: Optional[str] = None
    file_path: Optional[str] = None
    command: Optional[str] = None

    # Resolution
    resolved: bool = False
    resolution_strategy: Optional[str] = None
    resolution_notes: Optional[str] = None

    # Matching
    similar_failures: List[str] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "failure_id": self.failure_id,
            "execution_id": self.execution_id,
            "unit_id": self.unit_id,
            "failure_type": self.failure_type.value,
            "error_message": self.error_message,
            "error_signature": self.error_signature,
            "timestamp": self.timestamp.isoformat(),
            "unit_type": self.unit_type,
            "operation": self.operation,
            "file_path": self.file_path,
            "command": self.command,
            "resolved": self.resolved,
            "resolution_strategy": self.resolution_strategy,
            "resolution_notes": self.resolution_notes,
            "similar_failures": self.similar_failures,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FailureRecord":
        """Create from dictionary."""
        return cls(
            failure_id=data["failure_id"],
            execution_id=data["execution_id"],
            unit_id=data.get("unit_id"),
            failure_type=FailureType(data["failure_type"]),
            error_message=data["error_message"],
            error_signature=data["error_signature"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            unit_type=data.get("unit_type"),
            operation=data.get("operation"),
            file_path=data.get("file_path"),
            command=data.get("command"),
            resolved=data.get("resolved", False),
            resolution_strategy=data.get("resolution_strategy"),
            resolution_notes=data.get("resolution_notes"),
            similar_failures=data.get("similar_failures", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Prevention:
    """A suggested prevention for a failure type."""
    prevention_id: str
    failure_type: FailureType
    pattern: str  # Regex pattern to match
    suggestion: str
    confidence: float  # 0.0 to 1.0
    success_count: int = 0
    failure_count: int = 0

    @property
    def effectiveness(self) -> float:
        """Calculate effectiveness rate."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5  # No data, assume neutral
        return self.success_count / total

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "prevention_id": self.prevention_id,
            "failure_type": self.failure_type.value,
            "pattern": self.pattern,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Prevention":
        """Create from dictionary."""
        return cls(
            prevention_id=data["prevention_id"],
            failure_type=FailureType(data["failure_type"]),
            pattern=data["pattern"],
            suggestion=data["suggestion"],
            confidence=data.get("confidence", 0.5),
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
        )


@dataclass
class SimilarFailure:
    """A similar failure match."""
    failure_record: FailureRecord
    similarity_score: float
    matching_factors: List[str]


# Default preventions based on common failure types
DEFAULT_PREVENTIONS: List[Prevention] = [
    Prevention(
        prevention_id="prev_file_not_found",
        failure_type=FailureType.EXECUTION_ERROR,
        pattern=r"(FileNotFoundError|No such file|ENOENT)",
        suggestion="Verify file paths exist before operations. Create parent directories if needed.",
        confidence=0.9,
    ),
    Prevention(
        prevention_id="prev_permission",
        failure_type=FailureType.PERMISSION_DENIED,
        pattern=r"(Permission denied|EACCES|PermissionError)",
        suggestion="Check file permissions before operations. Consider using sudo for system files.",
        confidence=0.85,
    ),
    Prevention(
        prevention_id="prev_timeout",
        failure_type=FailureType.TIMEOUT,
        pattern=r"(timeout|timed out|TimeoutError)",
        suggestion="Increase timeout for long-running operations. Add progress monitoring.",
        confidence=0.8,
    ),
    Prevention(
        prevention_id="prev_import",
        failure_type=FailureType.DEPENDENCY_MISSING,
        pattern=r"(ImportError|ModuleNotFoundError|No module named)",
        suggestion="Install missing dependencies before execution. Use requirements.txt.",
        confidence=0.9,
    ),
    Prevention(
        prevention_id="prev_syntax",
        failure_type=FailureType.PARSE_ERROR,
        pattern=r"(SyntaxError|IndentationError|invalid syntax)",
        suggestion="Validate code syntax before execution. Use linting tools.",
        confidence=0.85,
    ),
    Prevention(
        prevention_id="prev_memory",
        failure_type=FailureType.RESOURCE_EXHAUSTED,
        pattern=r"(MemoryError|out of memory|OOM)",
        suggestion="Process data in smaller batches. Monitor memory usage.",
        confidence=0.75,
    ),
    Prevention(
        prevention_id="prev_network",
        failure_type=FailureType.NETWORK_ERROR,
        pattern=r"(ConnectionError|ConnectionRefused|ECONNREFUSED)",
        suggestion="Check network connectivity. Implement retry with exponential backoff.",
        confidence=0.8,
    ),
    Prevention(
        prevention_id="prev_test",
        failure_type=FailureType.TEST_FAILURE,
        pattern=r"(AssertionError|FAILED|test.*failed)",
        suggestion="Review test assertions. Check for state pollution between tests.",
        confidence=0.7,
    ),
]


class FailureLearner:
    """
    Learn from failures to prevent future issues.

    Features:
    - Record failure patterns
    - Find similar past failures
    - Suggest preventions
    - Track resolution effectiveness
    - Persist learning for context compaction survival
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        max_records: int = 1000,
        similarity_threshold: float = 0.6,
    ):
        """
        Initialize failure learner.

        Args:
            storage_path: Path for persisting failure records
            max_records: Maximum number of failure records to keep
            similarity_threshold: Minimum similarity score for matching
        """
        self.storage_path = Path(storage_path) if storage_path else Path.cwd() / ".l05_failures"
        self.max_records = max_records
        self.similarity_threshold = similarity_threshold

        # In-memory storage
        self._failures: Dict[str, FailureRecord] = {}
        self._preventions: Dict[str, Prevention] = {}
        self._signature_index: Dict[str, List[str]] = {}  # signature -> failure_ids

        # Initialize
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._load_data()
        self._initialize_default_preventions()

    def record_failure(
        self,
        execution_id: str,
        error_message: str,
        failure_type: Optional[FailureType] = None,
        unit_id: Optional[str] = None,
        unit_type: Optional[str] = None,
        operation: Optional[str] = None,
        file_path: Optional[str] = None,
        command: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FailureRecord:
        """
        Record a failure for learning.

        Args:
            execution_id: Execution identifier
            error_message: The error message
            failure_type: Type of failure (auto-detected if not provided)
            unit_id: Associated unit ID
            unit_type: Type of unit
            operation: Operation being performed
            file_path: File path involved
            command: Command being executed
            metadata: Additional metadata

        Returns:
            FailureRecord
        """
        # Auto-detect failure type if not provided
        if failure_type is None:
            failure_type = self._detect_failure_type(error_message)

        # Generate signature for matching
        signature = self._generate_signature(error_message, failure_type)

        failure_id = f"fail_{uuid4().hex[:12]}"

        record = FailureRecord(
            failure_id=failure_id,
            execution_id=execution_id,
            unit_id=unit_id,
            failure_type=failure_type,
            error_message=error_message,
            error_signature=signature,
            timestamp=datetime.now(),
            unit_type=unit_type,
            operation=operation,
            file_path=file_path,
            command=command,
            metadata=metadata or {},
        )

        # Find similar failures
        similar = self.find_similar_failures(record)
        record.similar_failures = [s.failure_record.failure_id for s in similar[:5]]

        # Store
        self._failures[failure_id] = record

        # Update signature index
        if signature not in self._signature_index:
            self._signature_index[signature] = []
        self._signature_index[signature].append(failure_id)

        # Persist
        self._persist_failure(record)

        # Trim if over limit
        self._trim_records()

        logger.info(f"Recorded failure: {failure_id} ({failure_type.value})")

        return record

    def find_similar_failures(
        self,
        failure: FailureRecord,
        limit: int = 10,
    ) -> List[SimilarFailure]:
        """
        Find similar past failures.

        Args:
            failure: Failure to match against
            limit: Maximum number of matches

        Returns:
            List of similar failures with scores
        """
        matches = []

        for record in self._failures.values():
            if record.failure_id == failure.failure_id:
                continue

            score, factors = self._calculate_similarity(failure, record)

            if score >= self.similarity_threshold:
                matches.append(SimilarFailure(
                    failure_record=record,
                    similarity_score=score,
                    matching_factors=factors,
                ))

        # Sort by similarity score
        matches.sort(key=lambda m: m.similarity_score, reverse=True)

        return matches[:limit]

    def suggest_preventions(
        self,
        error_message: str,
        failure_type: Optional[FailureType] = None,
    ) -> List[Tuple[Prevention, float]]:
        """
        Suggest preventions for an error.

        Args:
            error_message: The error message
            failure_type: Type of failure (optional)

        Returns:
            List of (prevention, match_score) tuples
        """
        if failure_type is None:
            failure_type = self._detect_failure_type(error_message)

        suggestions = []

        for prevention in self._preventions.values():
            # Match by type
            type_match = prevention.failure_type == failure_type

            # Match by pattern
            pattern_match = False
            try:
                if re.search(prevention.pattern, error_message, re.IGNORECASE):
                    pattern_match = True
            except re.error:
                pass

            if type_match or pattern_match:
                # Calculate match score
                score = 0.0
                if type_match:
                    score += 0.4
                if pattern_match:
                    score += 0.4

                # Factor in effectiveness
                score += 0.2 * prevention.effectiveness

                # Factor in confidence
                score *= prevention.confidence

                suggestions.append((prevention, score))

        # Sort by score
        suggestions.sort(key=lambda x: x[1], reverse=True)

        return suggestions

    def mark_resolved(
        self,
        failure_id: str,
        resolution_strategy: str,
        resolution_notes: Optional[str] = None,
        effective: bool = True,
    ):
        """
        Mark a failure as resolved.

        Args:
            failure_id: Failure identifier
            resolution_strategy: Strategy used to resolve
            resolution_notes: Additional notes
            effective: Whether the resolution was effective
        """
        if failure_id not in self._failures:
            return

        record = self._failures[failure_id]
        record.resolved = True
        record.resolution_strategy = resolution_strategy
        record.resolution_notes = resolution_notes

        # Update prevention effectiveness
        self._update_prevention_effectiveness(
            record.failure_type,
            record.error_message,
            effective,
        )

        self._persist_failure(record)

        logger.info(f"Marked failure resolved: {failure_id}")

    def add_prevention(
        self,
        failure_type: FailureType,
        pattern: str,
        suggestion: str,
        confidence: float = 0.5,
    ) -> Prevention:
        """
        Add a new prevention rule.

        Args:
            failure_type: Type of failure this prevents
            pattern: Regex pattern to match
            suggestion: Prevention suggestion
            confidence: Initial confidence

        Returns:
            Created Prevention
        """
        prevention_id = f"prev_{uuid4().hex[:8]}"

        prevention = Prevention(
            prevention_id=prevention_id,
            failure_type=failure_type,
            pattern=pattern,
            suggestion=suggestion,
            confidence=confidence,
        )

        self._preventions[prevention_id] = prevention
        self._persist_preventions()

        logger.info(f"Added prevention: {prevention_id}")

        return prevention

    def get_failure(self, failure_id: str) -> Optional[FailureRecord]:
        """Get a specific failure record."""
        return self._failures.get(failure_id)

    def list_failures(
        self,
        failure_type: Optional[FailureType] = None,
        resolved: Optional[bool] = None,
        execution_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[FailureRecord]:
        """
        List failure records with optional filters.

        Args:
            failure_type: Filter by failure type
            resolved: Filter by resolution status
            execution_id: Filter by execution
            limit: Maximum number to return

        Returns:
            List of failure records
        """
        records = list(self._failures.values())

        if failure_type is not None:
            records = [r for r in records if r.failure_type == failure_type]

        if resolved is not None:
            records = [r for r in records if r.resolved == resolved]

        if execution_id is not None:
            records = [r for r in records if r.execution_id == execution_id]

        # Sort by timestamp (newest first)
        records.sort(key=lambda r: r.timestamp, reverse=True)

        return records[:limit]

    def get_failure_stats(self) -> Dict[str, Any]:
        """Get statistics about recorded failures."""
        by_type: Dict[str, int] = {}
        resolved_count = 0

        for record in self._failures.values():
            type_key = record.failure_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1
            if record.resolved:
                resolved_count += 1

        return {
            "total_failures": len(self._failures),
            "resolved_count": resolved_count,
            "unresolved_count": len(self._failures) - resolved_count,
            "by_type": by_type,
            "prevention_count": len(self._preventions),
        }

    def _detect_failure_type(self, error_message: str) -> FailureType:
        """Auto-detect failure type from error message."""
        message_lower = error_message.lower()

        if any(kw in message_lower for kw in ["timeout", "timed out"]):
            return FailureType.TIMEOUT

        if any(kw in message_lower for kw in ["permission denied", "eacces"]):
            return FailureType.PERMISSION_DENIED

        if any(kw in message_lower for kw in ["import", "module", "no module"]):
            return FailureType.DEPENDENCY_MISSING

        if any(kw in message_lower for kw in ["syntax", "parse", "indentation"]):
            return FailureType.PARSE_ERROR

        if any(kw in message_lower for kw in ["validate", "validation", "invalid"]):
            return FailureType.VALIDATION_ERROR

        if any(kw in message_lower for kw in ["memory", "oom", "out of memory"]):
            return FailureType.RESOURCE_EXHAUSTED

        if any(kw in message_lower for kw in ["connection", "network", "refused"]):
            return FailureType.NETWORK_ERROR

        if any(kw in message_lower for kw in ["test", "assert", "failed"]):
            return FailureType.TEST_FAILURE

        if any(kw in message_lower for kw in ["rollback", "revert"]):
            return FailureType.ROLLBACK_FAILURE

        return FailureType.EXECUTION_ERROR

    def _generate_signature(
        self,
        error_message: str,
        failure_type: FailureType,
    ) -> str:
        """Generate a normalized signature for matching."""
        # Normalize the error message
        normalized = error_message.lower()

        # Remove variable parts (paths, numbers, etc.)
        normalized = re.sub(r'/[\w/.-]+', '<path>', normalized)
        normalized = re.sub(r'\d+', '<num>', normalized)
        normalized = re.sub(r'0x[0-9a-f]+', '<hex>', normalized)
        normalized = re.sub(r"'[^']*'", '<str>', normalized)
        normalized = re.sub(r'"[^"]*"', '<str>', normalized)

        # Create hash
        content = f"{failure_type.value}:{normalized}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _calculate_similarity(
        self,
        failure1: FailureRecord,
        failure2: FailureRecord,
    ) -> Tuple[float, List[str]]:
        """Calculate similarity between two failures."""
        score = 0.0
        factors = []

        # Same failure type (high weight)
        if failure1.failure_type == failure2.failure_type:
            score += 0.3
            factors.append("same_type")

        # Same signature (very high weight)
        if failure1.error_signature == failure2.error_signature:
            score += 0.4
            factors.append("same_signature")

        # Same unit type
        if failure1.unit_type and failure1.unit_type == failure2.unit_type:
            score += 0.1
            factors.append("same_unit_type")

        # Same operation
        if failure1.operation and failure1.operation == failure2.operation:
            score += 0.1
            factors.append("same_operation")

        # Similar file paths
        if failure1.file_path and failure2.file_path:
            if self._paths_similar(failure1.file_path, failure2.file_path):
                score += 0.1
                factors.append("similar_path")

        return score, factors

    def _paths_similar(self, path1: str, path2: str) -> bool:
        """Check if two file paths are similar."""
        # Extract extensions
        ext1 = Path(path1).suffix
        ext2 = Path(path2).suffix

        if ext1 and ext1 == ext2:
            return True

        # Check for similar directory structure
        parts1 = set(Path(path1).parts)
        parts2 = set(Path(path2).parts)

        overlap = len(parts1 & parts2)
        total = len(parts1 | parts2)

        return overlap / total > 0.5 if total > 0 else False

    def _update_prevention_effectiveness(
        self,
        failure_type: FailureType,
        error_message: str,
        effective: bool,
    ):
        """Update prevention effectiveness based on resolution."""
        for prevention in self._preventions.values():
            if prevention.failure_type != failure_type:
                continue

            try:
                if re.search(prevention.pattern, error_message, re.IGNORECASE):
                    if effective:
                        prevention.success_count += 1
                    else:
                        prevention.failure_count += 1
            except re.error:
                pass

        self._persist_preventions()

    def _trim_records(self):
        """Trim old records if over limit."""
        if len(self._failures) <= self.max_records:
            return

        # Sort by timestamp
        sorted_records = sorted(
            self._failures.values(),
            key=lambda r: r.timestamp,
        )

        # Remove oldest, keeping unresolved ones
        to_remove = []
        for record in sorted_records:
            if len(self._failures) - len(to_remove) <= self.max_records:
                break
            if record.resolved:
                to_remove.append(record.failure_id)

        for failure_id in to_remove:
            del self._failures[failure_id]
            # Clean up signature index
            for sig, ids in list(self._signature_index.items()):
                if failure_id in ids:
                    ids.remove(failure_id)
                    if not ids:
                        del self._signature_index[sig]

    def _initialize_default_preventions(self):
        """Initialize default preventions if not already loaded."""
        for prevention in DEFAULT_PREVENTIONS:
            if prevention.prevention_id not in self._preventions:
                self._preventions[prevention.prevention_id] = prevention

        self._persist_preventions()

    def _persist_failure(self, record: FailureRecord):
        """Persist a failure record to disk."""
        file_path = self.storage_path / "failures" / f"{record.failure_id}.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, "w") as f:
                json.dump(record.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist failure record: {e}")

    def _persist_preventions(self):
        """Persist all preventions to disk."""
        file_path = self.storage_path / "preventions.json"

        try:
            data = {pid: p.to_dict() for pid, p in self._preventions.items()}
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist preventions: {e}")

    def _load_data(self):
        """Load data from disk."""
        # Load failures
        failures_dir = self.storage_path / "failures"
        if failures_dir.exists():
            for file_path in failures_dir.glob("*.json"):
                try:
                    with open(file_path) as f:
                        data = json.load(f)
                        record = FailureRecord.from_dict(data)
                        self._failures[record.failure_id] = record

                        # Update signature index
                        if record.error_signature not in self._signature_index:
                            self._signature_index[record.error_signature] = []
                        self._signature_index[record.error_signature].append(record.failure_id)
                except Exception as e:
                    logger.warning(f"Failed to load failure record {file_path}: {e}")

        # Load preventions
        preventions_path = self.storage_path / "preventions.json"
        if preventions_path.exists():
            try:
                with open(preventions_path) as f:
                    data = json.load(f)
                    for pid, pdata in data.items():
                        self._preventions[pid] = Prevention.from_dict(pdata)
            except Exception as e:
                logger.warning(f"Failed to load preventions: {e}")

        logger.info(f"Loaded {len(self._failures)} failure records, {len(self._preventions)} preventions")
