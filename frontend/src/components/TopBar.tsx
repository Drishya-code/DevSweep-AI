import { cn } from '../utils/helpers'
import { Sparkles, Database, HardDrive, CheckCircle, AlertCircle, XCircle, Bot, Menu } from 'lucide-react'
import { useDevSweep } from '../context/DevSweepContext'

export function TopBar() {
  const { currentProject, demoMode, aiProvider, aiModel } = useDevSweep()

  const getStorageUsed = () => {
    if (!currentProject) return '0 B'
    const total = currentProject.cleanup_candidates.reduce((sum, c) => sum + c.size_bytes, 0)
    return formatBytes(total)
  }

  const getRecoverable = () => {
    if (!currentProject) return '0 B'
    return currentProject.total_recoverable_human
  }

  const getProjectHealth = () => {
    if (!currentProject) return { label: 'Unknown', color: 'text-devsweep-textMuted', icon: AlertCircle }
    if (!currentProject.git_clean) return { label: 'Uncommitted Changes', color: 'text-devsweep-warning', icon: AlertCircle }
    if (currentProject.cleanup_candidates.some(c => c.risk === 'DANGEROUS')) {
      return { label: 'Risky Items Found', color: 'text-devsweep-danger', icon: XCircle }
    }
    return { label: 'Healthy', color: 'text-devsweep-success', icon: CheckCircle }
  }

  const health = getProjectHealth()

  return (
    <header className="h-16 bg-devsweep-bgSecondary border-b border-devsweep-border flex items-center justify-between px-6">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-devsweep-accent" />
          <span className="font-semibold text-lg">DevSweep AI</span>
        </div>

        {currentProject && (
          <div className="hidden md:flex items-center gap-4 px-4 py-2 bg-devsweep-bg rounded-lg border border-devsweep-border">
            <span className="text-xs text-devsweep-textMuted">Project:</span>
            <span className="font-medium text-sm truncate max-w-[200px]">
              {currentProject.project_path.split('/').pop() || currentProject.project_path}
            </span>
            <span className="text-xs text-devsweep-textMuted">({currentProject.framework})</span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-6">
        <div className="hidden sm:flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2 text-devsweep-textSecondary">
            <Database className="w-4 h-4" />
            <span>Used: <span className="text-devsweep-text font-mono">{getStorageUsed()}</span></span>
          </div>
          <div className="flex items-center gap-2 text-devsweep-success">
            <HardDrive className="w-4 h-4" />
            <span>Recoverable: <span className="font-mono">{getRecoverable()}</span></span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className={cn('flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium', health.color)}>
            <health.icon className="w-3 h-3" />
            {health.label}
          </div>

          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-devsweep-bg rounded-lg border border-devsweep-border text-xs text-devsweep-textMuted">
            <Bot className="w-3 h-3" />
            <span>{aiProvider}</span>
            <span className="text-devsweep-border">/</span>
            <span>{aiModel}</span>
          </div>

          {demoMode && (
            <span className="px-2 py-1 bg-devsweep-warning/10 text-devsweep-warning text-xs font-medium rounded-full border border-devsweep-warning/20">
              DEMO
            </span>
          )}
        </div>
      </div>
    </header>
  )
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}