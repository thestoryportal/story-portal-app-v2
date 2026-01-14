"""
Unit tests for Sandbox Manager
"""

import pytest

from ..models import TrustLevel, RuntimeClass, NetworkPolicy, ResourceLimits
from ..services import SandboxManager, SandboxError


class TestSandboxManager:
    """Test Sandbox Manager"""

    @pytest.fixture
    def manager(self):
        """Create sandbox manager instance"""
        config = {
            "default_runtime_class": "runc",
            "available_runtimes": ["runc"],
            "default_cpu": "2",
            "default_memory": "2Gi",
            "default_tokens_per_hour": 100000
        }
        return SandboxManager(config)

    @pytest.mark.asyncio
    async def test_initialize(self, manager):
        """Test manager initialization"""
        await manager.initialize()
        assert manager is not None

    def test_get_sandbox_config_trusted(self, manager):
        """Test sandbox config for trusted code"""
        sandbox = manager.get_sandbox_config(TrustLevel.TRUSTED)

        assert sandbox.trust_level == TrustLevel.TRUSTED
        assert sandbox.runtime_class == RuntimeClass.RUNC
        assert sandbox.network_policy == NetworkPolicy.ALLOW_EGRESS
        assert sandbox.security_context["read_only_root_filesystem"] == False

    def test_get_sandbox_config_untrusted(self, manager):
        """Test sandbox config for untrusted code"""
        sandbox = manager.get_sandbox_config(TrustLevel.UNTRUSTED)

        assert sandbox.trust_level == TrustLevel.UNTRUSTED
        # Falls back to runc since kata not available
        assert sandbox.runtime_class == RuntimeClass.RUNC
        assert sandbox.network_policy == NetworkPolicy.ISOLATED

    def test_get_sandbox_config_custom_limits(self, manager):
        """Test sandbox config with custom resource limits"""
        custom_limits = ResourceLimits(
            cpu="4",
            memory="4Gi",
            tokens_per_hour=200000
        )

        sandbox = manager.get_sandbox_config(
            TrustLevel.STANDARD,
            custom_limits=custom_limits
        )

        assert sandbox.resource_limits.cpu == "4"
        assert sandbox.resource_limits.memory == "4Gi"
        assert sandbox.resource_limits.tokens_per_hour == 200000

    def test_validate_sandbox_config_valid(self, manager):
        """Test validation of valid config"""
        sandbox = manager.get_sandbox_config(TrustLevel.STANDARD)
        manager.validate_sandbox_config(sandbox)  # Should not raise

    def test_validate_sandbox_config_invalid_runtime(self, manager):
        """Test validation fails for unavailable runtime"""
        sandbox = manager.get_sandbox_config(TrustLevel.STANDARD)
        sandbox.runtime_class = RuntimeClass.KATA  # Not in available_runtimes

        with pytest.raises(SandboxError) as exc_info:
            manager.validate_sandbox_config(sandbox)

        assert exc_info.value.code == "E2040"

    def test_validate_sandbox_config_invalid_cpu(self, manager):
        """Test validation fails for invalid CPU"""
        limits = ResourceLimits(cpu="99", memory="2Gi")  # Exceeds max
        sandbox = manager.get_sandbox_config(TrustLevel.STANDARD, limits)

        with pytest.raises(SandboxError) as exc_info:
            manager.validate_sandbox_config(sandbox)

        assert exc_info.value.code == "E2041"

    def test_validate_sandbox_config_invalid_memory(self, manager):
        """Test validation fails for invalid memory"""
        limits = ResourceLimits(cpu="2", memory="100Gi")  # Exceeds max
        sandbox = manager.get_sandbox_config(TrustLevel.STANDARD, limits)

        with pytest.raises(SandboxError) as exc_info:
            manager.validate_sandbox_config(sandbox)

        assert exc_info.value.code == "E2042"

    def test_get_network_policy(self, manager):
        """Test network policy mapping"""
        assert manager.get_network_policy(TrustLevel.TRUSTED) == NetworkPolicy.ALLOW_EGRESS
        assert manager.get_network_policy(TrustLevel.STANDARD) == NetworkPolicy.RESTRICTED
        assert manager.get_network_policy(TrustLevel.UNTRUSTED) == NetworkPolicy.ISOLATED
        assert manager.get_network_policy(TrustLevel.CONFIDENTIAL) == NetworkPolicy.ISOLATED

    def test_get_available_runtimes(self, manager):
        """Test getting available runtimes"""
        runtimes = manager.get_available_runtimes()
        assert "runc" in runtimes

    def test_parse_cpu(self, manager):
        """Test CPU parsing"""
        assert manager._parse_cpu("2") == 2.0
        assert manager._parse_cpu("500m") == 0.5
        assert manager._parse_cpu("1000m") == 1.0

    def test_parse_memory(self, manager):
        """Test memory parsing"""
        assert manager._parse_memory("2Gi") == 2048
        assert manager._parse_memory("512Mi") == 512
        assert manager._parse_memory("1G") == 1000
        assert manager._parse_memory("500M") == 500
