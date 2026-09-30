import { cn, formatBytes } from '../utils/helpers'
import { useDevSweep } from '../context/DevSweepContext'
import {
  Database,
  HardDrive,
  Search,
  Sparkles,
  FolderGit2,
  TrendingUp,
  CheckCircle,
  AlertCircle,
  XCircle,
  Bot,
  FileText,
  RotateCcw,
} from 'lucide-react'
import { Link } from 'react-router-dom'

export function Dashboard() {
  const { currentProject, scanHistory, isScanning, demoMode, setIsScanning, addScanToHistory } = useDevSweep()

  const handleScanDemo = async () => {
    setIsScanning(true)
    try {
      const res = await fetch('/api/scan/demo')
      const data = await res.json()
      addScanToHistory(data)
      setIsScanning(false)
    } catch (error) {
      console.error('Demo scan failed:', error)
      setIsScanning(false)
    }
  }

  const handleScanWorkspace = async () => {
    setIsScanning(true)
    try {
      const res = await fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      const data = await res.json()
      addScanToHistory(data)
      setIsScanning(false)
    } catch (error) {
      console.error('Workspace scan failed:', error)
      setIsScanning(false)
    }
  }

  const getTotalScanned = () => scanHistory.length
  const getTotalRecoverable = () => scanHistory.reduce((sum, s) => sum + s.total_recoverable_bytes, 0)
  const getLastScan = () => scanHistory[0]?.project_path ? new Date().toLocaleDateString() : 'Never'

  const stats = [
    { label: 'Storage Used', value: currentProject ? formatBytes(currentProject.cleanup_candidates.reduce((s, c) => s + c.size_bytes, 0)) : '0 B', icon: Database, color: 'text-devsweep-text' },
    { label: 'Recoverable', value: currentProject?.total_recoverable_human || '0 B', icon: HardDrive, color: 'text-devsweep-success' },
    { label: 'Projects Scanned', value: getTotalScanned().toString(), icon: FolderGit2, color: 'text-devsweep-accent' },
    { label: 'Total Cleanup Opportunities', value: formatBytes(getTotalRecoverable()), icon: TrendingUp, color: 'text-devsweep-warning' },
  ]

  const healthStatus = currentProject ? (
    currentProject.git_clean
      ? currentProject.cleanup_candidates.some(c => c.risk === 'DANGEROUS')
        ? { label: 'Risky Items Detected', color: 'text-devsweep-danger bg-devsweep-danger/10 border-devsweep-danger/20', icon: XCircle }
        : { label: 'Healthy', color: 'text-devsweep-success bg-devsweep-success/10 border-devsweep-success/20', icon: CheckCircle }
      : { label: 'Uncommitted Changes', color: 'text-devsweep-warning bg-devsweep-warning/10 border-devsweep-warning/20', icon: AlertCircle }
  ) : { label: 'No Project Scanned', color: 'text-devsweep-textMuted bg-devsweep-bgTertiary/50 border-devsweep-border', icon: Bot }

  const HealthIcon = healthStatus.icon

  return (
    <div className="space-y-6 animate-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-devsweep-textSecondary mt-1">Overview of your workspace cleanup opportunities</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleScanDemo}
            disabled={isScanning}
            className={cn(
              'px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2',
              'bg-devsweep-warning/10 text-devsweep-warning border border-devsweep-warning/20 hover:bg-devsweep-warning/20'
            )}
          >
            <Sparkles className="w-4 h-4" />
            Scan Demo Project
          </button>
          <button
            onClick={handleScanWorkspace}
            disabled={isScanning}
            className={cn(
              'px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2',
              'bg-devsweep-accent text-devsweep-bg hover:bg-devsweep-accentHover'
            )}
          >
            <Search className="w-4 h-4" />
            {isScanning ? 'Scanning...' : 'Scan Workspace'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, i) => (
          <div key={i} className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-5">
            <div className="flex items-center gap-3">
              <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center', stat.color + '/10 bg-' + stat.color.replace('text-', '') + '/10')}>
                <stat.icon className={cn('w-5 h-5', stat.color)} />
              </div>
              <div>
                <p className="text-xs text-devsweep-textMuted">{stat.label}</p>
                <p className="text-xl font-bold font-mono">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-5">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-devsweep-accent" />
            Storage Breakdown
          </h2>
          {currentProject ? (
            <div className="space-y-3">
              {currentProject.cleanup_candidates.map((candidate, i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-devsweep-border last:border-0">
                  <div className="flex items-center gap-3">
                    <span className={cn('w-6 h-6 rounded flex items-center justify-center text-xs font-medium', 
                      candidate.risk === 'SAFE' && 'bg-devsweep-success/20 text-devsweep-success',
                      candidate.risk === 'CAUTION' && 'bg-devsweep-warning/20 text-devsweep-warning',
                      candidate.risk === 'DANGEROUS' && 'bg-devsweep-danger/20 text-devsweep-danger'
                    )}>
                      {candidate.risk === 'SAFE' && '✓'}
                      {candidate.risk === 'CAUTION' && '⚠'}
                      {candidate.risk === 'DANGEROUS' && '✕'}
                    </span>
                    <div>
                      <p className="font-medium text-sm">{candidate.path}</p>
                      <p className="text-xs text-devsweep-textMuted">{candidate.reason}</p>
                    </div>
                  </div>
                  <span className="font-mono text-sm text-devsweep-textSecondary">{candidate.size_human}</span>
                </div>
              ))}
              {currentProject.cleanup_candidates.length === 0 && (
                <p className="text-devsweep-textMuted text-center py-8">No cleanup candidates found. Your workspace is clean!</p>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-devsweep-textMuted">
              <Sparkles className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No project scanned yet. Click "Scan Workspace" or "Scan Demo Project" to begin.</p>
            </div>
          )}
        </div>

        <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-5 space-y-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-devsweep-success" />
            Project Health
          </h2>
          <div className={cn('p-4 rounded-lg border', healthStatus.color)}>
            <div className="flex items-center gap-3">
              <HealthIcon className={cn('w-6 h-6', healthStatus.color.replace('bg-', '').replace('border-', '').replace('text-', 'text-'))} />
              <span className="font-medium">{healthStatus.label}</span>
            </div>
            {currentProject && (
              <div className="mt-3 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-devsweep-textSecondary">Type</span>
                  <span className="font-mono">{currentProject.project_type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-devsweep-textSecondary">Framework</span>
                  <span className="font-mono">{currentProject.framework}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-devsweep-textSecondary">Language</span>
                  <span className="font-mono">{currentProject.language}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-devsweep-textSecondary">Package Manager</span>
                  <span className="font-mono">{currentProject.package_manager}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-devsweep-textSecondary">Git</span>
                  <span className={cn('font-mono', currentProject.git_clean ? 'text-devsweep-success' : 'text-devsweep-warning')}>
                    {currentProject.git_clean ? 'Clean' : 'Uncommitted Changes'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-devsweep-textSecondary">Last Scan</span>
                  <span className="font-mono">{getLastScan()}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-5">
        <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Link to="/scan" className={cn('p-4 rounded-lg border border-devsweep-border hover:border-devsweep-accent/50 transition-colors text-center')}>
            <Search className="w-8 h-8 mx-auto mb-2 text-devsweep-accent" />
            <p className="font-medium">Scan Workspace</p>
            <p className="text-xs text-devsweep-textMuted mt-1">Analyze a project for cleanup opportunities</p>
          </Link>
          <Link to="/plans" className={cn('p-4 rounded-lg border border-devsweep-border hover:border-devsweep-accent/50 transition-colors text-center')}>
            <FileText className="w-8 h-8 mx-auto mb-2 text-devsweep-warning" />
            <p className="font-medium">Review Cleanup Plans</p>
            <p className="text-xs text-devsweep-textMuted mt-1">View and approve generated cleanup plans</p>
          </Link>
          <Link to="/restore" className={cn('p-4 rounded-lg border border-devsweep-border hover:border-devsweep-accent/50 transition-colors text-center')}>
            <RotateCcw className="w-8 h-8 mx-auto mb-2 text-devsweep-success" />
            <p className="font-medium">Restore Project</p>
            <p className="text-xs text-devsweep-textMuted mt-1">Reconstruct cleaned environments</p>
          </Link>
        </div>
      </div>
    </div>
  )
}