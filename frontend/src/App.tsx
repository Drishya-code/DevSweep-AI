import { Routes, Route } from 'react-router-dom'
import { useCallback, useState } from 'react'
import { Sidebar } from './components/Sidebar'
import { TopBar } from './components/TopBar'
import { Dashboard } from './pages/Dashboard'
import { Projects } from './pages/Projects'
import { ScanWorkspace } from './pages/ScanWorkspace'
import { CleanupPlans } from './pages/CleanupPlans'
import { CleanupHistory } from './pages/CleanupHistory'
import { RestoreCenter } from './pages/RestoreCenter'
import { AIAgent } from './pages/AIAgent'
import { Settings } from './pages/Settings'
import { DevSweepProvider } from './context/DevSweepContext'
import { ViewModeProvider } from './context/ViewModeContext'

function Layout() {
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false)
  const closeMobileNavigation = useCallback(() => setMobileNavigationOpen(false), [])
  const openMobileNavigation = useCallback(() => setMobileNavigationOpen(true), [])
  return (
    <div className="flex h-screen bg-devsweep-bg overflow-hidden">
      <Sidebar mobileOpen={mobileNavigationOpen} onClose={closeMobileNavigation} onNavigate={closeMobileNavigation} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar onOpenNavigation={openMobileNavigation} navigationOpen={mobileNavigationOpen} />
        <main id="main-content" className="flex-1 overflow-y-auto p-4 sm:p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/scan" element={<ScanWorkspace />} />
            <Route path="/plans" element={<CleanupPlans />} />
            <Route path="/history" element={<CleanupHistory />} />
            <Route path="/restore" element={<RestoreCenter />} />
            <Route path="/agent" element={<AIAgent />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

function App() {
  return (
    <DevSweepProvider>
      <ViewModeProvider>
        <Layout />
      </ViewModeProvider>
    </DevSweepProvider>
  )
}

export default App
