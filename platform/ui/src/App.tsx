import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from './components/layout/MainLayout'
import Dashboard from './pages/Dashboard'
import Agents from './pages/Agents'
import Services from './pages/Services'
import Workflows from './pages/Workflows'
import Goals from './pages/Goals'
import Monitoring from './pages/Monitoring'
import { useEffect } from 'react'
import { wsManager } from './api/websocket'

function App() {
  useEffect(() => {
    // Connect WebSocket on app mount
    wsManager.connect()

    // Cleanup on unmount
    return () => {
      wsManager.disconnect()
    }
  }, [])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="agents" element={<Agents />} />
          <Route path="services" element={<Services />} />
          <Route path="workflows" element={<Workflows />} />
          <Route path="goals" element={<Goals />} />
          <Route path="monitoring" element={<Monitoring />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
