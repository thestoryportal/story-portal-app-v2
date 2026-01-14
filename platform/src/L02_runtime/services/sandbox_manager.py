"""
Sandbox Manager

Configures and validates agent isolation settings.
Maps trust levels to runtime classes and builds security contexts.

Based on Section 3.3.5 and 11.4.1 of agent-runtime-layer-specification-v1.2-final-ASCII.md
"""

from typing import Dict, Any, Optional, Set
import logging

from ..models import (
    TrustLevel,
    RuntimeClass,
    NetworkPolicy,
    SandboxConfiguration,
    ResourceLimits,
)


logger = logging.getLogger(__name__)


class SandboxError(Exception):
    """Sandbox configuration error"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class SandboxManager:
    """
    Manages agent sandbox configuration.

    Responsibilities:
    - Map trust levels to runtime classes
    - Generate security contexts
    - Validate sandbox availability
    - Apply network policies
    """

    # Trust level to RuntimeClass mapping
    TRUST_LEVEL_MAPPING = {
        TrustLevel.TRUSTED: RuntimeClass.RUNC,
        TrustLevel.STANDARD: RuntimeClass.GVISOR,
        TrustLevel.UNTRUSTED: RuntimeClass.KATA,
        TrustLevel.CONFIDENTIAL: RuntimeClass.KATA_CC,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize SandboxManager.

        Args:
            config: Configuration dict with:
                - default_runtime_class: Fallback runtime class
                - default_limits: Default resource limits
                - available_runtimes: Set of available runtime classes
        """
        self.config = config or {}
        self.default_runtime_class = RuntimeClass(
            self.config.get("default_runtime_class", "runc")
        )
        self.default_limits = ResourceLimits(
            cpu=self.config.get("default_cpu", "2"),
            memory=self.config.get("default_memory", "2Gi"),
            tokens_per_hour=self.config.get("default_tokens_per_hour", 100000)
        )

        # Available runtime classes (for local dev, just support runc)
        self._available_runtimes: Set[str] = set(
            self.config.get("available_runtimes", ["runc"])
        )

        logger.info(
            f"SandboxManager initialized with available runtimes: "
            f"{self._available_runtimes}"
        )

    async def initialize(self) -> None:
        """
        Initialize sandbox manager.

        For LocalRuntime: Runtime classes are simulated
        For KubernetesRuntime: Query available RuntimeClasses from cluster
        """
        logger.info("SandboxManager initialization complete")

    def get_sandbox_config(
        self,
        trust_level: TrustLevel,
        custom_limits: Optional[ResourceLimits] = None
    ) -> SandboxConfiguration:
        """
        Generate sandbox configuration for trust level.

        Args:
            trust_level: Code trust classification
            custom_limits: Optional custom resource limits

        Returns:
            Complete sandbox configuration

        Raises:
            SandboxError: If requested runtime class not available
        """
        # Get runtime class for trust level
        runtime_class = self.TRUST_LEVEL_MAPPING.get(
            trust_level,
            self.default_runtime_class
        )

        # Validate availability
        if runtime_class.value not in self._available_runtimes:
            # Fall back to default if not available
            logger.warning(
                f"RuntimeClass {runtime_class.value} not available, "
                f"falling back to {self.default_runtime_class.value}"
            )
            runtime_class = self.default_runtime_class

        # Build configuration
        return SandboxConfiguration.from_trust_level(
            trust_level=trust_level,
            resource_limits=custom_limits or self.default_limits,
            runtime_class=runtime_class
        )

    def validate_sandbox_config(
        self,
        sandbox: SandboxConfiguration
    ) -> None:
        """
        Validate sandbox configuration.

        Args:
            sandbox: Sandbox configuration to validate

        Raises:
            SandboxError: If configuration is invalid
        """
        # Check runtime class availability
        if sandbox.runtime_class.value not in self._available_runtimes:
            raise SandboxError(
                code="E2040",
                message=f"RuntimeClass {sandbox.runtime_class.value} not available"
            )

        # Validate resource limits
        self._validate_resource_limits(sandbox.resource_limits)

        # Validate security context
        self._validate_security_context(sandbox.security_context)

        logger.debug(f"Sandbox configuration validated: {sandbox.to_dict()}")

    def _validate_resource_limits(self, limits: ResourceLimits) -> None:
        """Validate resource limits are within acceptable ranges"""
        # Parse CPU
        cpu_value = self._parse_cpu(limits.cpu)
        if cpu_value <= 0 or cpu_value > 32:
            raise SandboxError(
                code="E2041",
                message=f"CPU limit {limits.cpu} out of range (0-32 cores)"
            )

        # Parse memory
        memory_mb = self._parse_memory(limits.memory)
        if memory_mb <= 0 or memory_mb > 65536:  # 64GB max
            raise SandboxError(
                code="E2042",
                message=f"Memory limit {limits.memory} out of range (0-64Gi)"
            )

        # Validate token limits
        if limits.tokens_per_hour < 0:
            raise SandboxError(
                code="E2043",
                message="Token limit must be non-negative"
            )

    def _validate_security_context(self, context: Dict[str, Any]) -> None:
        """Validate security context settings"""
        # Ensure run_as_non_root is set
        if not context.get("run_as_non_root", False):
            logger.warning("run_as_non_root is False - potential security risk")

        # Ensure privilege escalation is disabled
        if context.get("allow_privilege_escalation", False):
            raise SandboxError(
                code="E2044",
                message="Privilege escalation must be disabled"
            )

        # Ensure capabilities are dropped
        caps = context.get("capabilities", {})
        if "ALL" not in caps.get("drop", []):
            logger.warning("Not all capabilities dropped - potential security risk")

    @staticmethod
    def _parse_cpu(cpu: str) -> float:
        """Parse Kubernetes-style CPU limit"""
        if cpu.endswith("m"):
            return float(cpu[:-1]) / 1000
        return float(cpu)

    @staticmethod
    def _parse_memory(memory: str) -> float:
        """Parse Kubernetes-style memory limit to MB"""
        if memory.endswith("Gi"):
            return float(memory[:-2]) * 1024
        elif memory.endswith("Mi"):
            return float(memory[:-2])
        elif memory.endswith("G"):
            return float(memory[:-1]) * 1000
        elif memory.endswith("M"):
            return float(memory[:-1])
        return 0.0

    def get_network_policy(
        self,
        trust_level: TrustLevel
    ) -> NetworkPolicy:
        """
        Get network policy for trust level.

        Args:
            trust_level: Code trust classification

        Returns:
            Network policy enum
        """
        policy_map = {
            TrustLevel.TRUSTED: NetworkPolicy.ALLOW_EGRESS,
            TrustLevel.STANDARD: NetworkPolicy.RESTRICTED,
            TrustLevel.UNTRUSTED: NetworkPolicy.ISOLATED,
            TrustLevel.CONFIDENTIAL: NetworkPolicy.ISOLATED,
        }
        return policy_map[trust_level]

    def get_available_runtimes(self) -> Set[str]:
        """Get set of available runtime classes"""
        return self._available_runtimes.copy()
