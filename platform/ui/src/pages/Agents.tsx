import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { useState } from 'react'
import { Play, Pause, Square, Plus, RefreshCw } from 'lucide-react'
import type { AgentConfig } from '../types'

export default function Agents() {
  const queryClient = useQueryClient()
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newAgent, setNewAgent] = useState<AgentConfig>({
    type: 'developer',
    capabilities: [],
    resource_limits: {
      cpu: '1.0',
      memory: '2Gi',
    },
  })

  const { data: agents, isLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: () => apiClient.listAgents(),
    refetchInterval: 5000,
  })

  const createMutation = useMutation({
    mutationFn: (config: AgentConfig) => apiClient.createAgent(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] })
      setShowCreateForm(false)
      setNewAgent({
        type: 'developer',
        capabilities: [],
        resource_limits: { cpu: '1.0', memory: '2Gi' },
      })
    },
  })

  const pauseMutation = useMutation({
    mutationFn: (agentId: string) => apiClient.pauseAgent(agentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agents'] }),
  })

  const resumeMutation = useMutation({
    mutationFn: (agentId: string) => apiClient.resumeAgent(agentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agents'] }),
  })

  const terminateMutation = useMutation({
    mutationFn: (agentId: string) => apiClient.terminateAgent(agentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agents'] }),
  })

  const handleCreateAgent = () => {
    createMutation.mutate(newAgent)
  }

  const addCapability = () => {
    const capability = prompt('Enter capability:')
    if (capability) {
      setNewAgent((prev) => ({
        ...prev,
        capabilities: [...prev.capabilities, capability],
      }))
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Agents</h1>
          <p className="text-gray-500 mt-1">Manage and monitor platform agents</p>
        </div>
        <button
          onClick={() => setShowCreateForm(true)}
          className="btn btn-primary flex items-center space-x-2"
        >
          <Plus className="w-4 h-4" />
          <span>Create Agent</span>
        </button>
      </div>

      {/* Create Agent Form */}
      {showCreateForm && (
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Create New Agent</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Agent Type
              </label>
              <select
                value={newAgent.type}
                onChange={(e) => setNewAgent({ ...newAgent, type: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="developer">Developer</option>
                <option value="researcher">Researcher</option>
                <option value="qa">QA Tester</option>
                <option value="general">General Purpose</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Capabilities
              </label>
              <div className="flex flex-wrap gap-2 mb-2">
                {newAgent.capabilities.map((cap, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-primary-100 text-primary-800"
                  >
                    {cap}
                    <button
                      onClick={() =>
                        setNewAgent({
                          ...newAgent,
                          capabilities: newAgent.capabilities.filter((_, i) => i !== idx),
                        })
                      }
                      className="ml-2 text-primary-600 hover:text-primary-800"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              <button onClick={addCapability} className="btn btn-secondary text-sm">
                + Add Capability
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  CPU Limit
                </label>
                <input
                  type="text"
                  value={newAgent.resource_limits?.cpu || ''}
                  onChange={(e) =>
                    setNewAgent({
                      ...newAgent,
                      resource_limits: {
                        cpu: e.target.value,
                        memory: newAgent.resource_limits?.memory || '2Gi',
                      },
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="1.0"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Memory Limit
                </label>
                <input
                  type="text"
                  value={newAgent.resource_limits?.memory || ''}
                  onChange={(e) =>
                    setNewAgent({
                      ...newAgent,
                      resource_limits: {
                        cpu: newAgent.resource_limits?.cpu || '1.0',
                        memory: e.target.value,
                      },
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="2Gi"
                />
              </div>
            </div>

            <div className="flex space-x-3">
              <button
                onClick={handleCreateAgent}
                disabled={createMutation.isPending}
                className="btn btn-primary"
              >
                {createMutation.isPending ? 'Creating...' : 'Create Agent'}
              </button>
              <button onClick={() => setShowCreateForm(false)} className="btn btn-secondary">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Agents List */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            All Agents ({agents?.length || 0})
          </h2>
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ['agents'] })}
            className="p-2 hover:bg-gray-100 rounded-md"
          >
            <RefreshCw className="w-4 h-4 text-gray-600" />
          </button>
        </div>

        {isLoading ? (
          <div className="text-center py-8 text-gray-500">Loading agents...</div>
        ) : agents && agents.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Agent ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Type
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Capabilities
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Created
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {agents.map((agent) => (
                  <tr key={agent.agent_id}>
                    <td className="px-4 py-3 text-sm font-mono text-gray-900">
                      {agent.agent_id.slice(0, 12)}...
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">{agent.type}</td>
                    <td className="px-4 py-3 text-sm">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                          agent.status === 'running'
                            ? 'bg-green-100 text-green-800'
                            : agent.status === 'paused'
                            ? 'bg-yellow-100 text-yellow-800'
                            : agent.status === 'terminated'
                            ? 'bg-gray-100 text-gray-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {agent.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {agent.capabilities?.slice(0, 2).join(', ') || 'None'}
                      {agent.capabilities && agent.capabilities.length > 2 && '...'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {new Date(agent.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center space-x-2">
                        {agent.status === 'running' && (
                          <button
                            onClick={() => pauseMutation.mutate(agent.agent_id)}
                            className="p-1 hover:bg-gray-100 rounded"
                            title="Pause"
                          >
                            <Pause className="w-4 h-4 text-yellow-600" />
                          </button>
                        )}
                        {agent.status === 'paused' && (
                          <button
                            onClick={() => resumeMutation.mutate(agent.agent_id)}
                            className="p-1 hover:bg-gray-100 rounded"
                            title="Resume"
                          >
                            <Play className="w-4 h-4 text-green-600" />
                          </button>
                        )}
                        {(agent.status === 'running' || agent.status === 'paused') && (
                          <button
                            onClick={() => terminateMutation.mutate(agent.agent_id)}
                            className="p-1 hover:bg-gray-100 rounded"
                            title="Terminate"
                          >
                            <Square className="w-4 h-4 text-red-600" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            No agents found. Create your first agent to get started.
          </div>
        )}
      </div>
    </div>
  )
}
