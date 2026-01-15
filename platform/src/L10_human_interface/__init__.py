"""
L10 Human Interface Layer

Provides real-time dashboard, control operations, and human-in-the-loop workflows
for the Agentic AI Workforce platform.

Key Components:
- Dashboard Service: Aggregate agent state and metrics from L02/L06
- WebSocket Gateway: Real-time event streaming to browsers
- Control Service: Pause/resume agents with idempotency and locking
- Event Service: Query event history with filtering
- Alert Service: Alert management and acknowledgment
- Audit Service: Audit trail logging and querying
- Cost Service: Cost tracking and attribution

Error Codes: E10000-E10999
"""

from .models import ErrorCode, InterfaceError
from .config import L10Settings, get_settings

__version__ = "1.0.0"

__all__ = [
    "ErrorCode",
    "InterfaceError",
    "L10Settings",
    "get_settings",
]
