import { useQuery, useMutation } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { useState } from 'react'
import { Search, Play, Package } from 'lucide-react'
import type { ServiceInvokeRequest } from '../types'

export default function Services() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedService, setSelectedService] = useState<string | null>(null)
  const [invokeParams, setInvokeParams] = useState('')
  const [invokeMethod, setInvokeMethod] = useState('')

  const { data: services, isLoading } = useQuery({
    queryKey: ['services'],
    queryFn: () => apiClient.listServices(),
  })

  const { data: searchResults } = useQuery({
    queryKey: ['service-search', searchQuery],
    queryFn: () => apiClient.searchServices(searchQuery, 0.6),
    enabled: searchQuery.length > 0,
  })

  const invokeMutation = useMutation({
    mutationFn: (request: ServiceInvokeRequest) => apiClient.invokeService(request),
  })

  const handleInvoke = () => {
    if (!selectedService || !invokeMethod) return

    try {
      const params = invokeParams ? JSON.parse(invokeParams) : {}
      invokeMutation.mutate({
        service_name: selectedService,
        method_name: invokeMethod,
        parameters: params,
      })
    } catch (error) {
      alert('Invalid JSON parameters')
    }
  }

  const displayedServices = searchQuery ? searchResults : services
  const groupedServices = displayedServices?.reduce((acc, service) => {
    const layer = service.layer
    if (!acc[layer]) acc[layer] = []
    acc[layer].push(service)
    return acc
  }, {} as Record<string, typeof services>)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Services</h1>
        <p className="text-gray-500 mt-1">
          Explore and invoke platform services ({services?.length || 0} available)
        </p>
      </div>

      {/* Search */}
      <div className="card">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search services (e.g., 'agent', 'plan', 'workflow')"
            className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
      </div>

      {/* Service Invocation Panel */}
      {selectedService && (
        <div className="card bg-blue-50 border border-blue-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Invoke: {selectedService}
          </h3>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Method Name
              </label>
              <input
                type="text"
                value={invokeMethod}
                onChange={(e) => setInvokeMethod(e.target.value)}
                placeholder="e.g., list_agents, create_plan"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Parameters (JSON)
              </label>
              <textarea
                value={invokeParams}
                onChange={(e) => setInvokeParams(e.target.value)}
                placeholder='{"key": "value"}'
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
              />
            </div>
            <div className="flex space-x-3">
              <button
                onClick={handleInvoke}
                disabled={invokeMutation.isPending}
                className="btn btn-primary flex items-center space-x-2"
              >
                <Play className="w-4 h-4" />
                <span>{invokeMutation.isPending ? 'Invoking...' : 'Invoke'}</span>
              </button>
              <button
                onClick={() => setSelectedService(null)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
            </div>
            {invokeMutation.isSuccess && (
              <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-md">
                <h4 className="font-medium text-green-900 mb-2">Result:</h4>
                <pre className="text-sm text-green-800 overflow-x-auto">
                  {JSON.stringify(invokeMutation.data, null, 2)}
                </pre>
              </div>
            )}
            {invokeMutation.isError && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
                <h4 className="font-medium text-red-900">Error:</h4>
                <p className="text-sm text-red-800 mt-1">
                  {(invokeMutation.error as Error).message}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Services List */}
      {isLoading ? (
        <div className="card text-center py-8 text-gray-500">Loading services...</div>
      ) : (
        <div className="space-y-6">
          {groupedServices &&
            Object.entries(groupedServices)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([layer, layerServices]) => (
                <div key={layer} className="card">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">
                    {layer} ({layerServices?.length || 0} services)
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {layerServices?.map((service) => (
                      <div
                        key={service.service_name}
                        className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 hover:shadow-md transition-all cursor-pointer"
                        onClick={() => setSelectedService(service.service_name)}
                      >
                        <div className="flex items-start space-x-3">
                          <Package className="w-5 h-5 text-primary-600 mt-1" />
                          <div className="flex-1 min-w-0">
                            <h3 className="text-sm font-semibold text-gray-900">
                              {service.service_name}
                            </h3>
                            <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                              {service.description}
                            </p>
                            <div className="flex flex-wrap gap-1 mt-2">
                              {service.keywords?.slice(0, 3).map((keyword) => (
                                <span
                                  key={keyword}
                                  className="inline-flex px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded"
                                >
                                  {keyword}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
        </div>
      )}
    </div>
  )
}
