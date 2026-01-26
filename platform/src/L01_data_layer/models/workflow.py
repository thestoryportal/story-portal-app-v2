"""
Workflow Builder Data Models

Pydantic models for the enhanced workflow orchestration system.
Supports DAG execution, saga pattern, human-in-the-loop, and nested workflows.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class WorkflowStatus(str, Enum):
    """Status of a workflow definition."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ExecutionStatus(str, Enum):
    """Status of a workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPENSATING = "compensating"


class NodeExecutionStatus(str, Enum):
    """Status of a single node execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    COMPENSATED = "compensated"


class NodeType(str, Enum):
    """Type of workflow node."""
    # Existing types
    AGENT = "agent"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"
    END = "end"
    # New types for enhanced workflows
    SUBWORKFLOW = "subworkflow"
    EVENT_TRIGGER = "event_trigger"
    HUMAN_APPROVAL = "human_approval"
    SERVICE = "service"
    WAIT = "wait"
    TRANSFORM = "transform"


class TriggerType(str, Enum):
    """Type of workflow trigger."""
    EVENT = "event"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"
    MANUAL = "manual"


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalRequestType(str, Enum):
    """Type of approval request."""
    APPROVAL = "approval"
    CONFIRMATION = "confirmation"
    INPUT_REQUIRED = "input_required"


class CompensationStatus(str, Enum):
    """Status of compensation/rollback."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowParadigm(str, Enum):
    """Execution paradigm for workflows."""
    DAG = "dag"
    SEQUENTIAL = "sequential"
    EVENT_DRIVEN = "event_driven"
    STATE_MACHINE = "state_machine"
    HYBRID = "hybrid"


class WorkflowVisibility(str, Enum):
    """Visibility/sharing level for workflows."""
    PRIVATE = "private"
    TEAM = "team"
    PUBLIC = "public"


# ============================================================================
# Configuration Models
# ============================================================================

class RetryConfig(BaseModel):
    """Configuration for retry behavior."""
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    initial_delay_ms: int = Field(default=1000, ge=100, description="Initial delay in milliseconds")
    max_delay_ms: int = Field(default=30000, description="Maximum delay in milliseconds")
    backoff_multiplier: float = Field(default=2.0, ge=1.0, description="Exponential backoff multiplier")
    retryable_errors: List[str] = Field(default_factory=list, description="Error codes that trigger retry")


class CompensationConfig(BaseModel):
    """Configuration for saga compensation/rollback."""
    service: str = Field(..., description="Service to call for compensation")
    method: str = Field(..., description="Method to invoke")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for compensation")
    order: int = Field(default=0, description="Execution order (reverse of forward)")
    timeout_seconds: int = Field(default=30, description="Timeout for compensation action")


class TimeoutConfig(BaseModel):
    """Timeout configuration for nodes."""
    execution_timeout_seconds: int = Field(default=300, description="Max execution time")
    idle_timeout_seconds: int = Field(default=60, description="Max idle time waiting for input")


# ============================================================================
# Node Definition Models
# ============================================================================

class WorkflowRoute(BaseModel):
    """Route from a node to another node."""
    target_node_id: str = Field(..., description="Target node ID")
    condition: Optional[str] = Field(None, description="Condition expression for this route")
    label: Optional[str] = Field(None, description="Human-readable label for the route")


class WorkflowNodeDefinition(BaseModel):
    """Definition of a single workflow node."""
    node_id: str = Field(..., description="Unique node identifier")
    node_type: NodeType = Field(..., description="Type of node")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(None, description="Node description")

    # Execution configuration
    config: Dict[str, Any] = Field(default_factory=dict, description="Type-specific configuration")
    routes: List[WorkflowRoute] = Field(default_factory=list, description="Outgoing routes")

    # Service invocation (for SERVICE node type)
    service: Optional[str] = Field(None, description="Service name to invoke")
    method: Optional[str] = Field(None, description="Method to call")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters template")

    # Agent configuration (for AGENT node type)
    agent_id: Optional[str] = Field(None, description="Agent ID for agent nodes")
    agent_config: Dict[str, Any] = Field(default_factory=dict, description="Agent-specific config")

    # Subworkflow (for SUBWORKFLOW node type)
    subworkflow_id: Optional[str] = Field(None, description="Nested workflow ID")

    # Human approval (for HUMAN_APPROVAL node type)
    approval_message: Optional[str] = Field(None, description="Message to show for approval")
    approval_timeout_seconds: Optional[int] = Field(None, description="Approval timeout")

    # Resilience
    retry_config: Optional[RetryConfig] = Field(None, description="Retry configuration")
    timeout_seconds: int = Field(default=300, description="Execution timeout")
    compensation: Optional[CompensationConfig] = Field(None, description="Compensation for rollback")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class WorkflowEdgeDefinition(BaseModel):
    """Definition of an edge between nodes."""
    source_node_id: str = Field(..., description="Source node ID")
    target_node_id: str = Field(..., description="Target node ID")
    condition: Optional[str] = Field(None, description="Condition expression")
    label: Optional[str] = Field(None, description="Edge label")


class WorkflowParameter(BaseModel):
    """Input parameter definition for a workflow."""
    name: str = Field(..., description="Parameter name")
    param_type: str = Field(default="string", description="Parameter type (string, number, boolean, object, array)")
    description: Optional[str] = Field(None, description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Optional[Any] = Field(None, description="Default value")
    validation: Optional[Dict[str, Any]] = Field(None, description="Validation rules")


# ============================================================================
# Workflow Definition Models
# ============================================================================

class WorkflowDefinitionCreate(BaseModel):
    """Request to create a new workflow definition."""
    name: str = Field(..., min_length=1, max_length=255, description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    version: str = Field(default="1.0.0", description="Semantic version")
    paradigm: WorkflowParadigm = Field(default=WorkflowParadigm.DAG, description="Execution paradigm")

    # Graph structure
    nodes: List[WorkflowNodeDefinition] = Field(..., min_length=1, description="Workflow nodes")
    edges: List[WorkflowEdgeDefinition] = Field(default_factory=list, description="Node connections")
    entry_node_id: str = Field(..., description="Entry point node ID")

    # Parameters
    parameters: List[WorkflowParameter] = Field(default_factory=list, description="Input parameters")

    # Organization
    category: str = Field(default="general", description="Workflow category")
    tags: List[str] = Field(default_factory=list, description="Tags for discovery")
    visibility: WorkflowVisibility = Field(default=WorkflowVisibility.PRIVATE)

    # AI generation metadata
    generated_from: Optional[str] = Field(None, description="Original NL prompt if AI-generated")
    ai_optimizations: List[str] = Field(default_factory=list, description="Applied AI optimizations")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowDefinitionUpdate(BaseModel):
    """Request to update a workflow definition."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    version: Optional[str] = None
    nodes: Optional[List[WorkflowNodeDefinition]] = None
    edges: Optional[List[WorkflowEdgeDefinition]] = None
    entry_node_id: Optional[str] = None
    parameters: Optional[List[WorkflowParameter]] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[WorkflowStatus] = None
    visibility: Optional[WorkflowVisibility] = None
    metadata: Optional[Dict[str, Any]] = None


class WorkflowDefinition(BaseModel):
    """Full workflow definition model."""
    id: UUID = Field(default_factory=uuid4)
    workflow_id: str = Field(..., description="Unique workflow identifier")
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    paradigm: WorkflowParadigm = WorkflowParadigm.DAG

    # Graph stored as JSONB
    definition: Dict[str, Any] = Field(..., description="Full graph definition")

    # Organization
    category: str = "general"
    tags: List[str] = Field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    owner_agent_id: Optional[UUID] = None
    visibility: WorkflowVisibility = WorkflowVisibility.PRIVATE

    # AI metadata
    generated_from: Optional[str] = None
    ai_optimizations: List[str] = Field(default_factory=list)

    # Versioning
    parent_version: Optional[str] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


# ============================================================================
# Workflow Execution Models
# ============================================================================

class WorkflowExecutionCreate(BaseModel):
    """Request to start a workflow execution."""
    workflow_id: str = Field(..., description="Workflow to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Input parameters")
    agent_id: Optional[UUID] = Field(None, description="Agent initiating execution")
    session_id: Optional[str] = Field(None, description="Session context")
    parent_execution_id: Optional[str] = Field(None, description="Parent for nested workflows")
    async_mode: bool = Field(default=True, description="Run asynchronously")
    trace_id: Optional[str] = Field(None, description="Distributed tracing ID")


class WorkflowExecutionUpdate(BaseModel):
    """Request to update an execution."""
    status: Optional[ExecutionStatus] = None
    current_node_id: Optional[str] = None
    execution_state: Optional[Dict[str, Any]] = None
    output_result: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    compensation_required: Optional[bool] = None
    compensation_status: Optional[CompensationStatus] = None


class WorkflowExecution(BaseModel):
    """Full workflow execution model."""
    id: UUID = Field(default_factory=uuid4)
    execution_id: str = Field(..., description="Unique execution identifier")
    workflow_id: str
    workflow_version: str

    # Context
    agent_id: Optional[UUID] = None
    session_id: Optional[str] = None
    parent_execution_id: Optional[str] = None

    # I/O
    input_parameters: Dict[str, Any] = Field(default_factory=dict)
    output_result: Optional[Dict[str, Any]] = None

    # State
    status: ExecutionStatus = ExecutionStatus.PENDING
    current_node_id: Optional[str] = None
    execution_state: Dict[str, Any] = Field(default_factory=dict)
    checkpoint_id: Optional[str] = None

    # Error handling
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    # Compensation/Saga
    compensation_required: bool = False
    compensation_status: Optional[CompensationStatus] = None
    compensated_nodes: List[str] = Field(default_factory=list)

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    # Tracing
    trace_id: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


# ============================================================================
# Node Execution Models
# ============================================================================

class NodeExecutionCreate(BaseModel):
    """Record a node execution."""
    execution_id: str = Field(..., description="Parent workflow execution")
    node_id: str = Field(..., description="Node being executed")
    node_type: NodeType
    input_data: Dict[str, Any] = Field(default_factory=dict)


class NodeExecutionUpdate(BaseModel):
    """Update a node execution."""
    status: Optional[NodeExecutionStatus] = None
    output_data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: Optional[int] = None
    compensated: Optional[bool] = None


class WorkflowNodeExecution(BaseModel):
    """Full node execution model."""
    id: UUID = Field(default_factory=uuid4)
    node_execution_id: str
    execution_id: str
    node_id: str
    node_type: NodeType

    status: NodeExecutionStatus = NodeExecutionStatus.PENDING
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None

    error_code: Optional[str] = None
    error_message: Optional[str] = None

    retry_count: int = 0
    max_retries: int = 3

    compensation_action: Optional[Dict[str, Any]] = None
    compensated: bool = False

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


# ============================================================================
# Trigger Models
# ============================================================================

class EventTriggerConfig(BaseModel):
    """Configuration for event-based triggers."""
    event_type: str = Field(..., description="Event type to watch")
    event_source: Optional[str] = Field(None, description="Event source filter")
    filter_expression: Optional[str] = Field(None, description="Event filter expression")


class ScheduleTriggerConfig(BaseModel):
    """Configuration for scheduled triggers."""
    cron_expression: str = Field(..., description="Cron expression")
    timezone: str = Field(default="UTC", description="Timezone for schedule")


class WebhookTriggerConfig(BaseModel):
    """Configuration for webhook triggers."""
    endpoint_path: str = Field(..., description="Webhook endpoint path")
    auth_type: str = Field(default="none", description="Authentication type")
    secret: Optional[str] = Field(None, description="Webhook secret for verification")


class WorkflowTriggerCreate(BaseModel):
    """Request to create a workflow trigger."""
    workflow_id: str = Field(..., description="Workflow to trigger")
    trigger_type: TriggerType
    trigger_config: Dict[str, Any] = Field(..., description="Type-specific configuration")
    enabled: bool = Field(default=True)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowTriggerUpdate(BaseModel):
    """Request to update a trigger."""
    trigger_config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class WorkflowTrigger(BaseModel):
    """Full workflow trigger model."""
    id: UUID = Field(default_factory=uuid4)
    trigger_id: str
    workflow_id: str
    trigger_type: TriggerType
    trigger_config: Dict[str, Any]
    enabled: bool = True
    last_triggered_at: Optional[datetime] = None
    trigger_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


# ============================================================================
# Approval Request Models
# ============================================================================

class ApprovalRequestCreate(BaseModel):
    """Request to create an approval request."""
    execution_id: str = Field(..., description="Workflow execution")
    node_id: str = Field(..., description="Node requiring approval")
    request_type: ApprovalRequestType
    request_message: Optional[str] = Field(None, description="Message for approver")
    request_data: Dict[str, Any] = Field(default_factory=dict, description="Context data")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")


class ApprovalResponse(BaseModel):
    """Response to an approval request."""
    approved: bool = Field(..., description="Whether request was approved")
    responded_by: str = Field(..., description="Who responded")
    response_data: Dict[str, Any] = Field(default_factory=dict, description="Additional response data")


class WorkflowApprovalRequest(BaseModel):
    """Full approval request model."""
    id: UUID = Field(default_factory=uuid4)
    approval_id: str
    execution_id: str
    node_id: str
    request_type: ApprovalRequestType
    request_message: Optional[str] = None
    request_data: Dict[str, Any] = Field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    responded_by: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None
    responded_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


# ============================================================================
# Checkpoint Models
# ============================================================================

class WorkflowCheckpoint(BaseModel):
    """Checkpoint for resumable workflows."""
    checkpoint_id: str = Field(default_factory=lambda: str(uuid4()))
    execution_id: str
    node_id: str
    execution_state: Dict[str, Any]
    completed_nodes: List[str] = Field(default_factory=list)
    variable_context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Response Models
# ============================================================================

class WorkflowExecutionResponse(BaseModel):
    """Response for workflow execution queries."""
    execution: WorkflowExecution
    node_executions: List[WorkflowNodeExecution] = Field(default_factory=list)
    pending_approvals: List[WorkflowApprovalRequest] = Field(default_factory=list)


class WorkflowListResponse(BaseModel):
    """Response for workflow listing."""
    workflows: List[WorkflowDefinition]
    total: int
    offset: int
    limit: int


class ExecutionListResponse(BaseModel):
    """Response for execution listing."""
    executions: List[WorkflowExecution]
    total: int
    offset: int
    limit: int
