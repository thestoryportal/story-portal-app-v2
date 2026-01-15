"""Data models for L12 Natural Language Interface.

This package provides all Pydantic models used throughout the L12 layer:

Service Metadata:
- ServiceMetadata: Complete service metadata
- MethodMetadata: Service method metadata
- ParameterMetadata: Method parameter metadata
- ServiceMatch: Fuzzy match result

Command Models:
- InvokeRequest: Service invocation request
- InvokeResponse: Service invocation response
- ErrorResponse: Structured error information
- SessionInfo: Session state information
- SearchQuery: Fuzzy search query

Enums:
- InvocationStatus: Invocation status enum
- ErrorCode: Error code enum
- ParameterType: Parameter type enum
"""

from .service_metadata import (
    ParameterMetadata,
    ParameterType,
    MethodMetadata,
    ServiceMetadata,
    ServiceMatch,
)

from .command_models import (
    ErrorCode,
    ErrorResponse,
    InvocationStatus,
    InvokeRequest,
    InvokeResponse,
    SearchQuery,
    SessionInfo,
)

__all__ = [
    # Service metadata
    "ParameterMetadata",
    "ParameterType",
    "MethodMetadata",
    "ServiceMetadata",
    "ServiceMatch",
    # Command models
    "ErrorCode",
    "ErrorResponse",
    "InvocationStatus",
    "InvokeRequest",
    "InvokeResponse",
    "SearchQuery",
    "SessionInfo",
]
