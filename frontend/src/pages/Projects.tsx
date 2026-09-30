import { cn } from '../utils/helpers'
import { FolderGit2, Search, Plus, ChevronDown, ChevronUp, Eye, Trash2, Clock } from 'lucide-react'
import { useDevSweep } from '../context/DevSweepContext'

export function Projects() {
  const { scanHistory, currentProject, setCurrentProject } = useDevSweep()

  return (
    <div className="space-y-6 animate-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Projects</h1>
          <p className="text-devsweep-textSecondary mt-1">Manage and track your scanned projects</p>
        </div>
        <button className="px-4 py-2 bg-devsweep-accent text-devsweep-bg rounded-lg font-medium flex items-center gap-2 hover:bg-devsweep-accentHover transition-colors">
          <Plus className="w-4 h-4" />
          Add Project
        </button>
      </div>

      {scanHistory.length === 0 ? (
        <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-12 text-center">
          <FolderGit2 className="w-16 h-16 mx-auto mb-4 text-devsweep-textMuted opacity-50" />
          <h3 className="text-lg font-medium mb-2">No projects scanned yet</h3>
          <p className="text-devsweep-textMuted mb-6">Scan a workspace to add your first project</p>
          <button className="px-6 py-3 bg-devsweep-accent text-devsweep-bg rounded-lg font-medium hover:bg-devsweep-accentHover transition-colors">
            Scan Workspace
          </button>
        </div>
      ) : (
        <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-devsweep-border bg-devsweep-bgTertiary/50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-devsweep-textMuted uppercase tracking-wider">Project</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-devsweep-textMuted uppercase tracking-wider">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-devsweep-textMuted uppercase tracking-wider">Framework</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-devsweep-textMuted uppercase tracking-wider">Recoverable</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-devsweep-textMuted uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-devsweep-textMuted uppercase tracking-wider">Last Scan</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-devsweep-textMuted uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {scanHistory.map((scan, i) => (
                <tr key={i} className="border-b border-devsweep-border/50 hover:bg-devsweep-bgTertiary/50 transition-colors">
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium text-sm truncate max-w-[250px]">{scan.project_path.split('/').pop() || scan.project_path}</p>
                      <p className="text-xs text-devsweep-textMuted font-mono">{scan.project_path}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 text-xs rounded-full bg-devsweep-bgTertiary text-devsweep-textSecondary font-mono">{scan.project_type}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 text-xs rounded-full bg-devsweep-accent/10 text-devsweep-accent font-mono">{scan.framework}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-mono text-sm text-devsweep-success">{scan.total_recoverable_human}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn('px-2 py-1 text-xs rounded-full font-medium',
                      scan.git_clean ? 'bg-devsweep-success/10 text-devsweep-success' : 'bg-devsweep-warning/10 text-devsweep-warning'
                    )}>
                      {scan.git_clean ? 'Clean' : 'Uncommitted'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-devsweep-textSecondary text-sm">Just now</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button className="p-2 hover:bg-devsweep-bgTertiary rounded-lg transition-colors" title="View details">
                        <Eye className="w-4 h-4 text-devsweep-textMuted" />
                      </button>
                      <button 
                        onClick={() => setCurrentProject(scan)}
                        className="p-2 hover:bg-devsweep-bgTertiary rounded-lg transition-colors font-medium text-sm text-devsweep-accent"
                      >
                        Select
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}