import { Routes, Route } from 'react-router-dom'
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

function Layout() {
  return (
    <div className="flex h-screen bg-devsweep-bg overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-6">
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
      <Layout />
    </DevSweepProvider>
  )
}

export default App