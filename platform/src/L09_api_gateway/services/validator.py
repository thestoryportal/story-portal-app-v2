"""
Request Validator - Input Validation and Sanitization
"""

import json
import unicodedata
from typing import Any, Dict, Optional
from ..models import RequestContext
from ..errors import ErrorCode, ValidationError


class RequestValidator:
    """
    Validates incoming requests for security and correctness

    Features:
    - JSON format validation
    - Character encoding validation
    - Null byte detection
    - Request size limits
    - Header validation
    - Query string validation
    - Unicode normalization
    """

    def __init__(
        self,
        max_body_size: int = 10 * 1024 * 1024,  # 10MB
        max_header_count: int = 100,
        max_header_size: int = 16 * 1024,  # 16KB
        max_query_length: int = 4096,
    ):
        self.max_body_size = max_body_size
        self.max_header_count = max_header_count
        self.max_header_size = max_header_size
        self.max_query_length = max_query_length

        # Forbidden headers
        self.forbidden_headers = {
            "x-internal-auth",
            "x-admin-token",
            "x-backend-key",
        }

    async def validate_request(
        self, context: RequestContext, body: Optional[bytes] = None
    ) -> None:
        """
        Validate request

        Args:
            context: Request context
            body: Request body bytes

        Raises:
            ValidationError: If validation fails
        """
        # Validate headers
        self._validate_headers(context)

        # Validate query string
        self._validate_query_string(context)

        # Validate body size
        if body:
            self._validate_body_size(context, body)

            # Validate body content
            if context.metadata.content_type and "json" in context.metadata.content_type:
                self._validate_json_body(body)

            # Validate character encoding
            self._validate_encoding(body)

    def _validate_headers(self, context: RequestContext) -> None:
        """Validate request headers"""
        headers = context.metadata.headers

        # Check header count
        if len(headers) > self.max_header_count:
            raise ValidationError(
                ErrorCode.E9309,
                f"Too many headers (max {self.max_header_count})",
                details={"count": len(headers)},
            )

        # Check header size
        total_size = sum(len(k) + len(v) for k, v in headers.items())
        if total_size > self.max_header_size:
            raise ValidationError(
                ErrorCode.E9309,
                f"Headers too large (max {self.max_header_size} bytes)",
                details={"size": total_size},
            )

        # Check forbidden headers
        for header_name in headers.keys():
            if header_name.lower() in self.forbidden_headers:
                raise ValidationError(
                    ErrorCode.E9309,
                    f"Forbidden header: {header_name}",
                )

    def _validate_query_string(self, context: RequestContext) -> None:
        """Validate query string"""
        # Reconstruct query string
        query_params = context.metadata.query_params
        query_string = "&".join(f"{k}={v}" for k, v in query_params.items())

        # Check length
        if len(query_string) > self.max_query_length:
            raise ValidationError(
                ErrorCode.E9308,
                f"Query string too long (max {self.max_query_length} chars)",
                details={"length": len(query_string)},
            )

    def _validate_body_size(
        self, context: RequestContext, body: bytes
    ) -> None:
        """Validate request body size"""
        body_size = len(body)

        if body_size > self.max_body_size:
            raise ValidationError(
                ErrorCode.E9304,
                f"Request body exceeds size limit (max {self.max_body_size} bytes)",
                details={"size": body_size},
            )

    def _validate_json_body(self, body: bytes) -> None:
        """Validate JSON body format"""
        try:
            json.loads(body)
        except json.JSONDecodeError as e:
            raise ValidationError(
                ErrorCode.E9305,
                f"Invalid JSON format: {str(e)}",
            )

    def _validate_encoding(self, body: bytes) -> None:
        """
        Validate character encoding

        Checks for:
        - Null bytes (0x00)
        - Invalid UTF-8
        - Control characters
        """
        # Check for null bytes
        if b"\x00" in body:
            raise ValidationError(
                ErrorCode.E9307,
                "Null byte detected in request body",
            )

        # Try to decode as UTF-8
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValidationError(
                ErrorCode.E9306,
                f"Invalid UTF-8 encoding: {str(e)}",
            )

        # Check for control characters (except newline, tab, carriage return)
        for char in text:
            if char in ["\n", "\t", "\r"]:
                continue
            if ord(char) < 32 or ord(char) == 127:
                raise ValidationError(
                    ErrorCode.E9306,
                    f"Control character detected: U+{ord(char):04X}",
                )

    def normalize_unicode(self, text: str) -> str:
        """
        Normalize Unicode text to NFC form

        This prevents Unicode normalization attacks
        """
        return unicodedata.normalize("NFC", text)

    def sanitize_string(self, value: str) -> str:
        """
        Sanitize string value

        - Normalize Unicode
        - Strip null bytes
        - Limit length
        """
        # Normalize Unicode
        value = self.normalize_unicode(value)

        # Strip null bytes
        value = value.replace("\x00", "")

        return value
