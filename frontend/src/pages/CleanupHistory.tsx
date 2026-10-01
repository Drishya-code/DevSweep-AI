import { cn, formatBytes } from '../utils/helpers'
import { useDevSweep } from '../context/DevSweepContext'
import {
  History,
  CheckCircle,
  XCircle,
  Eye,
  RotateCcw,
  AlertTriangle,
} from 'lucide-react'

export function CleanupHistory() {
  const { cleanupHistory } = useDevSweep()

  return (
    <div className="space-y-6 animate-in">
      <div>
        <h1 className="text-2xl font-bold">Cleanup History <span className="text-xs bg-devsweep-warning/10 text-devsweep-warning px-2 py-0.5 rounded ml-2">Preview</span></h1>
        <p className="text-devsweep-textSecondary mt-1">Audit trail of all cleanup operations (Preview: history persistence not yet implemented)</p>
      </div>

      <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-12 text-center">
        <History className="w-16 h-16 mx-auto mb-4 text-devsweep-textMuted opacity-50" />
        <AlertTriangle className="w-8 h-8 mx-auto mb-4 text-devsweep-warning/50" />
        <h3 className="text-lg font-medium mb-2">History Feature Preview</h3>
        <p className="text-devsweep-textMuted mb-6">Cleanup history persistence is not yet implemented. This page shows a preview of the planned interface.</p>
        <div className="text-left max-w-md mx-auto text-sm space-y-2 text-devsweep-textSecondary">
          <p>• <strong>Planned:</strong> Persistent cleanup history with timestamps</p>
          <p>• <strong>Planned:</strong> Space recovered tracking per project</p>
          <p>• <strong>Planned:</strong> Verification status per operation</p>
          <p>• <strong>Planned:</strong> One-click restore from history</p>
        </div>
      </div>
    </div>
  )
}