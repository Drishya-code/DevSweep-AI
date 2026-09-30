import { cn, formatBytes } from '../utils/helpers'
import { useDevSweep } from '../context/DevSweepContext'
import {
  History,
  CheckCircle,
  XCircle,
  Eye,
  RotateCcw,
} from 'lucide-react'

export function CleanupHistory() {
  const { cleanupHistory } = useDevSweep()

  // Mock history data
  const mockHistory = [
    {
      id: '1',
      date: '2026-09-28',
      project: 'my-react-app',
      items_removed: ['node_modules', 'dist', '.vite'],
      space_recovered: 2306000000,
      verification_passed: true,
      duration_seconds: 45,
    },
    {
      id: '2',
      date: '2026-09-25',
      project: 'python-api',
      items_removed: ['__pycache__', '.pytest_cache', 'venv'],
      space_recovered: 524000000,
      verification_passed: true,
      duration_seconds: 32,
    },
    {
      id: '3',
      date: '2026-09-20',
      project: 'legacy-project',
      items_removed: ['node_modules', 'build', 'coverage'],
      space_recovered: 1800000000,
      verification_passed: false,
      duration_seconds: 120,
    },
  ]

  return (
    <div className="space-y-6 animate-in">
      <div>
        <h1 className="text-2xl font-bold">Cleanup History</h1>
        <p className="text-devsweep-textSecondary mt-1">Audit trail of all cleanup operations</p>
      </div>

      {mockHistory.length === 0 ? (
        <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-12 text-center">
          <History className="w-16 h-16 mx-auto mb-4 text-devsweep-textMuted opacity-50" />
          <h3 className="text-lg font-medium mb-2">No cleanup history yet</h3>
          <p className="text-devsweep-textMuted">Cleanup operations will appear here</p>
        </div>
      ) : (
        <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-devsweep-border bg-devsweep-bgTertiary/50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-devsweep-textMuted uppercase tracking-wider">Date</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-devsweep-textMuted uppercase tracking-wider">Project</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-devsweep-textMuted uppercase tracking-wider">Items Removed</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-devsweep-textMuted uppercase tracking-wider">Space Recovered</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-devsweep-textMuted uppercase tracking-wider">Verification</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-devsweep-textMuted uppercase tracking-wider">Duration</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-devsweep-textMuted uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {mockHistory.map((entry) => (
                <tr key={entry.id} className="border-b border-devsweep-border/50 hover:bg-devsweep-bgTertiary/50 transition-colors">
                  <td className="px-4 py-3 text-sm font-mono">{entry.date}</td>
                  <td className="px-4 py-3">
                    <span className="font-medium">{entry.project}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {entry.items_removed.map((item, i) => (
                        <span key={i} className="px-2 py-0.5 text-xs bg-devsweep-bgTertiary text-devsweep-textSecondary rounded font-mono">{item}</span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-devsweep-success">{formatBytes(entry.space_recovered)}</td>
                  <td className="px-4 py-3">
                    <span className={cn('flex items-center gap-1 px-2 py-1 text-xs rounded-full font-medium',
                      entry.verification_passed ? 'bg-devsweep-success/10 text-devsweep-success' : 'bg-devsweep-danger/10 text-devsweep-danger'
                    )}>
                      {entry.verification_passed ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                      {entry.verification_passed ? 'Passed' : 'Failed'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-devsweep-textSecondary">{entry.duration_seconds}s</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button className="p-2 hover:bg-devsweep-bgTertiary rounded-lg transition-colors" title="View details">
                        <Eye className="w-4 h-4 text-devsweep-textMuted" />
                      </button>
                      <button className="p-2 hover:bg-devsweep-bgTertiary rounded-lg transition-colors" title="Restore">
                        <RotateCcw className="w-4 h-4 text-devsweep-textMuted" />
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