// Agent Types
export interface Agent {
  agent_id: string
  type: string
  status: 'idle' | 'running' | 'paused' | 'terminated' | 'failed'
  capabilities: string[]
  created_at: string
  updated_at: string
  resource_usage?: {
    cpu: number
    memory: number
  }
  metadata?: Record<string, any>
}

export interface AgentConfig {
  type: string
  capabilities: string[]
  resource_limits?: {
    cpu: string
    memory: string
  }
  metadata?: Record<string, any>
}

// Service Types
export interface Service {
  service_name: string
  layer: string
  description: string
  keywords: string[]
  module_path: string
  class_name: string
  methods?: ServiceMethod[]
}

export interface ServiceMethod {
  name: string
  description?: string
  parameters?: Record<string, any>
}

export interface ServiceSearchResult extends Service {
  score: number
  match_reason: string
}

export interface ServiceInvokeRequest {
  service_name: string
  method_name: string
  parameters: Record<string, any>
  session_id?: string
}

export interface ServiceInvokeResponse {
  result: any
  execution_time_ms: number
  session_id: string
}

// Workflow Types
export interface Workflow {
  workflow_id: string
  name: string
  description: string
  steps: WorkflowStep[]
  created_at: string
  status: 'draft' | 'active' | 'archived'
  metadata?: Record<string, any>
}

// Alias for WorkflowDefinition
export type WorkflowDefinition = Workflow

export interface WorkflowStep {
  step_id: string
  service_name: string
  method_name: string
  parameters: Record<string, any>
  depends_on?: string[]
}

export interface WorkflowExecution {
  execution_id: string
  workflow_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at: string
  completed_at?: string
  results?: any
}

// Goal & Plan Types
export interface Goal {
  goal_id: string
  description: string
  priority: 'low' | 'medium' | 'high'
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  created_at: string
  constraints?: Record<string, any>
  context?: Record<string, any>
}

export interface Plan {
  plan_id: string
  goal_id: string
  strategy: string
  tasks: Task[]
  status: 'draft' | 'executing' | 'completed' | 'failed'
  created_at: string
  completed_at?: string
}

export interface Task {
  task_id: string
  description: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  assigned_agent?: string
  dependencies?: string[]
}

// System Health Types
export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy'
  services: ServiceHealth[]
  timestamp: string
}

export interface ServiceHealth {
  name: string
  status: 'healthy' | 'unhealthy'
  url: string
  response_time_ms?: number
}

// Metrics Types
export interface SystemMetrics {
  agents: {
    total: number
    active: number
    idle: number
    failed: number
  }
  resources: {
    cpu_usage: number
    memory_usage: number
    total_memory: number
  }
  requests: {
    total: number
    success_rate: number
    avg_response_time_ms: number
  }
}

// Event Types
export interface PlatformEvent {
  event_id: string
  event_type: string
  payload: Record<string, any>
  timestamp: string
  source: string
  severity?: 'low' | 'medium' | 'high' | 'critical'
}

// Context Types
export interface ExecutionContext {
  context_id: string
  name: string
  variables: Record<string, any>
  created_at: string
  updated_at: string
}

// API Response Types
export interface ApiResponse<T> {
  data: T
  message?: string
  timestamp: string
}

export interface ApiError {
  error: string
  code: string
  details?: Record<string, any>
}
