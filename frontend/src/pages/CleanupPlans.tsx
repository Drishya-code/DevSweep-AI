import { cn, formatBytes } from '../utils/helpers'
import { useDevSweep } from '../context/DevSweepContext'
import {
  FileText,
  CheckCircle,
  AlertCircle,
  XCircle,
  Trash2,
  Eye,
  ArrowRight,
  Clock,
  Shield,
} from 'lucide-react'

export function CleanupPlans() {
  const { currentProject, cleanupPlans } = useDevSweep()

  // Mock cleanup plan based on current project
  const mockPlan = currentProject ? {
    plan: currentProject.cleanup_candidates
      .filter(c => c.risk !== 'DANGEROUS')
      .map(c => ({
        path: c.path,
        action: 'DELETE' as const,
        risk: c.risk as 'SAFE' | 'CAUTION' | 'DANGEROUS',
        reason: c.reason,
        estimated_bytes: c.size_bytes,
        regeneration_command: c.path === 'node_modules' ? 'npm install' :
                            c.path === 'dist' ? 'npm run build' :
                            c.path === '.vite' ? 'npm run dev' : undefined,
      })),
    total_safe_recovery_bytes: currentProject.cleanup_candidates
      .filter(c => c.risk === 'SAFE')
      .reduce((s, c) => s + c.size_bytes, 0),
    total_caution_recovery_bytes: currentProject.cleanup_candidates
      .filter(c => c.risk === 'CAUTION')
      .reduce((s, c) => s + c.size_bytes, 0),
    requires_approval: true,
    warnings: ['This will remove regenerable artifacts. Source code and Git history are protected.'],
    verification_steps: ['Run npm install', 'Run npm run build', 'Verify tests pass'],
  } : null

  const getRiskIcon = (risk: string) => {
    switch (risk) {
      case 'SAFE': return <CheckCircle className="w-4 h-4 text-devsweep-success" />
      case 'CAUTION': return <AlertCircle className="w-4 h-4 text-devsweep-warning" />
      case 'DANGEROUS': return <XCircle className="w-4 h-4 text-devsweep-danger" />
    }
  }

  return (
    <div className="space-y-6 animate-in max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold">Cleanup Plans</h1>
        <p className="text-devsweep-textSecondary mt-1">Review and approve generated cleanup plans</p>
      </div>

      {!currentProject ? (
        <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-12 text-center">
          <FileText className="w-16 h-16 mx-auto mb-4 text-devsweep-textMuted opacity-50" />
          <h3 className="text-lg font-medium mb-2">No project selected</h3>
          <p className="text-devsweep-textMuted mb-6">Scan a workspace first to generate a cleanup plan</p>
        </div>
      ) : !mockPlan || mockPlan.plan.length === 0 ? (
        <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-12 text-center">
          <CheckCircle className="w-16 h-16 mx-auto mb-4 text-devsweep-success" />
          <h3 className="text-lg font-medium mb-2">Nothing to clean up</h3>
          <p className="text-devsweep-textMuted">Your project is already clean!</p>
        </div>
      ) : (
        <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl overflow-hidden">
          <div className="p-6 border-b border-devsweep-border bg-devsweep-bgTertiary/50">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">Cleanup Plan for {currentProject.project_path.split('/').pop()}</h2>
                <p className="text-devsweep-textSecondary text-sm mt-1">Review each item before approving</p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold font-mono text-devsweep-success">{formatBytes(mockPlan.total_safe_recovery_bytes)}</p>
                <p className="text-xs text-devsweep-textMuted">Safe Recovery</p>
              </div>
            </div>
          </div>

          <div className="p-6 space-y-4 max-h-[500px] overflow-y-auto">
            {mockPlan.plan.map((item, i) => (
              <div key={i} className="bg-devsweep-bg border border-devsweep-border rounded-lg p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <span className={cn('w-6 h-6 rounded flex items-center justify-center text-xs font-medium', 
                        item.risk === 'SAFE' && 'bg-devsweep-success/20 text-devsweep-success',
                        item.risk === 'CAUTION' && 'bg-devsweep-warning/20 text-devsweep-warning',
                        item.risk === 'DANGEROUS' && 'bg-devsweep-danger/20 text-devsweep-danger'
                      )}>
                        {getRiskIcon(item.risk)}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">{item.path}</p>
                        <p className="text-xs text-devsweep-textMuted">{item.reason}</p>
                      </div>
                      <span className="font-mono text-sm text-devsweep-textSecondary whitespace-nowrap">{formatBytes(item.estimated_bytes)}</span>
                    </div>
                    <div className="ml-9 flex items-center gap-2">
                      <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-devsweep-accent/10 text-devsweep-accent">
                        {item.action}
                      </span>
                      <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full', 
                        item.risk === 'SAFE' && 'bg-devsweep-success/10 text-devsweep-success border border-devsweep-success/20',
                        item.risk === 'CAUTION' && 'bg-devsweep-warning/10 text-devsweep-warning border border-devsweep-warning/20',
                        item.risk === 'DANGEROUS' && 'bg-devsweep-danger/10 text-devsweep-danger border border-devsweep-danger/20'
                      )}>
                        {item.risk}
                      </span>
                      {item.regeneration_command && (
                        <span className="px-2 py-0.5 text-xs font-mono bg-devsweep-bgTertiary text-devsweep-textMuted rounded">
                          {item.regeneration_command}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {mockPlan.warnings.length > 0 && (
              <div className="p-4 bg-devsweep-warning/10 border border-devsweep-warning/20 rounded-lg">
                <h4 className="font-medium text-devsweep-warning flex items-center gap-2 mb-2">
                  <AlertCircle className="w-4 h-4" />
                  Warnings
                </h4>
                <ul className="list-disc list-inside text-sm text-devsweep-textSecondary space-y-1">
                  {mockPlan.warnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              </div>
            )}

            <div className="p-4 bg-devsweep-accent/10 border border-devsweep-accent/20 rounded-lg">
              <h4 className="font-medium text-devsweep-accent flex items-center gap-2 mb-2">
                <Shield className="w-4 h-4" />
                Verification Steps (After Cleanup)
              </h4>
              <ol className="list-decimal list-inside text-sm text-devsweep-textSecondary space-y-1">
                {mockPlan.verification_steps.map((v, i) => <li key={i}>{v}</li>)}
              </ol>
            </div>
          </div>

          <div className="p-6 border-t border-devsweep-border bg-devsweep-bgTertiary/50 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" className="w-4 h-4 rounded border-devsweep-border text-devsweep-accent focus:ring-devsweep-accent" />
                <span className="text-sm">I understand this will delete the selected items and have reviewed the plan</span>
              </label>
            </div>
            <button className="px-6 py-2 bg-devsweep-accent text-devsweep-bg rounded-lg font-medium hover:bg-devsweep-accentHover transition-colors flex items-center gap-2">
              <Trash2 className="w-4 h-4" />
              Approve & Execute Cleanup
            </button>
          </div>
        </div>
      )}
    </div>
  )
}