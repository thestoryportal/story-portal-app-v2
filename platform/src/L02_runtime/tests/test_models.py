"""
Unit tests for data models
"""

import pytest
from datetime import datetime

from ..models import (
    AgentState,
    TrustLevel,
    NetworkPolicy,
    RuntimeClass,
    AgentConfig,
    ResourceLimits,
    SandboxConfiguration,
    SpawnResult,
    AgentInstance,
    ToolDefinition,
)


class TestResourceLimits:
    """Test ResourceLimits model"""

    def test_default_values(self):
        """Test default resource limits"""
        limits = ResourceLimits()
        assert limits.cpu == "2"
        assert limits.memory == "2Gi"
        assert limits.tokens_per_hour == 100000

    def test_custom_values(self):
        """Test custom resource limits"""
        limits = ResourceLimits(
            cpu="4",
            memory="4Gi",
            tokens_per_hour=200000
        )
        assert limits.cpu == "4"
        assert limits.memory == "4Gi"
        assert limits.tokens_per_hour == 200000

    def test_to_dict(self):
        """Test serialization"""
        limits = ResourceLimits(cpu="4", memory="4Gi", tokens_per_hour=200000)
        data = limits.to_dict()
        assert data["cpu"] == "4"
        assert data["memory"] == "4Gi"
        assert data["tokens_per_hour"] == 200000


class TestAgentConfig:
    """Test AgentConfig model"""

    def test_minimal_config(self):
        """Test minimal agent configuration"""
        config = AgentConfig(
            agent_id="agent-123",
            trust_level=TrustLevel.STANDARD
        )
        assert config.agent_id == "agent-123"
        assert config.trust_level == TrustLevel.STANDARD
        assert isinstance(config.resource_limits, ResourceLimits)
        assert len(config.tools) == 0
        assert len(config.environment) == 0

    def test_full_config(self):
        """Test complete agent configuration"""
        tool = ToolDefinition(
            name="search",
            description="Search the web",
            parameters={"query": "string"}
        )

        config = AgentConfig(
            agent_id="agent-456",
            trust_level=TrustLevel.TRUSTED,
            resource_limits=ResourceLimits(cpu="8", memory="8Gi"),
            tools=[tool],
            environment={"API_KEY": "secret"},
            initial_context={"session": "abc"}
        )

        assert config.agent_id == "agent-456"
        assert config.trust_level == TrustLevel.TRUSTED
        assert config.resource_limits.cpu == "8"
        assert len(config.tools) == 1
        assert config.tools[0].name == "search"
        assert config.environment["API_KEY"] == "secret"
        assert config.initial_context["session"] == "abc"

    def test_to_dict(self):
        """Test serialization"""
        config = AgentConfig(
            agent_id="agent-789",
            trust_level=TrustLevel.UNTRUSTED
        )
        data = config.to_dict()
        assert data["agent_id"] == "agent-789"
        assert data["trust_level"] == "untrusted"


class TestSandboxConfiguration:
    """Test SandboxConfiguration model"""

    def test_from_trust_level_trusted(self):
        """Test sandbox config for trusted code"""
        limits = ResourceLimits()
        sandbox = SandboxConfiguration.from_trust_level(
            trust_level=TrustLevel.TRUSTED,
            resource_limits=limits
        )

        assert sandbox.runtime_class == RuntimeClass.RUNC
        assert sandbox.trust_level == TrustLevel.TRUSTED
        assert sandbox.network_policy == NetworkPolicy.ALLOW_EGRESS
        assert sandbox.security_context["read_only_root_filesystem"] == False

    def test_from_trust_level_untrusted(self):
        """Test sandbox config for untrusted code"""
        limits = ResourceLimits()
        sandbox = SandboxConfiguration.from_trust_level(
            trust_level=TrustLevel.UNTRUSTED,
            resource_limits=limits
        )

        assert sandbox.runtime_class == RuntimeClass.KATA
        assert sandbox.trust_level == TrustLevel.UNTRUSTED
        assert sandbox.network_policy == NetworkPolicy.ISOLATED
        assert sandbox.security_context["read_only_root_filesystem"] == True
        assert sandbox.security_context["run_as_non_root"] == True

    def test_from_trust_level_confidential(self):
        """Test sandbox config for confidential code"""
        limits = ResourceLimits()
        sandbox = SandboxConfiguration.from_trust_level(
            trust_level=TrustLevel.CONFIDENTIAL,
            resource_limits=limits
        )

        assert sandbox.runtime_class == RuntimeClass.KATA_CC
        assert sandbox.network_policy == NetworkPolicy.ISOLATED

    def test_custom_runtime_class(self):
        """Test custom runtime class override"""
        limits = ResourceLimits()
        sandbox = SandboxConfiguration.from_trust_level(
            trust_level=TrustLevel.STANDARD,
            resource_limits=limits,
            runtime_class=RuntimeClass.RUNC
        )

        assert sandbox.runtime_class == RuntimeClass.RUNC

    def test_to_dict(self):
        """Test serialization"""
        limits = ResourceLimits()
        sandbox = SandboxConfiguration.from_trust_level(
            trust_level=TrustLevel.STANDARD,
            resource_limits=limits
        )
        data = sandbox.to_dict()

        assert data["runtime_class"] == "gvisor"
        assert data["trust_level"] == "standard"
        assert data["network_policy"] == "restricted"


class TestSpawnResult:
    """Test SpawnResult model"""

    def test_spawn_result(self):
        """Test spawn result creation"""
        result = SpawnResult(
            agent_id="agent-123",
            session_id="session-456",
            state=AgentState.RUNNING,
            sandbox_type="runc",
            container_id="abc123"
        )

        assert result.agent_id == "agent-123"
        assert result.session_id == "session-456"
        assert result.state == AgentState.RUNNING
        assert result.sandbox_type == "runc"
        assert result.container_id == "abc123"

    def test_to_dict(self):
        """Test serialization"""
        result = SpawnResult(
            agent_id="agent-123",
            session_id="session-456",
            state=AgentState.RUNNING,
            sandbox_type="gvisor"
        )
        data = result.to_dict()

        assert data["agent_id"] == "agent-123"
        assert data["state"] == "running"
        assert data["sandbox_type"] == "gvisor"


class TestAgentInstance:
    """Test AgentInstance model"""

    def test_from_spawn_result(self):
        """Test creating instance from spawn result"""
        config = AgentConfig(
            agent_id="agent-789",
            trust_level=TrustLevel.STANDARD
        )

        sandbox = SandboxConfiguration.from_trust_level(
            trust_level=TrustLevel.STANDARD,
            resource_limits=ResourceLimits()
        )

        result = SpawnResult(
            agent_id="agent-789",
            session_id="session-999",
            state=AgentState.RUNNING,
            sandbox_type="gvisor",
            container_id="container-123"
        )

        instance = AgentInstance.from_spawn_result(
            result=result,
            config=config,
            sandbox=sandbox
        )

        assert instance.agent_id == "agent-789"
        assert instance.session_id == "session-999"
        assert instance.state == AgentState.RUNNING
        assert instance.container_id == "container-123"
        assert instance.config == config
        assert instance.sandbox == sandbox

    def test_to_dict(self):
        """Test serialization"""
        config = AgentConfig(
            agent_id="agent-999",
            trust_level=TrustLevel.TRUSTED
        )

        sandbox = SandboxConfiguration.from_trust_level(
            trust_level=TrustLevel.TRUSTED,
            resource_limits=ResourceLimits()
        )

        instance = AgentInstance(
            agent_id="agent-999",
            session_id="session-111",
            state=AgentState.RUNNING,
            config=config,
            sandbox=sandbox
        )

        data = instance.to_dict()
        assert data["agent_id"] == "agent-999"
        assert data["state"] == "running"
        assert "config" in data
        assert "sandbox" in data
