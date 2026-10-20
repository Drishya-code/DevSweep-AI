import { Routes, Route } from 'react-router-dom'
import { useCallback, useEffect, useState } from 'react'
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
import { HostedDemo } from './pages/HostedDemo'
import { requestJson } from './utils/api'
import { RealWorkspace } from './pages/RealWorkspace'
import { Link } from 'react-router-dom'

type RuntimeConfig = { hosted_demo?: boolean }

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
            <Route path="/real-workspace" element={<RealWorkspace />} />
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
  const [runtime, setRuntime] = useState<RuntimeConfig | null>(null)
  const [configError, setConfigError] = useState('')
  useEffect(() => {
    requestJson<RuntimeConfig>('/api/config')
      .then(setRuntime)
      .catch(error => setConfigError(error instanceof Error ? error.message : 'The DevSweep backend is unavailable.'))
  }, [])

  if (configError) return <main className="flex min-h-screen items-center justify-center bg-devsweep-bg p-6"><section role="alert" className="max-w-lg rounded-2xl border border-devsweep-border bg-devsweep-bgSecondary p-6"><h1 className="text-xl font-semibold text-devsweep-text">DevSweep backend unavailable</h1><p className="mt-2 text-devsweep-textMuted">{configError} Start the backend and check the API connection, then reload this page.</p></section></main>
  if (!runtime) return <main className="flex min-h-screen items-center justify-center bg-devsweep-bg text-devsweep-text">Connecting to DevSweep…</main>
  if (runtime.hosted_demo) return <ViewModeProvider><main className="min-h-screen overflow-y-auto bg-devsweep-bg p-4 sm:p-8"><nav className="mx-auto mb-6 flex max-w-5xl gap-4 text-sm"><Link className="text-devsweep-accent underline" to="/">Synthetic judge demo</Link><Link className="text-devsweep-accent underline" to="/real-workspace">Choose my folder</Link></nav><Routes><Route path="/" element={<HostedDemo />} /><Route path="/real-workspace" element={<RealWorkspace />} /></Routes></main></ViewModeProvider>
  return (
    <DevSweepProvider>
      <ViewModeProvider>
        <Layout />
      </ViewModeProvider>
    </DevSweepProvider>
  )
}

export default App
