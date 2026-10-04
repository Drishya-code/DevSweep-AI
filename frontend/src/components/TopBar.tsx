import { cn } from '../utils/helpers'
import { Sparkles, Database, HardDrive, CheckCircle, AlertCircle, XCircle, Bot, Menu, Sun, Moon, Code, LayoutDashboard } from 'lucide-react'
import { useDevSweep } from '../context/DevSweepContext'
import { useViewMode } from '../context/ViewModeContext'
import { formatBytes as formatBytesUtil } from '../design-tokens'
import { useState, useEffect, useRef } from 'react'

export function TopBar({ onOpenNavigation, navigationOpen = false }: { onOpenNavigation?: () => void; navigationOpen?: boolean }) {
  const { currentProject, demoMode, aiProvider, aiModel } = useDevSweep()
  const { viewMode, setViewMode } = useViewMode()
  const [theme, setTheme] = useState<'light' | 'dark'>('dark')
  const navigationButtonRef = useRef<HTMLButtonElement>(null)
  const wasNavigationOpen = useRef(false)

  useEffect(() => {
    const stored = localStorage.getItem('devsweep-theme') as 'light' | 'dark' | null
    if (stored) {
      setTheme(stored)
      document.documentElement.setAttribute('data-theme', stored)
    } else if (window.matchMedia?.('(prefers-color-scheme: light)')?.matches) {
      setTheme('light')
      document.documentElement.setAttribute('data-theme', 'light')
    }
  }, [])

  useEffect(() => {
    if (wasNavigationOpen.current && !navigationOpen) navigationButtonRef.current?.focus()
    wasNavigationOpen.current = navigationOpen
  }, [navigationOpen])

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light'
    setTheme(newTheme)
    localStorage.setItem('devsweep-theme', newTheme)
    document.documentElement.setAttribute('data-theme', newTheme)
  }

  const getCandidateSize = () => {
    if (!currentProject) return '—'
    const total = currentProject.cleanup_candidates.reduce((sum, c) => sum + c.size_bytes, 0)
    return formatBytesUtil(total)
  }

  const getRecoverable = () => {
    if (!currentProject) return '—'
    return currentProject.total_recoverable_human
  }

  const getProjectHealth = () => {
    if (!currentProject) return { label: 'Unknown', color: 'text-devsweep-textMuted', icon: AlertCircle }
    if (!currentProject.has_git) return { label: 'Git Not Detected', color: 'text-devsweep-textMuted', icon: AlertCircle }
    if (!currentProject.git_clean) return { label: 'Uncommitted Changes', color: 'text-devsweep-warning', icon: AlertCircle }
    if (currentProject.cleanup_candidates.some(c => c.risk === 'DANGEROUS')) {
      return { label: 'Risky Items Found', color: 'text-devsweep-danger', icon: XCircle }
    }
    return { label: 'Healthy', color: 'text-devsweep-success', icon: CheckCircle }
  }

  const health = getProjectHealth()

  return (
    <header className="min-h-16 bg-devsweep-bgSecondary border-b border-devsweep-border flex items-center justify-between gap-2 px-3 md:px-6">
      <div className="flex min-w-0 items-center gap-2 md:gap-6">
        {onOpenNavigation && <button ref={navigationButtonRef} type="button" onClick={onOpenNavigation} className="lg:hidden rounded-lg p-2 text-devsweep-textSecondary hover:bg-devsweep-bgTertiary hover:text-devsweep-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-devsweep-accent" aria-label="Open navigation menu" aria-haspopup="dialog" aria-expanded={navigationOpen} aria-controls="primary-navigation"><Menu className="h-5 w-5" aria-hidden="true" /></button>}
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-devsweep-accent" />
          <span className="hidden font-semibold text-lg sm:inline">DevSweep AI</span>
        </div>

        {currentProject && (
          <div className="hidden xl:flex items-center gap-4 px-4 py-2 bg-devsweep-bg rounded-lg border border-devsweep-border">
            <span className="text-xs text-devsweep-textMuted">Project:</span>
            <span className="font-medium text-sm truncate max-w-[200px]">
              {currentProject.project_path.split('/').pop() || currentProject.project_path}
            </span>
            <span className="text-xs text-devsweep-textMuted">({currentProject.framework})</span>
          </div>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-2 md:gap-6">
        <div className="hidden xl:flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2 text-devsweep-textSecondary">
            <Database className="w-4 h-4" />
            <span>Candidate size: <span className="text-devsweep-text font-mono">{getCandidateSize()}</span></span>
          </div>
          <div className="flex items-center gap-2 text-devsweep-success">
            <HardDrive className="w-4 h-4" />
            <span>Recoverable: <span className="font-mono">{getRecoverable()}</span></span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className={cn('hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium', health.color)}>
            <health.icon className="w-3 h-3" />
            {health.label}
          </div>

          <div className="hidden 2xl:flex items-center gap-2 px-3 py-1.5 bg-devsweep-bg rounded-lg border border-devsweep-border text-xs text-devsweep-textMuted">
            <Bot className="w-3 h-3" />
            <span>{aiProvider}</span>
            <span className="text-devsweep-border">/</span>
            <span>{aiModel}</span>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-0.5 bg-devsweep-bg rounded-lg border border-devsweep-border p-1" role="group" aria-label="View mode">
            <button
              type="button"
              onClick={() => setViewMode('simple')}
              className={cn(
                'flex items-center rounded-md px-1.5 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-devsweep-accent sm:px-3',
                viewMode === 'simple'
                  ? 'bg-devsweep-accent text-devsweep-bg'
                  : 'text-devsweep-textSecondary hover:text-devsweep-text'
              )}
              aria-pressed={viewMode === 'simple'}
            >
              <LayoutDashboard className="w-3 h-3 sm:mr-1" aria-hidden="true" />
              <span className="text-[10px] leading-none sm:text-xs">Simple</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('technical')}
              className={cn(
                'flex items-center rounded-md px-1.5 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-devsweep-accent sm:px-3',
                viewMode === 'technical'
                  ? 'bg-devsweep-accent text-devsweep-bg'
                  : 'text-devsweep-textSecondary hover:text-devsweep-text'
              )}
              aria-pressed={viewMode === 'technical'}
            >
              <Code className="w-3 h-3 sm:mr-1" aria-hidden="true" />
              <span className="text-[10px] leading-none sm:text-xs">Technical</span>
            </button>
          </div>

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="rounded-lg bg-devsweep-bg border border-devsweep-border p-2 text-devsweep-textSecondary hover:text-devsweep-text hover:bg-devsweep-bgTertiary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-devsweep-accent"
            aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
          >
            {theme === 'light' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
          </button>

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
