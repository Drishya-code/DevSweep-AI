import { NavLink, useLocation } from 'react-router-dom'
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

export function Sidebar() {
  const location = useLocation()

  return (
    <aside className="w-64 bg-devsweep-bgSecondary border-r border-devsweep-border flex flex-col h-full">
      <div className="p-4 border-b border-devsweep-border">
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
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
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
  )
}