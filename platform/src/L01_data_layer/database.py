"""
Database connection and schema management for L01 Data Layer.
"""

import asyncpg
from typing import Optional
import logging

logger = logging.getLogger(__name__)

DATABASE_SCHEMA = """
-- Core event sourcing
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(255) NOT NULL,
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id UUID NOT NULL,
    payload JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    version INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_events_aggregate ON events(aggregate_type, aggregate_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);

-- L02 Agent Runtime
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    did VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    agent_type VARCHAR(100) DEFAULT 'general',
    status VARCHAR(50) DEFAULT 'created',
    configuration JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    resource_limits JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- L03 Tool Execution
CREATE TABLE IF NOT EXISTS tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    tool_type VARCHAR(100) DEFAULT 'function',
    schema_def JSONB NOT NULL,
    permissions JSONB DEFAULT '{}',
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invocation_id UUID UNIQUE NOT NULL,
    tool_id UUID REFERENCES tools(id),
    tool_name VARCHAR(255) NOT NULL,
    tool_version VARCHAR(50),

    -- Agent context
    agent_id UUID REFERENCES agents(id),
    agent_did VARCHAR(255),
    tenant_id VARCHAR(255),
    session_id VARCHAR(255),
    parent_sandbox_id VARCHAR(255),

    -- Execution details
    input_params JSONB NOT NULL,
    output_result JSONB,
    status VARCHAR(50) DEFAULT 'pending',

    -- Error information
    error_code VARCHAR(100),
    error_message TEXT,
    error_details JSONB,
    retryable BOOLEAN DEFAULT false,

    -- Execution metadata (resource usage, performance)
    duration_ms INTEGER,
    cpu_used_millicore_seconds INTEGER,
    memory_peak_mb INTEGER,
    network_bytes_sent INTEGER,
    network_bytes_received INTEGER,

    -- Phase 15/16 integration
    documents_accessed JSONB DEFAULT '[]',
    checkpoints_created JSONB DEFAULT '[]',
    checkpoint_ref VARCHAR(255),

    -- Execution options
    async_mode BOOLEAN DEFAULT false,
    priority INTEGER DEFAULT 5,
    idempotency_key VARCHAR(255),
    require_approval BOOLEAN DEFAULT false,

    -- Resource limits
    cpu_millicore_limit INTEGER,
    memory_mb_limit INTEGER,
    timeout_seconds INTEGER,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tool_executions_invocation ON tool_executions(invocation_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_tool ON tool_executions(tool_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_agent ON tool_executions(agent_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_status ON tool_executions(status);
CREATE INDEX IF NOT EXISTS idx_tool_executions_session ON tool_executions(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_tenant ON tool_executions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_created ON tool_executions(created_at);

-- L04 Model Gateway
CREATE TABLE IF NOT EXISTS model_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(255) UNIQUE NOT NULL,

    -- Agent context
    agent_id UUID REFERENCES agents(id),
    agent_did VARCHAR(255),
    tenant_id VARCHAR(255),
    session_id VARCHAR(255),

    -- Model info
    model_provider VARCHAR(100) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    model_id VARCHAR(255),

    -- Token usage
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cached_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,

    -- Performance
    latency_ms INTEGER,
    cached BOOLEAN DEFAULT false,

    -- Cost
    cost_estimate DECIMAL(10,6),
    cost_input_cents DECIMAL(10,6),
    cost_output_cents DECIMAL(10,6),
    cost_cached_cents DECIMAL(10,6),

    -- Response metadata
    finish_reason VARCHAR(50),
    error_message TEXT,
    response_status VARCHAR(50) DEFAULT 'success',

    -- Additional metadata
    metadata JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_model_usage_request ON model_usage(request_id);
CREATE INDEX IF NOT EXISTS idx_model_usage_agent ON model_usage(agent_id);
CREATE INDEX IF NOT EXISTS idx_model_usage_agent_did ON model_usage(agent_did);
CREATE INDEX IF NOT EXISTS idx_model_usage_session ON model_usage(session_id);
CREATE INDEX IF NOT EXISTS idx_model_usage_tenant ON model_usage(tenant_id);
CREATE INDEX IF NOT EXISTS idx_model_usage_model ON model_usage(model_provider, model_name);
CREATE INDEX IF NOT EXISTS idx_model_usage_created ON model_usage(created_at);

-- L05 Planning
CREATE TABLE IF NOT EXISTS goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id VARCHAR(255) UNIQUE NOT NULL,
    agent_id UUID REFERENCES agents(id),
    agent_did VARCHAR(255) NOT NULL,

    -- Goal content
    goal_text TEXT NOT NULL,
    goal_type VARCHAR(50) DEFAULT 'compound',
    status VARCHAR(50) DEFAULT 'pending',

    -- Constraints
    constraints_max_token_budget INTEGER,
    constraints_max_execution_time_sec INTEGER,
    constraints_max_parallelism INTEGER DEFAULT 10,
    constraints_deadline_unix_ms BIGINT,
    constraints_priority INTEGER DEFAULT 5,
    constraints_require_approval BOOLEAN DEFAULT false,
    constraints_allowed_agent_types TEXT[],
    constraints_forbidden_tools TEXT[],
    constraints_cost_limit_usd DECIMAL(10,2),

    -- Metadata
    metadata JSONB DEFAULT '{}',
    parent_goal_id VARCHAR(255),
    decomposition_strategy VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_goals_goal_id ON goals(goal_id);
CREATE INDEX IF NOT EXISTS idx_goals_agent ON goals(agent_id);
CREATE INDEX IF NOT EXISTS idx_goals_agent_did ON goals(agent_did);
CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status);
CREATE INDEX IF NOT EXISTS idx_goals_created ON goals(created_at);

CREATE TABLE IF NOT EXISTS plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id VARCHAR(255) UNIQUE NOT NULL,
    goal_id VARCHAR(255) NOT NULL,
    agent_id UUID REFERENCES agents(id),

    -- Plan content
    tasks JSONB DEFAULT '[]',
    dependency_graph JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'draft',

    -- Resource budget
    resource_budget JSONB,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    validated_at TIMESTAMP,
    execution_started_at TIMESTAMP,
    execution_completed_at TIMESTAMP,

    -- Metadata
    signature VARCHAR(255),
    decomposition_strategy VARCHAR(50) DEFAULT 'hybrid',
    decomposition_latency_ms DECIMAL(10,2),
    cache_hit BOOLEAN DEFAULT false,
    llm_provider VARCHAR(100),
    llm_model VARCHAR(255),
    total_tokens_used INTEGER DEFAULT 0,
    validation_time_ms DECIMAL(10,2),
    execution_time_ms DECIMAL(10,2),
    parallelism_achieved INTEGER DEFAULT 1,
    tags TEXT[],
    metadata JSONB DEFAULT '{}',

    -- Results
    error TEXT,
    completed_task_count INTEGER DEFAULT 0,
    failed_task_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_plans_plan_id ON plans(plan_id);
CREATE INDEX IF NOT EXISTS idx_plans_goal ON plans(goal_id);
CREATE INDEX IF NOT EXISTS idx_plans_agent ON plans(agent_id);
CREATE INDEX IF NOT EXISTS idx_plans_status ON plans(status);
CREATE INDEX IF NOT EXISTS idx_plans_created ON plans(created_at);

CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(255) UNIQUE NOT NULL,
    plan_id VARCHAR(255) NOT NULL,
    agent_id UUID REFERENCES agents(id),

    -- Task content
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    task_type VARCHAR(50) DEFAULT 'atomic',
    status VARCHAR(50) DEFAULT 'pending',

    -- Dependencies and I/O
    dependencies JSONB DEFAULT '[]',
    inputs JSONB DEFAULT '{}',
    outputs JSONB DEFAULT '{}',

    -- Execution
    assigned_agent VARCHAR(255),
    timeout_seconds INTEGER DEFAULT 300,
    retry_policy JSONB,
    retry_count INTEGER DEFAULT 0,

    -- Task specifics
    tool_name VARCHAR(255),
    llm_prompt TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    error TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_tasks_task_id ON tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_tasks_plan ON tasks(plan_id);
CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at);

-- L06 Evaluation
CREATE TABLE IF NOT EXISTS evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    task_id UUID REFERENCES tasks(id),
    evaluation_type VARCHAR(100) NOT NULL,
    score DECIMAL(5,4),
    metrics JSONB DEFAULT '{}',
    feedback TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- L06 Quality Scores
CREATE TABLE IF NOT EXISTS quality_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    score_id VARCHAR(255) UNIQUE NOT NULL,
    agent_id UUID REFERENCES agents(id),
    agent_did VARCHAR(255),
    tenant_id VARCHAR(255),
    timestamp TIMESTAMP NOT NULL,

    -- Overall score
    overall_score DECIMAL(5,4) NOT NULL,
    assessment VARCHAR(50) NOT NULL,
    data_completeness DECIMAL(5,4) DEFAULT 1.0,
    cached BOOLEAN DEFAULT false,

    -- Multi-dimensional scores stored as JSONB
    -- Format: {"accuracy": {"dimension": "accuracy", "score": 0.95, "weight": 0.3, "raw_metrics": {...}}, ...}
    dimensions JSONB DEFAULT '{}',

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_quality_scores_agent ON quality_scores(agent_id);
CREATE INDEX IF NOT EXISTS idx_quality_scores_tenant ON quality_scores(tenant_id);
CREATE INDEX IF NOT EXISTS idx_quality_scores_timestamp ON quality_scores(timestamp);
CREATE INDEX IF NOT EXISTS idx_quality_scores_assessment ON quality_scores(assessment);

-- L06 Metrics (Time-series)
CREATE TABLE IF NOT EXISTS metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(255) NOT NULL,
    metric_type VARCHAR(50) DEFAULT 'gauge',
    value DECIMAL(20,6) NOT NULL,
    timestamp TIMESTAMP NOT NULL,

    -- Prometheus-style labels as JSONB
    -- Format: {"agent_id": "agent-123", "task_type": "llm_call", "model": "gpt-4", ...}
    labels JSONB DEFAULT '{}',

    -- Optional agent/tenant tracking
    agent_id UUID REFERENCES agents(id),
    tenant_id VARCHAR(255),

    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_agent ON metrics(agent_id);
CREATE INDEX IF NOT EXISTS idx_metrics_tenant ON metrics(tenant_id);
CREATE INDEX IF NOT EXISTS idx_metrics_labels ON metrics USING GIN(labels);

-- L06 Anomalies
CREATE TABLE IF NOT EXISTS anomalies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anomaly_id VARCHAR(255) UNIQUE NOT NULL,
    metric_name VARCHAR(255) NOT NULL,
    severity VARCHAR(50) NOT NULL,

    -- Anomaly detection values
    baseline_value DECIMAL(20,6) NOT NULL,
    current_value DECIMAL(20,6) NOT NULL,
    z_score DECIMAL(10,4) NOT NULL,
    deviation_percent DECIMAL(10,4),
    confidence DECIMAL(5,4) DEFAULT 0.95,

    -- Status tracking
    status VARCHAR(50) DEFAULT 'alerting',
    detected_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,
    alert_sent BOOLEAN DEFAULT false,

    -- Optional agent/tenant tracking
    agent_id UUID REFERENCES agents(id),
    agent_did VARCHAR(255),
    tenant_id VARCHAR(255),

    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_anomalies_metric ON anomalies(metric_name);
CREATE INDEX IF NOT EXISTS idx_anomalies_severity ON anomalies(severity);
CREATE INDEX IF NOT EXISTS idx_anomalies_status ON anomalies(status);
CREATE INDEX IF NOT EXISTS idx_anomalies_detected ON anomalies(detected_at);
CREATE INDEX IF NOT EXISTS idx_anomalies_agent ON anomalies(agent_id);

-- L06 Compliance Results
CREATE TABLE IF NOT EXISTS compliance_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    result_id VARCHAR(255) UNIQUE NOT NULL,
    execution_id VARCHAR(255) NOT NULL,
    agent_id UUID REFERENCES agents(id),
    agent_did VARCHAR(255),
    tenant_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP NOT NULL,

    -- Compliance status
    compliant BOOLEAN DEFAULT true,

    -- Violations and constraints stored as JSONB arrays
    -- violations format: [{"violation_id": "...", "constraint": {...}, "actual": 100, ...}, ...]
    violations JSONB DEFAULT '[]',
    constraints_checked JSONB DEFAULT '[]',

    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_compliance_execution ON compliance_results(execution_id);
CREATE INDEX IF NOT EXISTS idx_compliance_agent ON compliance_results(agent_id);
CREATE INDEX IF NOT EXISTS idx_compliance_tenant ON compliance_results(tenant_id);
CREATE INDEX IF NOT EXISTS idx_compliance_compliant ON compliance_results(compliant);
CREATE INDEX IF NOT EXISTS idx_compliance_timestamp ON compliance_results(timestamp);

-- L06 Alerts
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id VARCHAR(255) UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    severity VARCHAR(50) NOT NULL,
    type VARCHAR(100) NOT NULL,
    metric VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,

    -- Delivery tracking
    channels TEXT[] DEFAULT '{}',
    delivery_attempts INTEGER DEFAULT 0,
    delivered BOOLEAN DEFAULT false,
    last_attempt TIMESTAMP,

    -- Optional agent/tenant tracking
    agent_id UUID REFERENCES agents(id),
    agent_did VARCHAR(255),
    tenant_id VARCHAR(255),

    -- Alert metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(type);
CREATE INDEX IF NOT EXISTS idx_alerts_delivered ON alerts(delivered);
CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_agent ON alerts(agent_id);

-- L07 Learning
CREATE TABLE IF NOT EXISTS feedback_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    task_id UUID REFERENCES tasks(id),
    feedback_type VARCHAR(100) NOT NULL,
    rating INTEGER,
    content TEXT,
    metadata JSONB DEFAULT '{}',
    processed BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS training_examples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id VARCHAR(255),
    task_id VARCHAR(255),
    agent_id UUID REFERENCES agents(id),
    source_type VARCHAR(100) DEFAULT 'execution_trace',
    source_trace_hash VARCHAR(255),
    input_text TEXT NOT NULL,
    input_structured JSONB DEFAULT '{}',
    output_text TEXT DEFAULT '',
    expected_actions JSONB DEFAULT '[]',
    final_answer TEXT DEFAULT '',
    quality_score DECIMAL(5,2) DEFAULT 0.0,
    confidence DECIMAL(5,4) DEFAULT 0.0,
    labels TEXT[] DEFAULT '{}',
    domain VARCHAR(100) DEFAULT 'general',
    task_type VARCHAR(100) DEFAULT 'single_step',
    difficulty DECIMAL(5,4) DEFAULT 0.5,
    metadata JSONB DEFAULT '{}',
    extracted_by VARCHAR(255) DEFAULT 'L07 TrainingDataExtractor',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_training_examples_agent ON training_examples(agent_id);
CREATE INDEX IF NOT EXISTS idx_training_examples_quality ON training_examples(quality_score);
CREATE INDEX IF NOT EXISTS idx_training_examples_domain ON training_examples(domain);

CREATE TABLE IF NOT EXISTS datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) DEFAULT '1.0.0',
    description TEXT DEFAULT '',
    tags TEXT[] DEFAULT '{}',
    split_ratios JSONB DEFAULT '{"train": 0.8, "validation": 0.1, "test": 0.1}',
    lineage JSONB DEFAULT '{"source_datasets": [], "extraction_jobs": [], "filter_configs": [], "transformations": []}',
    statistics JSONB DEFAULT '{}',
    created_by VARCHAR(255) DEFAULT 'L07 DatasetCurator',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_datasets_name ON datasets(name);

CREATE TABLE IF NOT EXISTS dataset_examples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID REFERENCES datasets(id) ON DELETE CASCADE,
    example_id UUID REFERENCES training_examples(id) ON DELETE CASCADE,
    split VARCHAR(50) DEFAULT 'train',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(dataset_id, example_id)
);
CREATE INDEX IF NOT EXISTS idx_dataset_examples_dataset ON dataset_examples(dataset_id);
CREATE INDEX IF NOT EXISTS idx_dataset_examples_split ON dataset_examples(dataset_id, split);

-- Configuration store
CREATE TABLE IF NOT EXISTS configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace VARCHAR(100) NOT NULL,
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(namespace, key)
);

-- Documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    content TEXT,
    content_type VARCHAR(100) DEFAULT 'text/plain',
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Sessions
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    session_type VARCHAR(100) DEFAULT 'conversation',
    status VARCHAR(50) DEFAULT 'active',
    context JSONB DEFAULT '{}',
    checkpoint JSONB,
    runtime_backend VARCHAR(50),
    runtime_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- L09 API Gateway
CREATE TABLE IF NOT EXISTS api_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(255) UNIQUE NOT NULL,
    trace_id VARCHAR(255),
    span_id VARCHAR(255),
    timestamp TIMESTAMP NOT NULL,
    method VARCHAR(10) NOT NULL,
    path VARCHAR(1000) NOT NULL,
    consumer_id VARCHAR(255),
    tenant_id VARCHAR(255),
    authenticated BOOLEAN DEFAULT false,
    auth_method VARCHAR(50),
    status_code INTEGER NOT NULL,
    latency_ms DECIMAL(10,2) NOT NULL,
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,
    rate_limit_tier VARCHAR(50),
    idempotency_key VARCHAR(255),
    idempotent_cache_hit BOOLEAN DEFAULT false,
    error_code VARCHAR(50),
    error_message TEXT,
    client_ip VARCHAR(45),
    user_agent TEXT,
    headers JSONB DEFAULT '{}',
    query_params JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_api_requests_timestamp ON api_requests(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_api_requests_consumer ON api_requests(consumer_id);
CREATE INDEX IF NOT EXISTS idx_api_requests_tenant ON api_requests(tenant_id);
CREATE INDEX IF NOT EXISTS idx_api_requests_status ON api_requests(status_code);
CREATE INDEX IF NOT EXISTS idx_api_requests_path ON api_requests(path);
CREATE INDEX IF NOT EXISTS idx_api_requests_trace ON api_requests(trace_id);

CREATE TABLE IF NOT EXISTS authentication_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(255) UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    consumer_id VARCHAR(255),
    tenant_id VARCHAR(255),
    auth_method VARCHAR(50) NOT NULL,
    success BOOLEAN NOT NULL,
    failure_reason VARCHAR(255),
    client_ip VARCHAR(45),
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_auth_events_timestamp ON authentication_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_auth_events_consumer ON authentication_events(consumer_id);
CREATE INDEX IF NOT EXISTS idx_auth_events_success ON authentication_events(success);

CREATE TABLE IF NOT EXISTS rate_limit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(255) UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    consumer_id VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(255),
    rate_limit_tier VARCHAR(50) NOT NULL,
    endpoint VARCHAR(1000),
    tokens_requested INTEGER DEFAULT 1,
    tokens_remaining INTEGER NOT NULL,
    tokens_limit INTEGER NOT NULL,
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    exceeded BOOLEAN DEFAULT false,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rate_limit_events_timestamp ON rate_limit_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_rate_limit_events_consumer ON rate_limit_events(consumer_id);
CREATE INDEX IF NOT EXISTS idx_rate_limit_events_exceeded ON rate_limit_events(exceeded);

-- L10 Human Interface
CREATE TABLE IF NOT EXISTS user_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interaction_id VARCHAR(255) UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    user_id VARCHAR(255),
    interaction_type VARCHAR(100) NOT NULL,
    target_type VARCHAR(100),
    target_id VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    parameters JSONB DEFAULT '{}',
    result VARCHAR(50),
    error_message TEXT,
    client_ip VARCHAR(45),
    user_agent TEXT,
    session_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_user_interactions_timestamp ON user_interactions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_user_interactions_user ON user_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_interactions_type ON user_interactions(interaction_type);

CREATE TABLE IF NOT EXISTS control_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operation_id VARCHAR(255) UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    operation_type VARCHAR(100) NOT NULL,
    target_agent_id UUID REFERENCES agents(id),
    target_agent_did VARCHAR(255),
    command VARCHAR(100) NOT NULL,
    parameters JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    result JSONB,
    error_message TEXT,
    executed_at TIMESTAMP,
    completed_at TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_control_operations_timestamp ON control_operations(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_control_operations_user ON control_operations(user_id);
CREATE INDEX IF NOT EXISTS idx_control_operations_status ON control_operations(status);
CREATE INDEX IF NOT EXISTS idx_control_operations_agent ON control_operations(target_agent_id);

-- L11 Integration Layer
CREATE TABLE IF NOT EXISTS saga_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    saga_id VARCHAR(255) UNIQUE NOT NULL,
    saga_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'running',
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    steps_total INTEGER NOT NULL,
    steps_completed INTEGER DEFAULT 0,
    steps_failed INTEGER DEFAULT 0,
    current_step VARCHAR(255),
    context JSONB DEFAULT '{}',
    compensation_mode BOOLEAN DEFAULT false,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_saga_executions_status ON saga_executions(status);
CREATE INDEX IF NOT EXISTS idx_saga_executions_started ON saga_executions(started_at DESC);

CREATE TABLE IF NOT EXISTS saga_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    step_id VARCHAR(255) UNIQUE NOT NULL,
    saga_id VARCHAR(255) NOT NULL,
    step_name VARCHAR(255) NOT NULL,
    step_index INTEGER NOT NULL,
    service_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    request JSONB DEFAULT '{}',
    response JSONB,
    error_message TEXT,
    compensation_executed BOOLEAN DEFAULT false,
    compensation_result JSONB,
    retry_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_saga_steps_saga ON saga_steps(saga_id);
CREATE INDEX IF NOT EXISTS idx_saga_steps_status ON saga_steps(status);

CREATE TABLE IF NOT EXISTS circuit_breaker_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(255) UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    service_id VARCHAR(255) NOT NULL,
    circuit_name VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    state_from VARCHAR(50),
    state_to VARCHAR(50) NOT NULL,
    failure_count INTEGER,
    success_count INTEGER,
    failure_threshold INTEGER,
    timeout_seconds INTEGER,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_circuit_breaker_events_timestamp ON circuit_breaker_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_circuit_breaker_events_service ON circuit_breaker_events(service_id);
CREATE INDEX IF NOT EXISTS idx_circuit_breaker_events_state ON circuit_breaker_events(state_to);

CREATE TABLE IF NOT EXISTS service_registry_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id VARCHAR(255) UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    service_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    layer VARCHAR(50),
    host VARCHAR(255),
    port INTEGER,
    health_status VARCHAR(50),
    capabilities TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_service_registry_events_timestamp ON service_registry_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_service_registry_events_service ON service_registry_events(service_id);
CREATE INDEX IF NOT EXISTS idx_service_registry_events_type ON service_registry_events(event_type);
"""


class Database:
    """PostgreSQL database manager with connection pooling."""

    def __init__(self, host: str = "localhost", port: int = 5432,
                 database: str = "agentic", user: str = "postgres",
                 password: str = "postgres"):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create connection pool."""
        if self.pool is None:
            try:
                self.pool = await asyncpg.create_pool(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                    min_size=5,
                    max_size=20,
                    command_timeout=60
                )
                logger.info(f"Connected to database {self.database}")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise

    async def disconnect(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection closed")

    async def initialize_schema(self):
        """Create all tables and indexes."""
        if not self.pool:
            raise RuntimeError("Database not connected")

        try:
            async with self.pool.acquire() as conn:
                # Migration: Drop old tables to apply new schemas
                await conn.execute("DROP TABLE IF EXISTS tool_executions CASCADE")
                logger.info("Dropped old tool_executions table for schema migration")

                await conn.execute("DROP TABLE IF EXISTS model_usage CASCADE")
                logger.info("Dropped old model_usage table for schema migration")

                await conn.execute("DROP TABLE IF EXISTS tasks CASCADE")
                logger.info("Dropped old tasks table for schema migration")

                await conn.execute("DROP TABLE IF EXISTS plans CASCADE")
                logger.info("Dropped old plans table for schema migration")

                await conn.execute("DROP TABLE IF EXISTS goals CASCADE")
                logger.info("Dropped old goals table for schema migration")

                # Execute main schema
                await conn.execute(DATABASE_SCHEMA)
            logger.info("Database schema initialized")
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise

    async def health_check(self) -> bool:
        """Check database connectivity."""
        if not self.pool:
            return False

        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def get_pool(self) -> asyncpg.Pool:
        """Get connection pool."""
        if not self.pool:
            raise RuntimeError("Database not connected")
        return self.pool


# Global database instance
import os

# Read from environment variables
_db_host = os.getenv("POSTGRES_HOST", "localhost")
_db_port = int(os.getenv("POSTGRES_PORT", "5432"))
_db_name = os.getenv("POSTGRES_DB", "agentic")
_db_user = os.getenv("POSTGRES_USER", "postgres")
_db_password = os.getenv("POSTGRES_PASSWORD", "postgres")

# Parse DATABASE_URL if provided (overrides individual vars)
_db_url = os.getenv("DATABASE_URL")
if _db_url:
    # Parse postgresql://user:pass@host:port/dbname
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', _db_url)
    if match:
        _db_user, _db_password, _db_host, _db_port, _db_name = match.groups()
        _db_port = int(_db_port)

db = Database(
    host=_db_host,
    port=_db_port,
    database=_db_name,
    user=_db_user,
    password=_db_password
)
