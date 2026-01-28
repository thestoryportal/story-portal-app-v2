"""
Tests for LocalRuntime Egress Filtering

Tests for network policy and restricted network functionality.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from ..backends.local_runtime import (
    LocalRuntime,
    NetworkPolicy,
    RESTRICTED_NETWORK_NAME,
    ALLOWED_EGRESS_HOSTS,
    ALLOWED_EGRESS_PORTS,
)


@pytest.fixture
def local_runtime():
    """Create LocalRuntime instance"""
    return LocalRuntime(config={})


@pytest.fixture
def mock_docker_client():
    """Create mock Docker client"""
    client = MagicMock()
    client.ping = MagicMock()
    client.networks = MagicMock()
    client.containers = MagicMock()
    client.close = MagicMock()
    return client


class TestNetworkConfiguration:
    """Tests for network configuration"""

    def test_restricted_network_name(self):
        """Test restricted network name constant"""
        assert RESTRICTED_NETWORK_NAME == "l02-restricted"

    def test_allowed_egress_hosts(self):
        """Test allowed egress hosts"""
        assert "127.0.0.1" in ALLOWED_EGRESS_HOSTS
        assert "host.docker.internal" in ALLOWED_EGRESS_HOSTS

    def test_allowed_egress_ports(self):
        """Test allowed egress ports include L01 and L04"""
        assert 8001 in ALLOWED_EGRESS_PORTS  # L01 Data Layer
        assert 8004 in ALLOWED_EGRESS_PORTS  # L04 Model Gateway


class TestNetworkMode:
    """Tests for network mode selection"""

    def test_isolated_network_mode(self, local_runtime):
        """Test ISOLATED policy returns 'none'"""
        mode = local_runtime._get_network_mode(NetworkPolicy.ISOLATED)
        assert mode == "none"

    def test_allow_egress_network_mode(self, local_runtime):
        """Test ALLOW_EGRESS policy returns 'bridge'"""
        mode = local_runtime._get_network_mode(NetworkPolicy.ALLOW_EGRESS)
        assert mode == "bridge"

    def test_restricted_mode_without_network(self, local_runtime):
        """Test RESTRICTED falls back to bridge if network not available"""
        local_runtime._restricted_network = None
        mode = local_runtime._get_network_mode(NetworkPolicy.RESTRICTED)
        assert mode == "bridge"

    def test_restricted_mode_with_network(self, local_runtime):
        """Test RESTRICTED uses restricted network when available"""
        local_runtime._restricted_network = MagicMock()
        mode = local_runtime._get_network_mode(NetworkPolicy.RESTRICTED)
        assert mode == RESTRICTED_NETWORK_NAME


class TestRestrictedNetworkCreation:
    """Tests for restricted network creation"""

    @pytest.mark.asyncio
    async def test_ensure_restricted_network_existing(
        self,
        local_runtime,
        mock_docker_client
    ):
        """Test using existing restricted network"""
        local_runtime.docker_client = mock_docker_client

        # Mock existing network
        existing_network = MagicMock()
        mock_docker_client.networks.list.return_value = [existing_network]

        await local_runtime._ensure_restricted_network()

        # Should use existing network
        assert local_runtime._restricted_network == existing_network
        mock_docker_client.networks.list.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_restricted_network_creates_new(
        self,
        local_runtime,
        mock_docker_client
    ):
        """Test creating new restricted network"""
        local_runtime.docker_client = mock_docker_client

        # Mock no existing network
        mock_docker_client.networks.list.return_value = []

        # Mock network creation
        new_network = MagicMock()
        mock_docker_client.networks.create.return_value = new_network

        await local_runtime._ensure_restricted_network()

        # Should create new network
        assert local_runtime._restricted_network == new_network
        mock_docker_client.networks.create.assert_called_once()

        # Verify network configuration
        call_kwargs = mock_docker_client.networks.create.call_args.kwargs
        assert call_kwargs["name"] == RESTRICTED_NETWORK_NAME
        assert call_kwargs["driver"] == "bridge"
        assert "l02.runtime" in call_kwargs["labels"]

    @pytest.mark.asyncio
    async def test_ensure_restricted_network_handles_failure(
        self,
        local_runtime,
        mock_docker_client
    ):
        """Test graceful handling of network creation failure"""
        from docker.errors import DockerException

        local_runtime.docker_client = mock_docker_client

        # Mock failure
        mock_docker_client.networks.list.return_value = []
        mock_docker_client.networks.create.side_effect = DockerException("Failed")

        # Should not raise, just log warning
        await local_runtime._ensure_restricted_network()

        # Network should remain None
        assert local_runtime._restricted_network is None

    @pytest.mark.asyncio
    async def test_ensure_restricted_network_no_client(self, local_runtime):
        """Test early return when no Docker client"""
        local_runtime.docker_client = None

        await local_runtime._ensure_restricted_network()

        assert local_runtime._restricted_network is None


class TestNetworkRemoval:
    """Tests for restricted network removal"""

    @pytest.mark.asyncio
    async def test_remove_restricted_network_success(
        self,
        local_runtime,
        mock_docker_client
    ):
        """Test successful network removal"""
        local_runtime.docker_client = mock_docker_client

        mock_network = MagicMock()
        mock_network.attrs = {"Containers": {}}  # No connected containers
        mock_network.reload = MagicMock()
        mock_network.remove = MagicMock()
        local_runtime._restricted_network = mock_network

        result = await local_runtime.remove_restricted_network()

        assert result is True
        mock_network.remove.assert_called_once()
        assert local_runtime._restricted_network is None

    @pytest.mark.asyncio
    async def test_remove_restricted_network_with_containers(
        self,
        local_runtime,
        mock_docker_client
    ):
        """Test network not removed if containers connected"""
        local_runtime.docker_client = mock_docker_client

        mock_network = MagicMock()
        mock_network.attrs = {
            "Containers": {"container-1": {}, "container-2": {}}
        }
        mock_network.reload = MagicMock()
        local_runtime._restricted_network = mock_network

        result = await local_runtime.remove_restricted_network()

        assert result is False
        mock_network.remove.assert_not_called()
        assert local_runtime._restricted_network == mock_network

    @pytest.mark.asyncio
    async def test_remove_restricted_network_no_client(self, local_runtime):
        """Test removal returns False when no Docker client"""
        local_runtime.docker_client = None
        local_runtime._restricted_network = None

        result = await local_runtime.remove_restricted_network()

        assert result is False

    @pytest.mark.asyncio
    async def test_remove_restricted_network_no_network(
        self,
        local_runtime,
        mock_docker_client
    ):
        """Test removal returns False when no restricted network"""
        local_runtime.docker_client = mock_docker_client
        local_runtime._restricted_network = None

        result = await local_runtime.remove_restricted_network()

        assert result is False


class TestContainerNetworkPolicy:
    """Tests for container spawn with network policy"""

    @pytest.mark.asyncio
    async def test_container_config_isolated(self, local_runtime):
        """Test container config uses 'none' for ISOLATED"""
        from ..models import (
            AgentConfig,
            SandboxConfiguration,
            ResourceLimits,
            RuntimeClass,
            TrustLevel,
        )

        config = AgentConfig(
            agent_id="test-agent",
            trust_level=TrustLevel.UNTRUSTED,
            environment={},
        )

        sandbox = SandboxConfiguration(
            runtime_class=RuntimeClass.GVISOR,
            trust_level=TrustLevel.UNTRUSTED,
            resource_limits=ResourceLimits(cpu="100m", memory="128Mi"),
            network_policy=NetworkPolicy.ISOLATED,
            security_context={},
        )

        container_config = local_runtime._build_container_config(
            config=config,
            sandbox=sandbox,
            image="test:latest",
            command=None,
            environment={},
        )

        assert container_config["network_mode"] == "none"

    @pytest.mark.asyncio
    async def test_container_config_restricted_with_network(self, local_runtime):
        """Test container config uses restricted network when available"""
        from ..models import (
            AgentConfig,
            SandboxConfiguration,
            ResourceLimits,
            RuntimeClass,
            TrustLevel,
        )

        # Set up restricted network
        local_runtime._restricted_network = MagicMock()

        config = AgentConfig(
            agent_id="test-agent",
            trust_level=TrustLevel.STANDARD,
            environment={},
        )

        sandbox = SandboxConfiguration(
            runtime_class=RuntimeClass.RUNC,
            trust_level=TrustLevel.STANDARD,
            resource_limits=ResourceLimits(cpu="100m", memory="128Mi"),
            network_policy=NetworkPolicy.RESTRICTED,
            security_context={},
        )

        container_config = local_runtime._build_container_config(
            config=config,
            sandbox=sandbox,
            image="test:latest",
            command=None,
            environment={},
        )

        assert container_config["network_mode"] == RESTRICTED_NETWORK_NAME


class TestCleanup:
    """Tests for cleanup"""

    @pytest.mark.asyncio
    async def test_cleanup_clears_network(
        self,
        local_runtime,
        mock_docker_client
    ):
        """Test cleanup clears restricted network reference"""
        local_runtime.docker_client = mock_docker_client
        local_runtime._restricted_network = MagicMock()
        local_runtime._container_registry = {"agent-1": "container-1"}

        await local_runtime.cleanup()

        assert local_runtime.docker_client is None
        assert local_runtime._restricted_network is None
        assert len(local_runtime._container_registry) == 0
