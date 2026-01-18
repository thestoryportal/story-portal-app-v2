import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { useState } from 'react'
import { Play, Plus, Clock, CheckCircle2, XCircle, Loader } from 'lucide-react'
import type { WorkflowDefinition } from '../types'

export default function Workflows() {
  const queryClient = useQueryClient()
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null)
  const [executeParams, setExecuteParams] = useState('')

  const [newWorkflow, setNewWorkflow] = useState<WorkflowDefinition>({
    workflow_id: '',
    name: '',
    description: '',
    steps: [],
    created_at: '',
    status: 'draft',
    metadata: {},
  })

  const { data: workflows, isLoading: workflowsLoading } = useQuery({
    queryKey: ['workflows'],
    queryFn: () => apiClient.listWorkflows(),
  })

  const { data: executions, isLoading: executionsLoading } = useQuery({
    queryKey: ['workflow-executions'],
    queryFn: () => apiClient.listWorkflowExecutions(),
    refetchInterval: 3000,
  })

  const createMutation = useMutation({
    mutationFn: (workflow: WorkflowDefinition) => apiClient.createWorkflow(workflow),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
      setShowCreateForm(false)
      setNewWorkflow({
        workflow_id: '',
        name: '',
        description: '',
        steps: [],
        created_at: '',
        status: 'draft',
        metadata: {},
      })
    },
  })

  const executeMutation = useMutation({
    mutationFn: ({ workflowId, params }: { workflowId: string; params: any }) =>
      apiClient.executeWorkflow(workflowId, params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow-executions'] })
      setSelectedWorkflow(null)
      setExecuteParams('')
    },
  })

  const handleCreateWorkflow = () => {
    createMutation.mutate(newWorkflow)
  }

  const handleExecuteWorkflow = () => {
    if (!selectedWorkflow) return

    try {
      const params = executeParams ? JSON.parse(executeParams) : {}
      executeMutation.mutate({ workflowId: selectedWorkflow, params })
    } catch (error) {
      alert('Invalid JSON parameters')
    }
  }

  const addStep = () => {
    const serviceName = prompt('Enter service name:')
    const methodName = prompt('Enter method name:')
    if (serviceName && methodName) {
      setNewWorkflow((prev: WorkflowDefinition) => ({
        ...prev,
        steps: [
          ...prev.steps,
          {
            step_id: `step_${prev.steps.length + 1}`,
            service_name: serviceName,
            method_name: methodName,
            parameters: {},
            depends_on: [],
          },
        ],
      }))
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-600" />
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-600" />
      case 'running':
        return <Loader className="w-5 h-5 text-blue-600 animate-spin" />
      default:
        return <Clock className="w-5 h-5 text-gray-400" />
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Workflows</h1>
          <p className="text-gray-500 mt-1">
            Create and execute multi-step workflows ({workflows?.length || 0} defined)
          </p>
        </div>
        <button
          onClick={() => setShowCreateForm(true)}
          className="btn btn-primary flex items-center space-x-2"
        >
          <Plus className="w-4 h-4" />
          <span>Create Workflow</span>
        </button>
      </div>

      {/* Create Workflow Form */}
      {showCreateForm && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Create New Workflow</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Workflow ID
              </label>
              <input
                type="text"
                value={newWorkflow.workflow_id}
                onChange={(e) =>
                  setNewWorkflow({ ...newWorkflow, workflow_id: e.target.value })
                }
                placeholder="e.g., testing.unit"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Workflow Name
              </label>
              <input
                type="text"
                value={newWorkflow.name}
                onChange={(e) => setNewWorkflow({ ...newWorkflow, name: e.target.value })}
                placeholder="e.g., Run Unit Tests"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={newWorkflow.description}
                onChange={(e) =>
                  setNewWorkflow({ ...newWorkflow, description: e.target.value })
                }
                placeholder="Describe what this workflow does"
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Workflow Steps
              </label>
              <div className="space-y-2 mb-2">
                {newWorkflow.steps.map((step: any, idx: number) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-md"
                  >
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {step.step_id}: {step.service_name}.{step.method_name}
                      </p>
                    </div>
                    <button
                      onClick={() =>
                        setNewWorkflow({
                          ...newWorkflow,
                          steps: newWorkflow.steps.filter((_: any, i: number) => i !== idx),
                        })
                      }
                      className="text-red-600 hover:text-red-800 text-sm"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
              <button onClick={addStep} className="btn btn-secondary text-sm">
                + Add Step
              </button>
            </div>

            <div className="flex space-x-3">
              <button
                onClick={handleCreateWorkflow}
                disabled={createMutation.isPending}
                className="btn btn-primary"
              >
                {createMutation.isPending ? 'Creating...' : 'Create Workflow'}
              </button>
              <button onClick={() => setShowCreateForm(false)} className="btn btn-secondary">
                Cancel
              </button>
            </div>

            {createMutation.isError && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-800">
                  {(createMutation.error as Error).message}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Execute Workflow Panel */}
      {selectedWorkflow && (
        <div className="card bg-blue-50 border border-blue-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Execute: {selectedWorkflow}
          </h3>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Parameters (JSON)
              </label>
              <textarea
                value={executeParams}
                onChange={(e) => setExecuteParams(e.target.value)}
                placeholder='{"key": "value"}'
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
              />
            </div>
            <div className="flex space-x-3">
              <button
                onClick={handleExecuteWorkflow}
                disabled={executeMutation.isPending}
                className="btn btn-primary flex items-center space-x-2"
              >
                <Play className="w-4 h-4" />
                <span>{executeMutation.isPending ? 'Executing...' : 'Execute'}</span>
              </button>
              <button onClick={() => setSelectedWorkflow(null)} className="btn btn-secondary">
                Cancel
              </button>
            </div>
            {executeMutation.isError && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-800">
                  {(executeMutation.error as Error).message}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Workflow List */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Available Workflows ({workflows?.length || 0})
        </h2>
        {workflowsLoading ? (
          <div className="text-center py-8 text-gray-500">Loading workflows...</div>
        ) : workflows && workflows.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {workflows.map((workflow) => (
              <div
                key={workflow.workflow_id}
                className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 hover:shadow-md transition-all cursor-pointer"
                onClick={() => setSelectedWorkflow(workflow.workflow_id)}
              >
                <h3 className="text-sm font-semibold text-gray-900">
                  {workflow.name || workflow.workflow_id}
                </h3>
                <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                  {workflow.description}
                </p>
                <div className="mt-3 flex items-center justify-between">
                  <span className="text-xs text-gray-600">
                    {workflow.steps?.length || 0} steps
                  </span>
                  <button className="text-primary-600 hover:text-primary-800 text-xs font-medium">
                    Execute →
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            No workflows found. Create your first workflow to get started.
          </div>
        )}
      </div>

      {/* Execution History */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Execution History</h2>
        {executionsLoading ? (
          <div className="text-center py-8 text-gray-500">Loading executions...</div>
        ) : executions && executions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Execution ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Workflow
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Started
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Duration
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {executions.slice(0, 10).map((execution: any) => (
                  <tr key={execution.execution_id}>
                    <td className="px-4 py-3 text-sm font-mono text-gray-900">
                      {execution.execution_id.slice(0, 12)}...
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {execution.workflow_id}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(execution.status)}
                        <span
                          className={`text-xs font-medium capitalize ${
                            execution.status === 'completed'
                              ? 'text-green-800'
                              : execution.status === 'failed'
                              ? 'text-red-800'
                              : execution.status === 'running'
                              ? 'text-blue-800'
                              : 'text-gray-800'
                          }`}
                        >
                          {execution.status}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {new Date(execution.started_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {execution.completed_at
                        ? `${(
                            (new Date(execution.completed_at).getTime() -
                              new Date(execution.started_at).getTime()) /
                            1000
                          ).toFixed(1)}s`
                        : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            No workflow executions yet. Execute a workflow to see history.
          </div>
        )}
      </div>
    </div>
  )
}
