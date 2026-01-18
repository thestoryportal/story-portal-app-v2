import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { Activity, Users, Package, TrendingUp, Clock, CheckCircle2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { wsManager } from '../api/websocket'
import type { PlatformEvent } from '../types'

export default function Dashboard() {
  const [recentEvents, setRecentEvents] = useState<PlatformEvent[]>([])

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['system-metrics'],
    queryFn: () => apiClient.getSystemMetrics(),
    refetchInterval: 5000,
  })

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiClient.checkHealth(),
    refetchInterval: 10000,
  })

  const { data: agents } = useQuery({
    queryKey: ['agents'],
    queryFn: () => apiClient.listAgents(),
    refetchInterval: 5000,
  })

  const { data: services } = useQuery({
    queryKey: ['services'],
    queryFn: () => apiClient.listServices(),
  })

  useEffect(() => {
    const unsubscribe = wsManager.subscribeToAll((event) => {
      setRecentEvents((prev) => [event, ...prev].slice(0, 10))
    })

    return () => unsubscribe()
  }, [])

  const stats = [
    {
      name: 'Active Agents',
      value: agents?.filter((a) => a.status === 'running').length || 0,
      total: agents?.length || 0,
      icon: Users,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      name: 'Services Available',
      value: services?.length || 0,
      icon: Package,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      name: 'System Health',
      value: health?.status || 'Unknown',
      icon: Activity,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
    {
      name: 'Success Rate',
      value: metrics?.requests?.success_rate
        ? `${(metrics.requests.success_rate * 100).toFixed(1)}%`
        : 'N/A',
      icon: TrendingUp,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">System overview and real-time metrics</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <div key={stat.name} className="card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">{stat.name}</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {typeof stat.value === 'number' && 'total' in stat
                    ? `${stat.value} / ${stat.total}`
                    : stat.value}
                </p>
              </div>
              <div className={`${stat.bgColor} p-3 rounded-lg`}>
                <stat.icon className={`w-6 h-6 ${stat.color}`} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Resource Usage */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Resource Usage</h2>
          {metricsLoading ? (
            <div className="text-gray-500">Loading metrics...</div>
          ) : (
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">CPU Usage</span>
                  <span className="text-sm font-medium text-gray-900">
                    {metrics?.resources?.cpu_usage?.toFixed(1) || 0}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all"
                    style={{ width: `${metrics?.resources?.cpu_usage || 0}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">Memory Usage</span>
                  <span className="text-sm font-medium text-gray-900">
                    {metrics?.resources?.memory_usage?.toFixed(1) || 0}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-600 h-2 rounded-full transition-all"
                    style={{ width: `${metrics?.resources?.memory_usage || 0}%` }}
                  />
                </div>
              </div>

              {metrics?.requests && (
                <div className="pt-4 border-t border-gray-200">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Avg Response Time</span>
                    <span className="text-sm font-medium text-gray-900">
                      {metrics.requests.avg_response_time_ms?.toFixed(0) || 0}ms
                    </span>
                  </div>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-sm text-gray-600">Total Requests</span>
                    <span className="text-sm font-medium text-gray-900">
                      {metrics.requests.total?.toLocaleString() || 0}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Recent Events */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Events</h2>
          <div className="space-y-3 max-h-80 overflow-y-auto">
            {recentEvents.length === 0 ? (
              <p className="text-sm text-gray-500">No recent events</p>
            ) : (
              recentEvents.map((event) => (
                <div
                  key={event.event_id}
                  className="flex items-start space-x-3 pb-3 border-b border-gray-100 last:border-0"
                >
                  <CheckCircle2 className="w-5 h-5 text-green-500 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{event.event_type}</p>
                    <p className="text-sm text-gray-500 truncate">
                      {JSON.stringify(event.payload).slice(0, 100)}
                    </p>
                    <div className="flex items-center space-x-2 mt-1">
                      <Clock className="w-3 h-3 text-gray-400" />
                      <span className="text-xs text-gray-400">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Active Agents List */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Active Agents</h2>
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
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {agents && agents.length > 0 ? (
                agents.slice(0, 5).map((agent) => (
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
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {agent.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {agent.capabilities?.join(', ') || 'N/A'}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-sm text-gray-500">
                    No active agents
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
