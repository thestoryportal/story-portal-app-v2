import { Outlet, NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Users,
  Package,
  Workflow,
  Target,
  Activity,
  Circle
} from 'lucide-react'
import { wsManager } from '../../api/websocket'
import { useState, useEffect } from 'react'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Agents', href: '/agents', icon: Users },
  { name: 'Services', href: '/services', icon: Package },
  { name: 'Workflows', href: '/workflows', icon: Workflow },
  { name: 'Goals', href: '/goals', icon: Target },
  { name: 'Monitoring', href: '/monitoring', icon: Activity },
]

export default function MainLayout() {
  const [wsStatus, setWsStatus] = useState<'connected' | 'disconnected' | 'connecting'>('disconnected')

  useEffect(() => {
    const checkStatus = () => {
      setWsStatus(wsManager.getConnectionStatus())
    }

    checkStatus()
    const interval = setInterval(checkStatus, 1000)

    return () => clearInterval(interval)
  }, [])

  const statusColors = {
    connected: 'bg-green-500',
    connecting: 'bg-yellow-500',
    disconnected: 'bg-red-500',
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
                <LayoutDashboard className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Platform Control Center</h1>
                <p className="text-sm text-gray-500">V2.0.0</p>
              </div>
            </div>

            {/* WebSocket Status */}
            <div className="flex items-center space-x-2">
              <Circle className={`w-3 h-3 ${statusColors[wsStatus]}`} fill="currentColor" />
              <span className="text-sm text-gray-600 capitalize">{wsStatus}</span>
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar Navigation */}
        <nav className="w-64 bg-white border-r border-gray-200 min-h-[calc(100vh-73px)]">
          <div className="px-3 py-4 space-y-1">
            {navigation.map((item) => (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                  }`
                }
              >
                <item.icon className="w-5 h-5" />
                <span>{item.name}</span>
              </NavLink>
            ))}
          </div>
        </nav>

        {/* Main Content */}
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
