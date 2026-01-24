"""
Unit Tests - Models

Tests for Pydantic models including validation, serialization, and deserialization.
"""

import pytest
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import ValidationError
import sys
import os

# Add platform src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from L01_data_layer.models.agent import Agent, AgentCreate, AgentUpdate, AgentStatus
from L01_data_layer.models.goal import Goal, GoalCreate, GoalUpdate, GoalStatus
from L01_data_layer.models.tool import Tool, ToolCreate, ToolUpdate

pytestmark = pytest.mark.unit


class TestAgentModel:
    """Test Agent model validation and behavior."""

    def test_agent_create_valid(self):
        """Test creating a valid agent."""
        agent_data = AgentCreate(
            name="TestAgent",
            agent_type="task",
            configuration={"max_iterations": 10},
            metadata={"test": True}
        )

        assert agent_data.name == "TestAgent"
        assert agent_data.agent_type == "task"
        assert agent_data.configuration["max_iterations"] == 10

    def test_agent_create_minimal(self):
        """Test creating agent with minimal data."""
        agent_data = AgentCreate(name="MinimalAgent")

        assert agent_data.name == "MinimalAgent"
        assert agent_data.agent_type == "general"
        assert agent_data.configuration == {}
        assert agent_data.metadata == {}

    def test_agent_create_invalid_missing_name(self):
        """Test that missing name is rejected."""
        with pytest.raises(ValidationError):
            AgentCreate()  # name is required

    def test_agent_model_with_defaults(self):
        """Test Agent model with default values."""
        agent = Agent(
            did="did:example:123",
            name="DefaultAgent"
        )

        assert agent.name == "DefaultAgent"
        assert agent.agent_type == "general"
        assert agent.status == AgentStatus.CREATED
        assert isinstance(agent.id, UUID)
        assert isinstance(agent.created_at, datetime)
        assert isinstance(agent.updated_at, datetime)

    def test_agent_status_enum(self):
        """Test AgentStatus enum values."""
        assert AgentStatus.CREATED == "created"
        assert AgentStatus.ACTIVE == "active"
        assert AgentStatus.IDLE == "idle"
        assert AgentStatus.BUSY == "busy"
        assert AgentStatus.SUSPENDED == "suspended"
        assert AgentStatus.TERMINATED == "terminated"
        assert AgentStatus.ERROR == "error"

    def test_agent_update_partial(self):
        """Test partial agent updates."""
        update = AgentUpdate(name="UpdatedName")

        assert update.name == "UpdatedName"
        assert update.agent_type is None
        assert update.status is None

    def test_agent_update_status_change(self):
        """Test updating agent status."""
        update = AgentUpdate(status=AgentStatus.ACTIVE)

        assert update.status == AgentStatus.ACTIVE

    def test_agent_serialization(self):
        """Test agent model serialization."""
        agent = Agent(
            did="did:example:123",
            name="SerializationTest"
        )

        # Convert to dict
        agent_dict = agent.model_dump()

        assert isinstance(agent_dict, dict)
        assert agent_dict["name"] == "SerializationTest"
        assert "id" in agent_dict
        assert "created_at" in agent_dict


class TestGoalModel:
    """Test Goal model validation and behavior."""

    def test_goal_create_valid(self):
        """Test creating a valid goal."""
        agent_id = uuid4()
        goal_data = GoalCreate(
            agent_id=agent_id,
            description="Test goal",
            success_criteria=[{"metric": "completion"}],
            priority=8
        )

        assert goal_data.agent_id == agent_id
        assert goal_data.description == "Test goal"
        assert goal_data.success_criteria[0]["metric"] == "completion"
        assert goal_data.priority == 8

    def test_goal_create_minimal(self):
        """Test creating goal with minimal data."""
        agent_id = uuid4()
        goal_data = GoalCreate(
            agent_id=agent_id,
            description="Minimal goal"
        )

        assert goal_data.agent_id == agent_id
        assert goal_data.description == "Minimal goal"

    def test_goal_update_partial(self):
        """Test partial goal updates."""
        update = GoalUpdate(description="Updated description")

        assert update.description == "Updated description"
        assert update.status is None


class TestToolModel:
    """Test Tool model validation and behavior."""

    def test_tool_create_valid(self):
        """Test creating a valid tool."""
        tool_data = ToolCreate(
            name="TestTool",
            tool_type="function",
            schema_def={"type": "function", "parameters": {"param1": "string"}},
            permissions={"execute": True}
        )

        assert tool_data.name == "TestTool"
        assert tool_data.tool_type == "function"
        assert tool_data.schema_def["parameters"]["param1"] == "string"

    def test_tool_create_minimal(self):
        """Test creating tool with minimal required data."""
        tool_data = ToolCreate(
            name="MinimalTool",
            schema_def={"type": "function"}
        )

        assert tool_data.name == "MinimalTool"
        assert tool_data.enabled is True  # default

    def test_tool_update_partial(self):
        """Test partial tool updates."""
        update = ToolUpdate(description="Updated description")

        assert update.description == "Updated description"
        assert update.schema_def is None
        assert update.enabled is None


class TestModelValidation:
    """Test model validation rules."""

    def test_invalid_type_conversion(self):
        """Test that invalid type conversion is rejected."""
        with pytest.raises(ValidationError):
            AgentCreate(name=12345)  # Name should be string

    def test_extra_fields_allowed(self):
        """Test handling of extra fields."""
        # By default, Pydantic models allow extra fields in configuration
        agent_data = AgentCreate(
            name="TestAgent",
            configuration={"extra": "field"}
        )

        assert agent_data.configuration["extra"] == "field"

    def test_uuid_validation(self):
        """Test UUID field validation."""
        # Valid UUID
        agent = Agent(
            id=uuid4(),
            did="did:example:123",
            name="TestAgent"
        )

        assert isinstance(agent.id, UUID)

    def test_datetime_validation(self):
        """Test datetime field validation."""
        agent = Agent(
            did="did:example:123",
            name="TestAgent"
        )

        assert isinstance(agent.created_at, datetime)
        assert isinstance(agent.updated_at, datetime)


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_model_to_json(self):
        """Test model to JSON conversion."""
        agent = Agent(
            did="did:example:123",
            name="JSONTest"
        )

        json_str = agent.model_dump_json()

        assert isinstance(json_str, str)
        assert "JSONTest" in json_str

    def test_model_from_dict(self):
        """Test creating model from dictionary."""
        agent_dict = {
            "id": str(uuid4()),
            "did": "did:example:123",
            "name": "DictTest",
            "agent_type": "general",
            "status": "created",
            "configuration": {},
            "metadata": {},
            "resource_limits": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        agent = Agent(**agent_dict)

        assert agent.name == "DictTest"
        assert agent.did == "did:example:123"

    def test_model_copy(self):
        """Test model copying."""
        agent1 = Agent(
            did="did:example:123",
            name="Original"
        )

        # model_copy preserves id by default, update with new id for a fresh copy
        agent2 = agent1.model_copy(update={"name": "Copy", "id": uuid4()})

        assert agent1.name == "Original"
        assert agent2.name == "Copy"
        assert agent1.id != agent2.id  # Different IDs due to explicit update


class TestModelDefaults:
    """Test model default values."""

    def test_agent_default_type(self):
        """Test agent default type."""
        agent = AgentCreate(name="DefaultTypeTest")

        assert agent.agent_type == "general"

    def test_agent_default_status(self):
        """Test agent default status."""
        agent = Agent(
            did="did:example:123",
            name="DefaultStatusTest"
        )

        assert agent.status == AgentStatus.CREATED

    def test_agent_default_collections(self):
        """Test agent default collection fields."""
        agent = AgentCreate(name="DefaultCollectionsTest")

        assert agent.configuration == {}
        assert agent.metadata == {}
        assert agent.resource_limits == {}


class TestModelImmutability:
    """Test model immutability where applicable."""

    def test_model_field_assignment(self):
        """Test that model fields can be updated."""
        agent = Agent(
            did="did:example:123",
            name="Original"
        )

        # Pydantic v2 models are mutable by default
        agent.name = "Updated"
        assert agent.name == "Updated"
