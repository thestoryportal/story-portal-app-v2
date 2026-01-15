"""Event validation service for CloudEvents"""

import re
from datetime import datetime, timedelta, UTC
from typing import Optional, List
import logging

from ..models.cloud_event import CloudEvent, EventSource
from ..models.error_codes import ErrorCode, ErrorCodeRegistry


logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Exception raised when event validation fails"""
    def __init__(self, code: ErrorCode, message: str, details: str = ""):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)

    def to_dict(self) -> dict:
        """Convert to error response dictionary"""
        return ErrorCodeRegistry.format_error_response(self.code, self.details)


class EventValidator:
    """
    Validates CloudEvents schema, source whitelist, and security constraints.

    Per spec Section 3.2 (Component Responsibilities #1):
    - Validates CloudEvents schema
    - Source whitelist validation
    - Timestamp bounds checking (not future, not too old)
    - Input sanitization (reject injection patterns)
    """

    def __init__(
        self,
        source_whitelist: Optional[List[str]] = None,
        max_event_age_hours: int = 24,
        allow_future_events: bool = False,
    ):
        """
        Initialize event validator.

        Args:
            source_whitelist: List of allowed event sources (default: all L01-L06)
            max_event_age_hours: Maximum event age in hours (default: 24)
            allow_future_events: Allow events with future timestamps (default: False)
        """
        self.source_whitelist = source_whitelist or [
            EventSource.L01_DATA_LAYER.value,
            EventSource.L02_AGENT_RUNTIME.value,
            EventSource.L03_TOOL_EXECUTION.value,
            EventSource.L04_MODEL_GATEWAY.value,
            EventSource.L05_PLANNING.value,
            EventSource.L06_EVALUATION.value,
        ]
        self.max_event_age_hours = max_event_age_hours
        self.allow_future_events = allow_future_events

        # Injection patterns to reject (SQL injection, command injection, XSS)
        self.dangerous_patterns = [
            r"[;\$\{\}]",  # Command injection
            r"--",  # SQL comment
            r"/\*|\*/",  # SQL block comment
            r"<script",  # XSS
            r"javascript:",  # XSS
            r"on\w+\s*=",  # HTML event handlers
        ]
        self.injection_regex = re.compile("|".join(self.dangerous_patterns), re.IGNORECASE)

    async def validate(self, event: CloudEvent) -> CloudEvent:
        """
        Validate CloudEvent against schema and security constraints.

        Args:
            event: CloudEvent to validate

        Returns:
            Validated CloudEvent

        Raises:
            ValidationError: If validation fails
        """
        # 1. Validate required fields
        self._validate_required_fields(event)

        # 2. Validate source whitelist
        self._validate_source(event)

        # 3. Validate timestamp bounds
        self._validate_timestamp(event)

        # 4. Sanitize inputs (check for injection patterns)
        self._sanitize_inputs(event)

        # 5. Validate data payload
        self._validate_data_payload(event)

        logger.debug(f"Event {event.id} validated successfully")
        return event

    def _validate_required_fields(self, event: CloudEvent):
        """Validate required CloudEvent fields"""
        required_fields = ["id", "source", "type", "subject", "data", "time"]

        for field in required_fields:
            if not hasattr(event, field) or getattr(event, field) is None:
                raise ValidationError(
                    ErrorCode.E6101,
                    "CloudEvent validation failed",
                    f"Missing required field: {field}",
                )

        # Validate specversion
        if event.specversion != "1.0":
            raise ValidationError(
                ErrorCode.E6101,
                "CloudEvent validation failed",
                f"Invalid specversion: {event.specversion}, expected 1.0",
            )

    def _validate_source(self, event: CloudEvent):
        """Validate event source against whitelist"""
        if event.source not in self.source_whitelist:
            raise ValidationError(
                ErrorCode.E6101,
                "CloudEvent validation failed",
                f"Source '{event.source}' not in whitelist: {self.source_whitelist}",
            )

    def _validate_timestamp(self, event: CloudEvent):
        """Validate event timestamp bounds"""
        now = datetime.now(UTC)

        # Check if event is from the future
        if not self.allow_future_events and event.time > now:
            future_seconds = (event.time - now).total_seconds()
            if future_seconds > 60:  # Allow 1 minute clock skew
                raise ValidationError(
                    ErrorCode.E6104,
                    "Timestamp invalid",
                    f"Event timestamp is {future_seconds:.0f}s in the future",
                )

        # Check if event is too old
        age_hours = (now - event.time).total_seconds() / 3600
        if age_hours > self.max_event_age_hours:
            raise ValidationError(
                ErrorCode.E6104,
                "Timestamp invalid",
                f"Event is {age_hours:.1f} hours old (max: {self.max_event_age_hours})",
            )

        # Check for negative durations in data payload
        if "duration_ms" in event.data:
            duration = event.data["duration_ms"]
            if isinstance(duration, (int, float)) and duration < 0:
                raise ValidationError(
                    ErrorCode.E6104,
                    "Timestamp invalid",
                    f"Negative duration detected: {duration}ms",
                )

    def _sanitize_inputs(self, event: CloudEvent):
        """Check for injection patterns in event fields"""
        # Check string fields for dangerous patterns
        string_fields = {
            "id": event.id,
            "source": event.source,
            "type": event.type,
            "subject": event.subject,
        }

        for field_name, field_value in string_fields.items():
            if isinstance(field_value, str) and self.injection_regex.search(field_value):
                raise ValidationError(
                    ErrorCode.E6101,
                    "CloudEvent validation failed",
                    f"Dangerous pattern detected in field '{field_name}': {field_value}",
                )

        # Check data payload for injection patterns (recursive)
        self._check_dict_for_injection(event.data, "data")

    def _check_dict_for_injection(self, data: dict, path: str):
        """Recursively check dictionary for injection patterns"""
        if not isinstance(data, dict):
            return

        for key, value in data.items():
            current_path = f"{path}.{key}"

            # Check key for dangerous patterns
            if isinstance(key, str) and self.injection_regex.search(key):
                raise ValidationError(
                    ErrorCode.E6101,
                    "CloudEvent validation failed",
                    f"Dangerous pattern in key at {current_path}",
                )

            # Check string values
            if isinstance(value, str):
                if self.injection_regex.search(value):
                    raise ValidationError(
                        ErrorCode.E6101,
                        "CloudEvent validation failed",
                        f"Dangerous pattern in value at {current_path}",
                    )

            # Recurse into nested dicts
            elif isinstance(value, dict):
                self._check_dict_for_injection(value, current_path)

            # Check lists
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        self._check_dict_for_injection(item, f"{current_path}[{i}]")
                    elif isinstance(item, str) and self.injection_regex.search(item):
                        raise ValidationError(
                            ErrorCode.E6101,
                            "CloudEvent validation failed",
                            f"Dangerous pattern in list at {current_path}[{i}]",
                        )

    def _validate_data_payload(self, event: CloudEvent):
        """Validate data payload structure and content"""
        if not isinstance(event.data, dict):
            raise ValidationError(
                ErrorCode.E6101,
                "CloudEvent validation failed",
                f"Data payload must be a dictionary, got {type(event.data)}",
            )

        # Validate payload size (max 1MB)
        import json
        payload_size = len(json.dumps(event.data))
        max_size = 1024 * 1024  # 1MB
        if payload_size > max_size:
            raise ValidationError(
                ErrorCode.E6101,
                "CloudEvent validation failed",
                f"Data payload too large: {payload_size} bytes (max: {max_size})",
            )

    def validate_sync(self, event: CloudEvent) -> Optional[CloudEvent]:
        """
        Synchronous validation wrapper.

        Returns None if validation fails (for use in sync contexts).
        """
        try:
            # Run validation logic synchronously
            self._validate_required_fields(event)
            self._validate_source(event)
            self._validate_timestamp(event)
            self._sanitize_inputs(event)
            self._validate_data_payload(event)
            return event
        except ValidationError as e:
            logger.error(f"Event validation failed: {e.message} - {e.details}")
            return None
        except Exception as e:
            logger.error(f"Unexpected validation error: {e}")
            return None
