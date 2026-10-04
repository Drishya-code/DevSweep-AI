import { NavLink, useLocation } from 'react-router-dom'
import { useEffect, useRef } from 'react'
import { cn } from '../utils/helpers'
import {
  LayoutDashboard,
  FolderGit2,
  Search,
  FileText,
  History,
  RotateCcw,
  Bot,
  Settings,
  Sparkles,
  X,
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Projects', href: '/projects', icon: FolderGit2 },
  { name: 'Scan Workspace', href: '/scan', icon: Search },
  { name: 'Cleanup Plans', href: '/plans', icon: FileText },
  { name: 'Cleanup History', href: '/history', icon: History },
  { name: 'Restore', href: '/restore', icon: RotateCcw },
  { name: 'AI Agent', href: '/agent', icon: Bot },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function Sidebar({ mobileOpen = false, onNavigate, onClose }: { mobileOpen?: boolean; onNavigate?: () => void; onClose?: () => void }) {
  const location = useLocation()
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const dialogRef = useRef<HTMLElement>(null)

  useEffect(() => {
    if (!mobileOpen) return
    closeButtonRef.current?.focus()
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose?.()
      if (event.key === 'Tab' && dialogRef.current) {
        const focusable = dialogRef.current.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])')
        const first = focusable.item(0)
        const last = focusable.item(focusable.length - 1)
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last?.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first?.focus()
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [mobileOpen, onClose])

  return (
    <>
    {mobileOpen && <button type="button" className="fixed inset-0 z-modal bg-devsweep-overlay/60 lg:hidden" onClick={onClose} aria-label="Dismiss navigation backdrop" />}
    <aside ref={dialogRef} id="primary-navigation" role={mobileOpen ? 'dialog' : undefined} aria-modal={mobileOpen ? true : undefined} aria-label="Primary navigation" className={cn('w-64 bg-devsweep-bgSecondary border-r border-devsweep-border flex-col h-full', mobileOpen ? 'fixed inset-y-0 left-0 z-modal flex shadow-xl lg:static lg:z-auto lg:shadow-none' : 'hidden lg:flex')}>
      <div className="p-4 border-b border-devsweep-border">
        {mobileOpen && <button ref={closeButtonRef} type="button" onClick={onClose} className="float-right rounded-lg p-2 text-devsweep-textSecondary hover:bg-devsweep-bgTertiary hover:text-devsweep-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-devsweep-accent lg:hidden" aria-label="Close navigation menu"><X className="h-5 w-5" aria-hidden="true" /></button>}
        <NavLink to="/" className="flex items-center gap-3">
          <div className="w-8 h-8 bg-devsweep-accent rounded-lg flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-devsweep-bg" />
          </div>
          <div>
            <h1 className="font-semibold text-lg">DevSweep AI</h1>
            <p className="text-xs text-devsweep-textMuted">Clean. Keep. Restore.</p>
          </div>
        </NavLink>
      </div>

      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href || 
            (item.href !== '/' && location.pathname.startsWith(item.href))
          return (
            <NavLink
              key={item.name}
              to={item.href}
              onClick={onNavigate}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-devsweep-accent focus-visible:ring-offset-2 focus-visible:ring-offset-devsweep-bgSecondary',
                isActive
                  ? 'bg-devsweep-accent/10 text-devsweep-accent border border-devsweep-accent/20'
                  : 'text-devsweep-textSecondary hover:text-devsweep-text hover:bg-devsweep-bgTertiary'
              )}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
              {item.name}
            </NavLink>
          )
        })}
      </nav>

      <div className="p-3 border-t border-devsweep-border">
        <div className="text-xs text-devsweep-textMuted text-center">
          v0.1.0 • Nebius + NVIDIA
        </div>
      </div>
    </aside>
    </>
  )
}
