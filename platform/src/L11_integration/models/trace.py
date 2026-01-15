"""
L11 Integration Layer - Tracing and Observability Models.

Models for distributed tracing and request correlation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any
from uuid import uuid4


class SpanKind(str, Enum):
    """Type of span in distributed trace."""

    CLIENT = "client"  # Outgoing request
    SERVER = "server"  # Incoming request
    PRODUCER = "producer"  # Message producer
    CONSUMER = "consumer"  # Message consumer
    INTERNAL = "internal"  # Internal operation


class SpanStatus(str, Enum):
    """Status of a trace span."""

    UNSET = "unset"  # Status not set
    OK = "ok"  # Operation completed successfully
    ERROR = "error"  # Operation failed


@dataclass
class RequestContext:
    """
    Context propagated across service boundaries for tracing and correlation.

    Based on OpenTelemetry context propagation standards.
    """

    trace_id: str = field(default_factory=lambda: str(uuid4()))  # W3C trace ID
    span_id: str = field(default_factory=lambda: str(uuid4()))  # Current span ID
    parent_span_id: Optional[str] = None  # Parent span ID
    correlation_id: Optional[str] = None  # Request correlation ID
    baggage: Dict[str, str] = field(default_factory=dict)  # Context baggage (key-value pairs)
    trace_flags: int = 1  # W3C trace flags (01 = sampled)

    @classmethod
    def create(
        cls,
        correlation_id: Optional[str] = None,
        baggage: Optional[Dict[str, str]] = None,
        parent_span_id: Optional[str] = None,
    ) -> "RequestContext":
        """Factory method to create a new request context."""
        return cls(
            trace_id=str(uuid4()),
            span_id=str(uuid4()),
            parent_span_id=parent_span_id,
            correlation_id=correlation_id or str(uuid4()),
            baggage=baggage or {},
        )

    def create_child_context(self) -> "RequestContext":
        """Create a child context for nested operations."""
        return RequestContext(
            trace_id=self.trace_id,  # Same trace ID
            span_id=str(uuid4()),  # New span ID
            parent_span_id=self.span_id,  # Current span becomes parent
            correlation_id=self.correlation_id,  # Propagate correlation ID
            baggage=self.baggage.copy(),  # Copy baggage
            trace_flags=self.trace_flags,
        )

    def to_headers(self) -> Dict[str, str]:
        """Convert context to HTTP headers for propagation."""
        headers = {
            "traceparent": f"00-{self.trace_id}-{self.span_id}-{self.trace_flags:02x}",
        }
        if self.correlation_id:
            headers["x-correlation-id"] = self.correlation_id
        if self.baggage:
            # W3C baggage format: key1=value1,key2=value2
            baggage_str = ",".join(f"{k}={v}" for k, v in self.baggage.items())
            headers["baggage"] = baggage_str
        return headers

    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> "RequestContext":
        """Extract context from HTTP headers."""
        # Parse W3C traceparent header
        traceparent = headers.get("traceparent", "")
        if traceparent:
            parts = traceparent.split("-")
            if len(parts) == 4:
                _, trace_id, span_id, flags = parts
                trace_flags = int(flags, 16)
            else:
                trace_id = str(uuid4())
                span_id = str(uuid4())
                trace_flags = 1
        else:
            trace_id = str(uuid4())
            span_id = str(uuid4())
            trace_flags = 1

        # Extract correlation ID
        correlation_id = headers.get("x-correlation-id")

        # Parse baggage
        baggage = {}
        baggage_str = headers.get("baggage", "")
        if baggage_str:
            for item in baggage_str.split(","):
                if "=" in item:
                    key, value = item.split("=", 1)
                    baggage[key.strip()] = value.strip()

        return cls(
            trace_id=trace_id,
            span_id=span_id,
            correlation_id=correlation_id,
            baggage=baggage,
            trace_flags=trace_flags,
        )


@dataclass
class TraceSpan:
    """
    A span in a distributed trace.

    Spans represent individual operations in a request flow.
    """

    span_id: str = field(default_factory=lambda: str(uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    parent_span_id: Optional[str] = None
    span_name: str = ""  # Operation name (e.g., "L02.execute_agent")
    span_kind: SpanKind = SpanKind.INTERNAL
    service_name: Optional[str] = None  # Service that created this span
    status: SpanStatus = SpanStatus.UNSET
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)  # Span attributes
    events: list[Dict[str, Any]] = field(default_factory=list)  # Span events
    error: Optional[str] = None  # Error message if status is ERROR

    def end(self, status: SpanStatus = SpanStatus.OK, error: Optional[str] = None) -> None:
        """End the span and calculate duration."""
        self.end_time = datetime.now(timezone.utc)
        self.status = status
        self.error = error
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            self.duration_ms = delta.total_seconds() * 1000

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the span."""
        self.events.append({
            "name": name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attributes": attributes or {},
        })

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        self.attributes[key] = value

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "span_name": self.span_name,
            "span_kind": self.span_kind.value,
            "service_name": self.service_name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": self.events,
            "error": self.error,
        }


@dataclass
class Metric:
    """
    A metric data point for observability.

    Supports counters, gauges, and histograms.
    """

    metric_name: str  # Metric name (e.g., "l11_rpc_call_duration_seconds")
    metric_type: str  # "counter", "gauge", "histogram"
    value: float  # Metric value
    labels: Dict[str, str] = field(default_factory=dict)  # Metric labels
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    unit: Optional[str] = None  # Unit of measurement (e.g., "seconds", "bytes")

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "metric_name": self.metric_name,
            "metric_type": self.metric_type,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp.isoformat(),
            "unit": self.unit,
        }
