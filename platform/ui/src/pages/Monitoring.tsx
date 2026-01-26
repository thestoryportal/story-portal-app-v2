import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { useState, useEffect } from 'react'
import {
  Activity,
  AlertTriangle,
  TrendingUp,
  DollarSign,
  Clock,
  Server,
  Database,
  Zap,
} from 'lucide-react'
import { wsManager } from '../api/websocket'
import type { PlatformEvent } from '../types'

export default function Monitoring() {
  const [recentAlerts, setRecentAlerts] = useState<PlatformEvent[]>([])
  const [timeRange, setTimeRange] = useState<'1h' | '24h' | '7d' | '30d'>('24h')

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

  const { data: events } = useQuery({
    queryKey: ['events', timeRange],
    queryFn: () => apiClient.listEvents(100, 0),
    refetchInterval: 5000,
  })

  const { data: services, isLoading: servicesLoading } = useQuery({
    queryKey: ['services-health'],
    queryFn: () => apiClient.getServicesHealth(),
    refetchInterval: 10000,
  })

  useEffect(() => {
    const unsubscribe = wsManager.subscribeToAll((event) => {
      if (
        event.event_type.includes('error') ||
        event.event_type.includes('failed') ||
        event.severity === 'high'
      ) {
        setRecentAlerts((prev) => [event, ...prev].slice(0, 20))
      }
    })

    return () => unsubscribe()
  }, [])

  const systemStats = [
    {
      name: 'CPU Usage',
      value: `${metrics?.resources?.cpu_usage?.toFixed(1) || 0}%`,
      icon: Server,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      trend: '+2.5%',
    },
    {
      name: 'Memory Usage',
      value: `${metrics?.resources?.memory_usage?.toFixed(1) || 0}%`,
      icon: Database,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      trend: '+1.2%',
    },
    {
      name: 'Avg Response Time',
      value: `${metrics?.requests?.avg_response_time_ms?.toFixed(0) || 0}ms`,
      icon: Clock,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      trend: '-5.3%',
    },
    {
      name: 'Error Rate',
      value: `${
        metrics?.requests?.total
          ? (
              ((metrics.requests.total - (metrics.requests.success_rate || 0) * metrics.requests.total) /
                metrics.requests.total) *
              100
            ).toFixed(2)
          : 0
      }%`,
      icon: AlertTriangle,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
      trend: '-0.8%',
    },
  ]

  const performanceMetrics = [
    {
      name: 'Total Requests',
      value: metrics?.requests?.total?.toLocaleString() || '0',
      change: '+12.5%',
      icon: TrendingUp,
    },
    {
      name: 'Success Rate',
      value: `${((metrics?.requests?.success_rate || 0) * 100).toFixed(1)}%`,
      change: '+0.5%',
      icon: Activity,
    },
    {
      name: 'Total Cost (Est.)',
      value: `$${((metrics?.requests?.total || 0) * 0.001).toFixed(2)}`,
      change: '+8.2%',
      icon: DollarSign,
    },
    {
      name: 'Token Usage',
      value: `${((metrics?.requests?.total || 0) * 1500).toLocaleString()}`,
      change: '+15.3%',
      icon: Zap,
    },
  ]

  const getEventSeverityColor = (severity?: string) => {
    switch (severity) {
      case 'high':
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'low':
        return 'bg-green-100 text-green-800 border-green-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">System Monitoring</h1>
          <p className="text-gray-500 mt-1">Real-time metrics and performance analytics</p>
        </div>
        <div className="flex items-center space-x-2">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as typeof timeRange)}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm"
          >
            <option value="1h">Last Hour</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
        </div>
      </div>

      {/* System Health Status */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div
              className={`w-3 h-3 rounded-full ${
                health?.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
              } animate-pulse`}
            />
            <div>
              <h2 className="text-lg font-semibold text-gray-900">System Status</h2>
              <p className="text-sm text-gray-500">
                {health?.status === 'healthy' ? 'All systems operational' : 'Issues detected'}
              </p>
            </div>
          </div>
          <span
            className={`px-4 py-2 rounded-full text-sm font-medium ${
              health?.status === 'healthy'
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            {health?.status || 'Unknown'}
          </span>
        </div>
      </div>

      {/* System Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {systemStats.map((stat) => (
          <div key={stat.name} className="card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">{stat.name}</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</p>
                <p className="text-xs text-gray-500 mt-1">{stat.trend} from last period</p>
              </div>
              <div className={`${stat.bgColor} p-3 rounded-lg`}>
                <stat.icon className={`w-6 h-6 ${stat.color}`} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Performance Metrics */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Performance Metrics</h2>
        {metricsLoading ? (
          <div className="text-center py-8 text-gray-500">Loading metrics...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {performanceMetrics.map((metric) => (
              <div key={metric.name} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <metric.icon className="w-4 h-4 text-gray-500" />
                  <span className="text-sm text-gray-600">{metric.name}</span>
                </div>
                <p className="text-2xl font-bold text-gray-900">{metric.value}</p>
                <p
                  className={`text-xs mt-1 ${
                    metric.change.startsWith('+') ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {metric.change} from previous period
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Alerts */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Recent Alerts ({recentAlerts.length})
          </h2>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {recentAlerts.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-8">No recent alerts</p>
            ) : (
              recentAlerts.map((alert) => (
                <div
                  key={alert.event_id}
                  className={`p-3 border rounded-md ${getEventSeverityColor(
                    alert.severity
                  )}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{alert.event_type}</p>
                      <p className="text-xs mt-1 truncate">
                        {JSON.stringify(alert.payload).slice(0, 100)}
                      </p>
                    </div>
                    <AlertTriangle className="w-4 h-4 ml-2 flex-shrink-0" />
                  </div>
                  <div className="flex items-center space-x-2 mt-2">
                    <Clock className="w-3 h-3 text-gray-400" />
                    <span className="text-xs text-gray-600">
                      {new Date(alert.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Service Health */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Service Health</h2>
          <div className="space-y-3">
            {servicesLoading ? (
              <div className="text-center py-8 text-gray-500">
                <Activity className="w-6 h-6 animate-spin mx-auto mb-2" />
                <p>Loading services...</p>
              </div>
            ) : services && services.length > 0 ? (
              services.map((service: any) => (
              <div
                key={service.name}
                className="flex items-center justify-between p-3 border border-gray-200 rounded-md"
              >
                <div className="flex items-center space-x-3">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      service.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                    }`}
                  />
                  <span className="text-sm font-medium text-gray-900">{service.name}</span>
                </div>
                <div className="flex items-center space-x-4">
                  <span className="text-xs text-gray-500">{service.latency}ms</span>
                  <span
                    className={`px-2 py-1 text-xs font-medium rounded-full ${
                      service.status === 'healthy'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}
                  >
                    {service.status}
                  </span>
                </div>
              </div>
            ))
            ) : (
              <div className="text-center py-8 text-gray-500">
                <Server className="w-6 h-6 mx-auto mb-2" />
                <p>No service data available</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Event Log */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Event Log</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead>
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Timestamp
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Event Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Source
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Severity
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Payload
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {events && events.length > 0 ? (
                events.slice(0, 20).map((event) => (
                  <tr key={event.event_id}>
                    <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {event.event_type}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {event.source || 'system'}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                          event.severity === 'high' || event.severity === 'critical'
                            ? 'bg-red-100 text-red-800'
                            : event.severity === 'medium'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {event.severity || 'info'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 max-w-md truncate">
                      {JSON.stringify(event.payload)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-500">
                    No events found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Cost Analytics */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Cost Analytics</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="border border-gray-200 rounded-lg p-4">
            <p className="text-sm text-gray-600">Estimated Daily Cost</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              $
              {(
                ((metrics?.requests?.total || 0) * 0.001) /
                (timeRange === '24h' ? 1 : timeRange === '7d' ? 7 : 30)
              ).toFixed(2)}
            </p>
            <p className="text-xs text-gray-500 mt-1">Based on current usage</p>
          </div>
          <div className="border border-gray-200 rounded-lg p-4">
            <p className="text-sm text-gray-600">Estimated Monthly Cost</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              $
              {(
                ((metrics?.requests?.total || 0) * 0.001 * 30) /
                (timeRange === '24h' ? 1 : timeRange === '7d' ? 7 : 30)
              ).toFixed(2)}
            </p>
            <p className="text-xs text-gray-500 mt-1">Projected from current rate</p>
          </div>
          <div className="border border-gray-200 rounded-lg p-4">
            <p className="text-sm text-gray-600">Cost per Request</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">$0.001</p>
            <p className="text-xs text-gray-500 mt-1">Average cost</p>
          </div>
        </div>
      </div>
    </div>
  )
}
