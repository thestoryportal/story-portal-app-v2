"""
L10 Human Interface Layer - Dashboard Models

Models for dashboard data aggregation and display.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class AgentState(str, Enum):
    """Agent execution state."""
    PENDING = "pending"
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class ResourceUtilization:
    """Resource utilization metrics."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    tokens_used: int = 0
    tokens_remaining: int = 0


@dataclass
class AgentStateInfo:
    """Agent state information for dashboard display."""
    agent_id: str
    name: str
    state: AgentState
    tenant_id: str
    current_task_id: Optional[str] = None
    resource_utilization: Optional[ResourceUtilization] = None
    error_count_1h: int = 0
    error_count_24h: int = 0
    last_event_at: Optional[datetime] = None
    uptime_percent: float = 100.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "state": self.state.value if isinstance(self.state, AgentState) else self.state,
            "tenant_id": self.tenant_id,
            "current_task_id": self.current_task_id,
            "resource_utilization": {
                "cpu_percent": self.resource_utilization.cpu_percent,
                "memory_percent": self.resource_utilization.memory_percent,
                "tokens_used": self.resource_utilization.tokens_used,
                "tokens_remaining": self.resource_utilization.tokens_remaining,
            } if self.resource_utilization else None,
            "error_count_1h": self.error_count_1h,
            "error_count_24h": self.error_count_24h,
            "last_event_at": self.last_event_at.isoformat() if self.last_event_at else None,
            "uptime_percent": self.uptime_percent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata,
        }


@dataclass
class AgentsSummary:
    """Summary of all agents."""
    total: int
    by_state: Dict[str, int]
    agents: List[AgentStateInfo]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total": self.total,
            "by_state": self.by_state,
            "agents": [agent.to_dict() for agent in self.agents],
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class MetricPoint:
    """Single metric data point."""
    metric_name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
        }


@dataclass
class MetricsSummary:
    """Summary of key metrics."""
    avg_task_duration_sec: float = 0.0
    task_success_count: int = 0
    task_failure_count: int = 0
    total_tokens_used: int = 0
    avg_response_time_ms: float = 0.0
    error_rate_percent: float = 0.0
    time_window_minutes: int = 60
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "avg_task_duration_sec": self.avg_task_duration_sec,
            "task_success_count": self.task_success_count,
            "task_failure_count": self.task_failure_count,
            "total_tokens_used": self.total_tokens_used,
            "avg_response_time_ms": self.avg_response_time_ms,
            "error_rate_percent": self.error_rate_percent,
            "time_window_minutes": self.time_window_minutes,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class CostSummary:
    """Cost summary."""
    total_cost_dollars: float = 0.0
    cost_by_model: Dict[str, float] = field(default_factory=dict)
    cost_by_agent: Dict[str, float] = field(default_factory=dict)
    projected_monthly_cost: float = 0.0
    budget_remaining: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_cost_dollars": self.total_cost_dollars,
            "cost_by_model": self.cost_by_model,
            "cost_by_agent": self.cost_by_agent,
            "projected_monthly_cost": self.projected_monthly_cost,
            "budget_remaining": self.budget_remaining,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AlertSummary:
    """Active alerts summary."""
    total_alerts: int = 0
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    recent_alerts: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_alerts": self.total_alerts,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "recent_alerts": self.recent_alerts,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class DashboardOverview:
    """Complete dashboard overview."""
    agents: AgentsSummary
    metrics: MetricsSummary
    cost: CostSummary
    alerts: AlertSummary
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agents": self.agents.to_dict(),
            "metrics": self.metrics.to_dict(),
            "cost": self.cost.to_dict(),
            "alerts": self.alerts.to_dict(),
            "timestamp": self.timestamp.isoformat(),
        }
