"""
L05 Planning Layer - Resource Models.

Represents resource estimates and constraints for tasks and plans.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class ResourceEstimate:
    """
    Resource requirements estimate for a task.

    Used for feasibility validation and resource budget tracking.
    """

    cpu_cores: float = 1.0  # Estimated CPU cores needed
    memory_mb: int = 512  # Estimated memory in MB
    execution_time_sec: int = 60  # Estimated execution time in seconds
    token_count: int = 0  # Estimated LLM tokens (if applicable)
    disk_mb: int = 0  # Estimated disk space in MB
    network_mb: int = 0  # Estimated network transfer in MB
    cost_usd: float = 0.0  # Estimated cost in USD

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "cpu_cores": self.cpu_cores,
            "memory_mb": self.memory_mb,
            "execution_time_sec": self.execution_time_sec,
            "token_count": self.token_count,
            "disk_mb": self.disk_mb,
            "network_mb": self.network_mb,
            "cost_usd": self.cost_usd,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceEstimate":
        """Create from dictionary representation."""
        return cls(
            cpu_cores=data.get("cpu_cores", 1.0),
            memory_mb=data.get("memory_mb", 512),
            execution_time_sec=data.get("execution_time_sec", 60),
            token_count=data.get("token_count", 0),
            disk_mb=data.get("disk_mb", 0),
            network_mb=data.get("network_mb", 0),
            cost_usd=data.get("cost_usd", 0.0),
        )


@dataclass
class ResourceConstraints:
    """
    Resource limits and constraints for plan execution.

    Enforces budgets and prevents resource oversubscription.
    """

    max_cpu_cores: Optional[float] = None  # Maximum CPU cores
    max_memory_mb: Optional[int] = None  # Maximum memory in MB
    max_execution_time_sec: Optional[int] = None  # Maximum execution time
    max_token_count: Optional[int] = None  # Maximum LLM tokens
    max_disk_mb: Optional[int] = None  # Maximum disk space
    max_network_mb: Optional[int] = None  # Maximum network transfer
    max_cost_usd: Optional[float] = None  # Maximum cost in USD
    max_parallel_tasks: int = 10  # Maximum concurrent tasks

    def is_within_budget(self, estimate: ResourceEstimate) -> tuple[bool, Optional[str]]:
        """
        Check if resource estimate is within constraints.

        Returns:
            (is_valid, error_message)
        """
        if self.max_cpu_cores and estimate.cpu_cores > self.max_cpu_cores:
            return False, f"CPU cores {estimate.cpu_cores} exceeds limit {self.max_cpu_cores}"

        if self.max_memory_mb and estimate.memory_mb > self.max_memory_mb:
            return False, f"Memory {estimate.memory_mb}MB exceeds limit {self.max_memory_mb}MB"

        if self.max_execution_time_sec and estimate.execution_time_sec > self.max_execution_time_sec:
            return False, f"Execution time {estimate.execution_time_sec}s exceeds limit {self.max_execution_time_sec}s"

        if self.max_token_count and estimate.token_count > self.max_token_count:
            return False, f"Token count {estimate.token_count} exceeds limit {self.max_token_count}"

        if self.max_disk_mb and estimate.disk_mb > self.max_disk_mb:
            return False, f"Disk space {estimate.disk_mb}MB exceeds limit {self.max_disk_mb}MB"

        if self.max_network_mb and estimate.network_mb > self.max_network_mb:
            return False, f"Network transfer {estimate.network_mb}MB exceeds limit {self.max_network_mb}MB"

        if self.max_cost_usd and estimate.cost_usd > self.max_cost_usd:
            return False, f"Cost ${estimate.cost_usd} exceeds limit ${self.max_cost_usd}"

        return True, None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "max_cpu_cores": self.max_cpu_cores,
            "max_memory_mb": self.max_memory_mb,
            "max_execution_time_sec": self.max_execution_time_sec,
            "max_token_count": self.max_token_count,
            "max_disk_mb": self.max_disk_mb,
            "max_network_mb": self.max_network_mb,
            "max_cost_usd": self.max_cost_usd,
            "max_parallel_tasks": self.max_parallel_tasks,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceConstraints":
        """Create from dictionary representation."""
        return cls(
            max_cpu_cores=data.get("max_cpu_cores"),
            max_memory_mb=data.get("max_memory_mb"),
            max_execution_time_sec=data.get("max_execution_time_sec"),
            max_token_count=data.get("max_token_count"),
            max_disk_mb=data.get("max_disk_mb"),
            max_network_mb=data.get("max_network_mb"),
            max_cost_usd=data.get("max_cost_usd"),
            max_parallel_tasks=data.get("max_parallel_tasks", 10),
        )
