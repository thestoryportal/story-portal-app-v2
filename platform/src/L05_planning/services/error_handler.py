"""
Error Handler - Centralized error handling
Path: platform/src/L05_planning/services/error_handler.py

Features:
- Severity classification (WARNING, RECOVERABLE, FATAL)
- Automatic recovery strategy selection
- Integration with RecoveryProtocol and CompensationEngine
"""

import logging
import re
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type
from uuid import uuid4

from ..checkpoints.recovery_protocol import RecoveryProtocol, RecoveryStrategy, RecoveryResult, FailureContext
from ..checkpoints.compensation_engine import CompensationEngine
from ..agents.spec_decomposer import AtomicUnit

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    DEBUG = "debug"        # Not really an error, just logging
    INFO = "info"          # Informational, no action needed
    WARNING = "warning"    # Something unexpected but not blocking
    RECOVERABLE = "recoverable"  # Error but can recover
    FATAL = "fatal"        # Cannot continue, must stop


class ErrorCategory(Enum):
    """Categories of errors."""
    PARSE = "parse"              # Plan parsing errors
    DECOMPOSITION = "decomposition"  # Unit decomposition errors
    VALIDATION = "validation"    # Validation failures
    EXECUTION = "execution"      # Execution errors
    NETWORK = "network"          # Network/connectivity errors
    TIMEOUT = "timeout"          # Timeout errors
    PERMISSION = "permission"    # Permission/access errors
    RESOURCE = "resource"        # Resource exhaustion
    DEPENDENCY = "dependency"    # Missing dependencies
    INTERNAL = "internal"        # Internal/unexpected errors
    USER = "user"                # User-caused errors


@dataclass
class HandledError:
    """An error that has been handled."""
    error_id: str
    original_error: Exception
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Context
    execution_id: Optional[str] = None
    unit_id: Optional[str] = None
    operation: Optional[str] = None

    # Recovery
    recovery_attempted: bool = False
    recovery_success: bool = False
    recovery_strategy: Optional[RecoveryStrategy] = None
    recovery_result: Optional[RecoveryResult] = None

    # Stack trace
    stack_trace: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_id": self.error_id,
            "error_type": type(self.original_error).__name__,
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "execution_id": self.execution_id,
            "unit_id": self.unit_id,
            "operation": self.operation,
            "recovery_attempted": self.recovery_attempted,
            "recovery_success": self.recovery_success,
            "recovery_strategy": self.recovery_strategy.value if self.recovery_strategy else None,
            "stack_trace": self.stack_trace,
            "metadata": self.metadata,
        }


@dataclass
class ErrorPattern:
    """Pattern for matching and classifying errors."""
    name: str
    pattern: str  # Regex pattern to match
    severity: ErrorSeverity
    category: ErrorCategory
    recovery_strategy: Optional[RecoveryStrategy] = None
    message_template: Optional[str] = None


# Default error patterns for classification
DEFAULT_ERROR_PATTERNS = [
    # Parse errors
    ErrorPattern(
        name="parse_error",
        pattern=r"(?i)(parse|parsing|syntax)\s*(error|failed|invalid)",
        severity=ErrorSeverity.RECOVERABLE,
        category=ErrorCategory.PARSE,
        recovery_strategy=RecoveryStrategy.SKIP,
        message_template="Parse error: {error}",
    ),
    ErrorPattern(
        name="invalid_format",
        pattern=r"(?i)(invalid|unexpected|malformed)\s*(format|structure|schema)",
        severity=ErrorSeverity.RECOVERABLE,
        category=ErrorCategory.PARSE,
        recovery_strategy=RecoveryStrategy.SKIP,
    ),

    # Validation errors
    ErrorPattern(
        name="validation_failed",
        pattern=r"(?i)(validation|criteria|assert)\s*(failed|error)",
        severity=ErrorSeverity.RECOVERABLE,
        category=ErrorCategory.VALIDATION,
        recovery_strategy=RecoveryStrategy.RETRY,
    ),
    ErrorPattern(
        name="test_failed",
        pattern=r"(?i)(test|pytest|unittest)\s*(failed|error|failure)",
        severity=ErrorSeverity.RECOVERABLE,
        category=ErrorCategory.VALIDATION,
        recovery_strategy=RecoveryStrategy.COMPENSATE_ONLY,
    ),

    # Network errors
    ErrorPattern(
        name="connection_error",
        pattern=r"(?i)(connection|connect)\s*(refused|failed|error|timeout)",
        severity=ErrorSeverity.RECOVERABLE,
        category=ErrorCategory.NETWORK,
        recovery_strategy=RecoveryStrategy.RETRY,
    ),
    ErrorPattern(
        name="http_error",
        pattern=r"(?i)(http|request)\s*(error|failed|4\d\d|5\d\d)",
        severity=ErrorSeverity.RECOVERABLE,
        category=ErrorCategory.NETWORK,
        recovery_strategy=RecoveryStrategy.RETRY,
    ),

    # Timeout errors
    ErrorPattern(
        name="timeout",
        pattern=r"(?i)(timeout|timed?\s*out|deadline\s*exceeded)",
        severity=ErrorSeverity.RECOVERABLE,
        category=ErrorCategory.TIMEOUT,
        recovery_strategy=RecoveryStrategy.RETRY,
    ),

    # Permission errors
    ErrorPattern(
        name="permission_denied",
        pattern=r"(?i)(permission|access)\s*(denied|forbidden|unauthorized)",
        severity=ErrorSeverity.FATAL,
        category=ErrorCategory.PERMISSION,
        recovery_strategy=None,
    ),
    ErrorPattern(
        name="auth_failed",
        pattern=r"(?i)(auth|authentication|authorization)\s*(failed|error|invalid)",
        severity=ErrorSeverity.FATAL,
        category=ErrorCategory.PERMISSION,
        recovery_strategy=None,
    ),

    # Resource errors
    ErrorPattern(
        name="out_of_memory",
        pattern=r"(?i)(out\s*of\s*memory|memory\s*error|oom)",
        severity=ErrorSeverity.FATAL,
        category=ErrorCategory.RESOURCE,
        recovery_strategy=None,
    ),
    ErrorPattern(
        name="disk_full",
        pattern=r"(?i)(disk|space)\s*(full|exhausted|no\s*space)",
        severity=ErrorSeverity.FATAL,
        category=ErrorCategory.RESOURCE,
        recovery_strategy=None,
    ),

    # Dependency errors
    ErrorPattern(
        name="import_error",
        pattern=r"(?i)(import|module)\s*(error|not\s*found)",
        severity=ErrorSeverity.FATAL,
        category=ErrorCategory.DEPENDENCY,
        recovery_strategy=None,
    ),
    ErrorPattern(
        name="file_not_found",
        pattern=r"(?i)(file|path)\s*(not\s*found|doesn't\s*exist|missing)",
        severity=ErrorSeverity.RECOVERABLE,
        category=ErrorCategory.DEPENDENCY,
        recovery_strategy=RecoveryStrategy.SKIP,
    ),

    # Execution errors
    ErrorPattern(
        name="command_failed",
        pattern=r"(?i)(command|process|subprocess)\s*(failed|error|non.?zero)",
        severity=ErrorSeverity.RECOVERABLE,
        category=ErrorCategory.EXECUTION,
        recovery_strategy=RecoveryStrategy.COMPENSATE_ONLY,
    ),
]


class ErrorHandler:
    """
    Centralized error handling for L05 Planning.

    Features:
    - Error classification by severity and category
    - Pattern-based error matching
    - Automatic recovery strategy selection
    - Integration with RecoveryProtocol
    - Error history tracking
    """

    def __init__(
        self,
        recovery_protocol: Optional[RecoveryProtocol] = None,
        compensation_engine: Optional[CompensationEngine] = None,
        auto_recover: bool = True,
        max_retries: int = 3,
        custom_patterns: Optional[List[ErrorPattern]] = None,
    ):
        """
        Initialize error handler.

        Args:
            recovery_protocol: Protocol for recovery operations
            compensation_engine: Engine for compensation operations
            auto_recover: Whether to automatically attempt recovery
            max_retries: Maximum recovery retries
            custom_patterns: Custom error patterns to add
        """
        self.recovery_protocol = recovery_protocol
        self.compensation_engine = compensation_engine
        self.auto_recover = auto_recover
        self.max_retries = max_retries

        # Error patterns
        self._patterns = list(DEFAULT_ERROR_PATTERNS)
        if custom_patterns:
            self._patterns.extend(custom_patterns)

        # Compile patterns
        self._compiled_patterns = [
            (p, re.compile(p.pattern))
            for p in self._patterns
        ]

        # Error history
        self._error_history: List[HandledError] = []

        # Custom handlers by exception type
        self._exception_handlers: Dict[Type[Exception], Callable] = {}

        # Statistics
        self._total_errors = 0
        self._recovered_errors = 0
        self._fatal_errors = 0

    def handle(
        self,
        error: Exception,
        execution_id: Optional[str] = None,
        unit: Optional[AtomicUnit] = None,
        operation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> HandledError:
        """
        Handle an error with classification and optional recovery.

        Args:
            error: The exception to handle
            execution_id: Execution context
            unit: Unit context if applicable
            operation: Operation being performed
            context: Additional context

        Returns:
            HandledError with classification and recovery status
        """
        self._total_errors += 1
        error_id = f"err-{uuid4().hex[:8]}"

        logger.debug(f"Handling error {error_id}: {error}")

        # Classify error
        severity, category, pattern = self._classify_error(error)

        # Create handled error record
        handled = HandledError(
            error_id=error_id,
            original_error=error,
            severity=severity,
            category=category,
            message=str(error),
            execution_id=execution_id,
            unit_id=unit.id if unit else None,
            operation=operation,
            stack_trace=traceback.format_exc(),
            metadata=context or {},
        )

        # Log based on severity
        self._log_error(handled)

        # Check for custom handler
        handler = self._exception_handlers.get(type(error))
        if handler:
            try:
                handler(handled)
            except Exception as e:
                logger.warning(f"Custom error handler failed: {e}")

        # Attempt recovery if appropriate
        if self.auto_recover and severity == ErrorSeverity.RECOVERABLE:
            recovery_strategy = pattern.recovery_strategy if pattern else RecoveryStrategy.RETRY

            if unit and self.recovery_protocol:
                handled = self._attempt_recovery(handled, unit, recovery_strategy)

        # Track fatal errors
        if severity == ErrorSeverity.FATAL:
            self._fatal_errors += 1

        # Add to history
        self._error_history.append(handled)

        return handled

    def handle_with_retry(
        self,
        func: Callable,
        *args,
        max_retries: Optional[int] = None,
        execution_id: Optional[str] = None,
        unit: Optional[AtomicUnit] = None,
        **kwargs,
    ) -> Any:
        """
        Execute a function with automatic retry on recoverable errors.

        Args:
            func: Function to execute
            *args: Arguments for function
            max_retries: Maximum retry attempts
            execution_id: Execution context
            unit: Unit context
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            Exception: If all retries exhausted or fatal error
        """
        retries = max_retries or self.max_retries
        last_error = None

        for attempt in range(retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handled = self.handle(
                    error=e,
                    execution_id=execution_id,
                    unit=unit,
                    operation=f"{func.__name__} (attempt {attempt + 1}/{retries + 1})",
                    context={"attempt": attempt + 1, "max_retries": retries},
                )

                last_error = handled

                if handled.severity == ErrorSeverity.FATAL:
                    raise

                if attempt < retries:
                    logger.info(f"Retrying {func.__name__} (attempt {attempt + 2}/{retries + 1})")

        # All retries exhausted
        raise last_error.original_error if last_error else Exception("Unknown error")

    def _classify_error(
        self,
        error: Exception,
    ) -> tuple[ErrorSeverity, ErrorCategory, Optional[ErrorPattern]]:
        """Classify an error by severity and category."""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Check against patterns
        for pattern, compiled in self._compiled_patterns:
            if compiled.search(error_str) or compiled.search(error_type):
                return pattern.severity, pattern.category, pattern

        # Default classification by exception type
        if isinstance(error, (SyntaxError, ValueError)):
            return ErrorSeverity.RECOVERABLE, ErrorCategory.PARSE, None

        if isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorSeverity.RECOVERABLE, ErrorCategory.NETWORK, None

        if isinstance(error, PermissionError):
            return ErrorSeverity.FATAL, ErrorCategory.PERMISSION, None

        if isinstance(error, MemoryError):
            return ErrorSeverity.FATAL, ErrorCategory.RESOURCE, None

        if isinstance(error, ImportError):
            return ErrorSeverity.FATAL, ErrorCategory.DEPENDENCY, None

        if isinstance(error, FileNotFoundError):
            return ErrorSeverity.RECOVERABLE, ErrorCategory.DEPENDENCY, None

        # Default: recoverable internal error
        return ErrorSeverity.RECOVERABLE, ErrorCategory.INTERNAL, None

    def _log_error(self, handled: HandledError):
        """Log error with appropriate level."""
        log_msg = f"[{handled.error_id}] {handled.category.value}: {handled.message}"

        if handled.severity == ErrorSeverity.DEBUG:
            logger.debug(log_msg)
        elif handled.severity == ErrorSeverity.INFO:
            logger.info(log_msg)
        elif handled.severity == ErrorSeverity.WARNING:
            logger.warning(log_msg)
        elif handled.severity == ErrorSeverity.RECOVERABLE:
            logger.warning(f"RECOVERABLE {log_msg}")
        else:  # FATAL
            logger.error(f"FATAL {log_msg}")

    def _attempt_recovery(
        self,
        handled: HandledError,
        unit: AtomicUnit,
        strategy: RecoveryStrategy,
    ) -> HandledError:
        """Attempt recovery for an error."""
        if not self.recovery_protocol:
            return handled

        handled.recovery_attempted = True
        handled.recovery_strategy = strategy

        try:
            # Create failure context
            failure_context = FailureContext(
                unit=unit,
                error=handled.message,
                attempt=1,
                max_retries=self.max_retries,
            )

            # Attempt recovery
            result = self.recovery_protocol.recover(failure_context, strategy)

            handled.recovery_result = result
            handled.recovery_success = result.success

            if result.success:
                self._recovered_errors += 1
                logger.info(f"Recovery successful for {handled.error_id} using {strategy.value}")
            else:
                logger.warning(f"Recovery failed for {handled.error_id}: {result.message}")

        except Exception as e:
            logger.error(f"Recovery attempt failed: {e}")
            handled.recovery_success = False

        return handled

    def register_handler(
        self,
        exception_type: Type[Exception],
        handler: Callable[[HandledError], None],
    ):
        """
        Register a custom handler for a specific exception type.

        Args:
            exception_type: Exception type to handle
            handler: Handler function
        """
        self._exception_handlers[exception_type] = handler
        logger.debug(f"Registered handler for {exception_type.__name__}")

    def add_pattern(self, pattern: ErrorPattern):
        """
        Add a custom error pattern.

        Args:
            pattern: ErrorPattern to add
        """
        self._patterns.append(pattern)
        self._compiled_patterns.append((pattern, re.compile(pattern.pattern)))
        logger.debug(f"Added error pattern: {pattern.name}")

    def get_history(
        self,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
        execution_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[HandledError]:
        """
        Get error history with optional filtering.

        Args:
            severity: Filter by severity
            category: Filter by category
            execution_id: Filter by execution
            limit: Maximum errors to return

        Returns:
            List of HandledErrors
        """
        errors = self._error_history

        if severity:
            errors = [e for e in errors if e.severity == severity]

        if category:
            errors = [e for e in errors if e.category == category]

        if execution_id:
            errors = [e for e in errors if e.execution_id == execution_id]

        return errors[-limit:]

    def get_fatal_errors(self, execution_id: Optional[str] = None) -> List[HandledError]:
        """Get fatal errors."""
        return self.get_history(severity=ErrorSeverity.FATAL, execution_id=execution_id)

    def get_recoverable_errors(self, execution_id: Optional[str] = None) -> List[HandledError]:
        """Get recoverable errors."""
        return self.get_history(severity=ErrorSeverity.RECOVERABLE, execution_id=execution_id)

    def clear_history(self):
        """Clear error history."""
        self._error_history = []

    def get_statistics(self) -> Dict[str, Any]:
        """Returns error handler statistics."""
        by_severity = {}
        for sev in ErrorSeverity:
            by_severity[sev.value] = len([
                e for e in self._error_history if e.severity == sev
            ])

        by_category = {}
        for cat in ErrorCategory:
            by_category[cat.value] = len([
                e for e in self._error_history if e.category == cat
            ])

        recovery_attempted = len([e for e in self._error_history if e.recovery_attempted])
        recovery_success = len([e for e in self._error_history if e.recovery_success])

        return {
            "total_errors": self._total_errors,
            "recovered_errors": self._recovered_errors,
            "fatal_errors": self._fatal_errors,
            "history_size": len(self._error_history),
            "by_severity": by_severity,
            "by_category": by_category,
            "recovery_attempted": recovery_attempted,
            "recovery_success": recovery_success,
            "recovery_rate": recovery_success / recovery_attempted if recovery_attempted > 0 else 0,
            "pattern_count": len(self._patterns),
            "auto_recover": self.auto_recover,
            "max_retries": self.max_retries,
        }
