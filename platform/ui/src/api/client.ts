import axios, { AxiosInstance } from 'axios'
import type {
  Agent,
  AgentConfig,
  Service,
  ServiceSearchResult,
  ServiceInvokeRequest,
  ServiceInvokeResponse,
  Workflow,
  WorkflowExecution,
  Goal,
  Plan,
  SystemMetrics,
  PlatformEvent,
  ExecutionContext,
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8012'
const L01_URL = import.meta.env.VITE_L01_URL || 'http://localhost:8001'
const L02_URL = import.meta.env.VITE_L02_URL || 'http://localhost:8002'
const L10_URL = import.meta.env.VITE_L10_URL || 'http://localhost:8010'

// Development API key - CHANGE IN PRODUCTION
const DEV_API_KEY = 'dev_key_CHANGE_IN_PRODUCTION'

class PlatformAPIClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor for auth
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('auth_token') || DEV_API_KEY
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    })

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('auth_token')
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  // ========== Service Discovery (L12) ==========
  async listServices(layer?: string): Promise<Service[]> {
    const params = layer ? { layer } : {}
    const { data } = await this.client.get('/v1/services', { params })
    return data
  }

  async searchServices(query: string, threshold = 0.7): Promise<ServiceSearchResult[]> {
    const { data } = await this.client.get('/v1/services/search', {
      params: { q: query, threshold },
    })
    return data
  }

  async getService(serviceName: string): Promise<Service> {
    const { data } = await this.client.get(`/v1/services/${serviceName}`)
    return data
  }

  async invokeService(request: ServiceInvokeRequest): Promise<ServiceInvokeResponse> {
    const { data } = await this.client.post('/v1/services/invoke', request)
    return data
  }

  // ========== Agent Management (L01 + L02) ==========
  async listAgents(filters?: { status?: string; type?: string }): Promise<Agent[]> {
    const { data } = await axios.get(`${L01_URL}/agents`, {
      params: filters,
      headers: { 'Authorization': `Bearer ${DEV_API_KEY}` }
    })
    return data
  }

  async getAgent(agentId: string): Promise<Agent> {
    const { data } = await axios.get(`${L01_URL}/agents/${agentId}`, {
      headers: { 'Authorization': `Bearer ${DEV_API_KEY}` }
    })
    return data
  }

  async createAgent(config: AgentConfig): Promise<Agent> {
    const { data } = await axios.post(`${L02_URL}/runtime/spawn`, config, {
      headers: { 'Authorization': `Bearer ${DEV_API_KEY}` }
    })
    return data
  }

  async pauseAgent(agentId: string): Promise<void> {
    await axios.post(`${L10_URL}/control/pause`, { agent_id: agentId }, {
      headers: { 'Authorization': `Bearer ${DEV_API_KEY}` }
    })
  }

  async resumeAgent(agentId: string): Promise<void> {
    await axios.post(`${L10_URL}/control/resume`, { agent_id: agentId }, {
      headers: { 'Authorization': `Bearer ${DEV_API_KEY}` }
    })
  }

  async terminateAgent(agentId: string): Promise<void> {
    await axios.post(`${L10_URL}/control/stop`, { agent_id: agentId }, {
      headers: { 'Authorization': `Bearer ${DEV_API_KEY}` }
    })
  }

  // ========== Workflows (L12) ==========
  async listWorkflows(): Promise<Workflow[]> {
    const { data } = await this.client.get('/v1/workflows')
    return data
  }

  async getWorkflow(workflowId: string): Promise<Workflow> {
    const { data } = await this.client.get(`/v1/workflows/${workflowId}`)
    return data
  }

  async createWorkflow(workflow: Omit<Workflow, 'workflow_id' | 'created_at'>): Promise<Workflow> {
    const { data } = await this.client.post('/v1/workflows', workflow)
    return data
  }

  async executeWorkflow(workflowId: string, params: any): Promise<WorkflowExecution> {
    const { data } = await this.client.post(`/v1/workflows/${workflowId}/execute`, params)
    return data
  }

  async getWorkflowExecution(executionId: string): Promise<WorkflowExecution> {
    const { data } = await this.client.get(`/v1/workflows/executions/${executionId}`)
    return data
  }

  async listWorkflowExecutions(): Promise<WorkflowExecution[]> {
    const { data } = await this.client.get('/v1/workflows/executions')
    return data
  }

  // ========== Goals & Plans (L01 + L05) ==========
  async listGoals(filters?: { status?: string }): Promise<Goal[]> {
    const { data } = await axios.get(`${L01_URL}/goals`, { params: filters })
    return data
  }

  async createGoal(goal: Partial<Goal>): Promise<Goal> {
    const { data } = await axios.post(`${L01_URL}/goals`, goal)
    return data
  }

  async getGoal(goalId: string): Promise<Goal> {
    const { data } = await axios.get(`${L01_URL}/goals/${goalId}`)
    return data
  }

  async listPlans(goalId?: string): Promise<Plan[]> {
    const params = goalId ? { goal_id: goalId } : {}
    const { data } = await axios.get(`${L01_URL}/plans`, { params })
    return data
  }

  async createPlan(goalId: string, strategy: string, tasks: any[]): Promise<Plan> {
    const { data } = await axios.post('http://localhost:8005/plans', {
      goal_id: goalId,
      strategy,
      tasks,
    })
    return data
  }

  async getPlan(planId: string): Promise<Plan> {
    const { data } = await axios.get(`${L01_URL}/plans/${planId}`)
    return data
  }

  // ========== Events (L01) ==========
  async listEvents(limit: number = 100, offset: number = 0): Promise<PlatformEvent[]> {
    const { data } = await axios.get(`${L01_URL}/events`, {
      params: { limit, offset },
    })
    return data
  }

  // ========== Context Management (L01) ==========
  async listContexts(): Promise<ExecutionContext[]> {
    const { data } = await axios.get(`${L01_URL}/contexts`)
    return data
  }

  async createContext(name: string, variables: any): Promise<ExecutionContext> {
    const { data } = await axios.post(`${L01_URL}/contexts`, { name, variables })
    return data
  }

  async getContext(contextId: string): Promise<ExecutionContext> {
    const { data } = await axios.get(`${L01_URL}/contexts/${contextId}`)
    return data
  }

  async updateContext(contextId: string, variables: any): Promise<ExecutionContext> {
    const { data } = await axios.patch(`${L01_URL}/contexts/${contextId}`, { variables })
    return data
  }

  async deleteContext(contextId: string): Promise<void> {
    await axios.delete(`${L01_URL}/contexts/${contextId}`)
  }

  // ========== System Metrics (L10) ==========
  async getSystemMetrics(): Promise<SystemMetrics> {
    const { data } = await axios.get(`${L10_URL}/dashboard/metrics`)
    return data
  }

  async getSystemOverview(): Promise<any> {
    const { data } = await axios.get(`${L10_URL}/dashboard/overview`)
    return data
  }

  // ========== Health Checks ==========
  async checkHealth(): Promise<{ status: string; services_loaded: number }> {
    const { data } = await this.client.get('/health')
    return data
  }
}

export const apiClient = new PlatformAPIClient()
export default apiClient
