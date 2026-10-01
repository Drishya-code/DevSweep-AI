import { useState } from 'react'
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
  Loader2,
  Bot,
  Sparkles,
  ShieldCheck,
} from 'lucide-react'

export function CleanupPlans() {
  const { currentProject, setCurrentPlan, addCleanupToHistory } = useDevSweep()
  const [plan, setPlan] = useState<{
    plan_id: string
    items: Array<{
      path: string
      action: 'DELETE' | 'KEEP'
      risk: 'SAFE' | 'CAUTION' | 'DANGEROUS'
      scanner_risk?: 'SAFE' | 'CAUTION' | 'DANGEROUS'
      ai_risk?: 'SAFE' | 'CAUTION' | 'DANGEROUS'
      effective_risk?: 'SAFE' | 'CAUTION' | 'DANGEROUS'
      reason: string
      estimated_bytes: number
      regeneration_command?: string
    }>
    total_safe_bytes: number
    total_caution_bytes: number
    total_dangerous_bytes: number
    requires_approval: boolean
    warnings: string[]
    verification_steps: string[]
  } | null>(null)
  const [loading, setLoading] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [executed, setExecuted] = useState(false)
  const [execResult, setExecResult] = useState<{
      success: boolean
      items_deleted: number
      items_failed: number
      bytes_freed: number
      bytes_freed_human: string
      errors: string[]
      duration_seconds: number
    } | null>(null)
    const [verifyResult, setVerifyResult] = useState<{
      passed: boolean
      checks: Array<{ name: string; passed: boolean; message: string }>
      errors: string[]
    } | null>(null)
    const [error, setError] = useState<string | null>(null)
  const [confirmed, setConfirmed] = useState(false)

  const getRiskIcon = (risk: string) => {
    switch (risk) {
      case 'SAFE': return <CheckCircle className="w-4 h-4 text-devsweep-success" />
      case 'CAUTION': return <AlertCircle className="w-4 h-4 text-devsweep-warning" />
      case 'DANGEROUS': return <XCircle className="w-4 h-4 text-devsweep-danger" />
    }
  }

  const generatePlan = async () => {
      if (!currentProject) return
      setLoading(true)
      setError(null)
      setConfirmed(false) // Reset confirmation when new plan generated
      try {
        const res = await fetch('/api/cleanup/generate-plan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project_path: currentProject.project_path }),
        })
        if (!res.ok) {
          const err = await res.json()
          throw new Error(err.detail || 'Failed to generate plan')
        }
        const data = await res.json()
        setPlan(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to generate plan')
      } finally {
        setLoading(false)
      }
    }

  const executePlan = async () => {
        if (!plan) return
        setExecuting(true)
        setError(null)
        try {
          const res = await fetch('/api/cleanup/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ plan_id: plan.plan_id, approved: confirmed }),
          })
          if (!res.ok) {
            const err = await res.json()
            throw new Error(err.detail || 'Execution failed')
          }
          const data = await res.json()
          setExecResult(data)
          setExecuted(true)
     
          // Run verification after execution
          const verifyData = await verifyProject()
          if (verifyData) {
            setVerifyResult(verifyData)
          }
     
          // Regenerate demo data for next run
          try {
            await fetch('/api/demo/reset', { method: 'POST' })
          } catch {}
     
          if (data.success) {
            addCleanupToHistory({
              plan_id: plan.plan_id,
              items_deleted: data.items_deleted,
              items_failed: data.items_failed,
              bytes_freed: data.bytes_freed,
              bytes_freed_human: data.bytes_freed_human,
              success: data.success,
              timestamp: new Date().toISOString(),
            })
          }
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Execution failed')
        } finally {
          setExecuting(false)
        }
      }

  const verifyProject = async () => {
      if (!currentProject || !plan) return
      try {
        const res = await fetch('/api/cleanup/verify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            project_path: currentProject.project_path, 
            project_type: 'node',
            plan_id: plan.plan_id
          }),
        })
        const data = await res.json()
        return data
      } catch {
        return null
      }
    }

  const getRiskBadge = (risk: string) => (
    <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full',
      risk === 'SAFE' && 'bg-devsweep-success/10 text-devsweep-success border border-devsweep-success/20',
      risk === 'CAUTION' && 'bg-devsweep-warning/10 text-devsweep-warning border border-devsweep-warning/20',
      risk === 'DANGEROUS' && 'bg-devsweep-danger/10 text-devsweep-danger border border-devsweep-danger/20'
    )}>
      {risk}
    </span>
  )

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
          <button onClick={generatePlan} disabled={loading} className="px-6 py-2 bg-devsweep-accent text-devsweep-bg rounded-lg font-medium hover:bg-devsweep-accentHover transition-colors disabled:opacity-50">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Generate Plan'}
          </button>
        </div>
      ) : !plan ? (
        <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-6 space-y-6">
          <div className="text-center">
            <Bot className="w-16 h-16 mx-auto mb-4 text-devsweep-accent opacity-50" />
            <h3 className="text-lg font-medium mb-2">AI Analysis Ready</h3>
            <p className="text-devsweep-textMuted">Scan complete. Generate a cleanup plan with AI-powered recommendations.</p>
          </div>
          <div className="p-4 bg-devsweep-accent/10 border border-devsweep-accent/20 rounded-lg space-y-2">
            <div className="flex items-center gap-3">
              <Bot className="w-5 h-5 text-devsweep-accent" />
              <span className="font-medium">Powered by NVIDIA Nemotron via Nebius Token Factory</span>
            </div>
            <p className="text-sm text-devsweep-textSecondary ml-8">AI analyzes candidates, provides risk classification and reasoning. Application validates against safety rules before execution.</p>
          </div>
          <button onClick={generatePlan} disabled={loading} className="w-full px-6 py-3 bg-devsweep-accent text-devsweep-bg rounded-lg font-medium hover:bg-devsweep-accentHover transition-colors flex items-center justify-center gap-2 disabled:opacity-50">
            <Sparkles className="w-5 h-5" />
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Analyzing with AI...
              </>
            ) : (
              'Generate Cleanup Plan with AI'
            )}
          </button>
        </div>
      ) : !executed ? (
        <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl overflow-hidden">
          <div className="p-6 border-b border-devsweep-border bg-devsweep-bgTertiary/50">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">Cleanup Plan for {currentProject.project_path.split('/').pop()}</h2>
                <p className="text-devsweep-textSecondary text-sm mt-1">Review each item before approving</p>
              </div>
              <div className="text-right">
                              <p className="text-2xl font-bold font-mono text-devsweep-success">{formatBytes(plan.total_safe_bytes)}</p>
                              <p className="text-xs text-devsweep-textMuted">Safe Recovery (effective)</p>
                              <p className="text-2xl font-bold font-mono text-devsweep-warning">{formatBytes(plan.total_caution_bytes)}</p>
                              <p className="text-xs text-devsweep-textMuted">Caution Recovery (effective)</p>
                            </div>
            </div>
          </div>

          <div className="p-6 space-y-4 max-h-[500px] overflow-y-auto">
            {plan.items.map((item, i) => (
                          <div key={i} className="bg-devsweep-bg border border-devsweep-border rounded-lg p-4">
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-3 mb-2">
                                  {/* Use effective_risk for display */}
                                  <span className={cn('w-6 h-6 rounded flex items-center justify-center text-xs font-medium',
                                    (item.effective_risk || item.risk) === 'SAFE' && 'bg-devsweep-success/20 text-devsweep-success',
                                    (item.effective_risk || item.risk) === 'CAUTION' && 'bg-devsweep-warning/20 text-devsweep-warning',
                                    (item.effective_risk || item.risk) === 'DANGEROUS' && 'bg-devsweep-danger/20 text-devsweep-danger'
                                  )}>
                                    {getRiskIcon(item.effective_risk || item.risk)}
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
                                  {/* Show effective risk prominently */}
                                  {getRiskBadge(item.effective_risk || item.risk)}
                                  {/* Show scanner and AI risk as secondary info */}
                                  {(item.scanner_risk && item.ai_risk && item.scanner_risk !== item.ai_risk) && (
                                    <span className="px-2 py-0.5 text-xs text-devsweep-textMuted bg-devsweep-bgTertiary rounded"
                                          title="Scanner: {item.scanner_risk} → AI: {item.ai_risk}">
                                      {item.scanner_risk} → {item.ai_risk}
                                    </span>
                                  )}
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

            {plan.warnings.length > 0 && (
              <div className="p-4 bg-devsweep-warning/10 border border-devsweep-warning/20 rounded-lg">
                <h4 className="font-medium text-devsweep-warning flex items-center gap-2 mb-2">
                  <AlertCircle className="w-4 h-4" />
                  Warnings
                </h4>
                <ul className="list-disc list-inside text-sm text-devsweep-textSecondary space-y-1">
                  {plan.warnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              </div>
            )}

            <div className="p-4 bg-devsweep-accent/10 border border-devsweep-accent/20 rounded-lg">
              <h4 className="font-medium text-devsweep-accent flex items-center gap-2 mb-2">
                <ShieldCheck className="w-4 h-4" />
                Safety: AI Recommends → Application Validates → User Approves → Application Executes
              </h4>
              <ol className="list-decimal list-inside text-sm text-devsweep-textSecondary space-y-1">
                {plan.verification_steps.map((v, i) => <li key={i}>{v}</li>)}
              </ol>
            </div>
          </div>

          <div className="p-6 border-t border-devsweep-border bg-devsweep-bgTertiary/50 flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input 
                            type="checkbox" 
                            className="w-4 h-4 rounded border-devsweep-border text-devsweep-accent focus:ring-devsweep-accent"
                            checked={confirmed}
                            onChange={(e) => setConfirmed(e.target.checked)}
                          />
                          <span className="text-sm">I understand this will delete the selected items and have reviewed the plan</span>
                        </label>
                      </div>
                      <button 
                        onClick={executePlan} 
                        disabled={executing || !confirmed} 
                        className="px-6 py-3 bg-devsweep-danger/10 text-devsweep-danger border border-devsweep-danger/20 rounded-lg font-medium hover:bg-devsweep-danger/20 transition-colors flex items-center gap-2 disabled:opacity-50"
                      >
                        {executing ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Executing...
                          </>
                        ) : (
                          <>
                            <Trash2 className="w-4 h-4" />
                            Approve & Execute Cleanup
                          </>
                        )}
                      </button>
                    </div>
        </div>
      ) : (
              <div className="space-y-6 animate-in">
                <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-6">
                  <div className="flex items-center gap-4 mb-6">
                    <div className="w-16 h-16 rounded-full bg-devsweep-success/10 flex items-center justify-center">
                      {verifyResult?.passed ? (
                        <CheckCircle className="w-8 h-8 text-devsweep-success" />
                      ) : (
                        <XCircle className="w-8 h-8 text-devsweep-danger" />
                      )}
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold text-devsweep-success">Cleanup Complete</h2>
                      <p className="text-devsweep-textSecondary">Verification: {verifyResult?.passed ? 'PASSED' : 'FAILED'}</p>
                    </div>
                  </div>
            
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                    <div className="bg-devsweep-bg p-4 rounded-lg border border-devsweep-border text-center">
                      <p className="text-3xl font-bold font-mono text-devsweep-success">{execResult?.bytes_freed_human}</p>
                      <p className="text-xs text-devsweep-textMuted">Storage Recovered</p>
                    </div>
                    <div className="bg-devsweep-bg p-4 rounded-lg border border-devsweep-border text-center">
                      <p className="text-3xl font-bold font-mono text-devsweep-accent">{execResult?.items_deleted}</p>
                      <p className="text-xs text-devsweep-textMuted">Items Removed</p>
                    </div>
                    <div className="bg-devsweep-bg p-4 rounded-lg border border-devsweep-border text-center">
                      <p className="text-3xl font-bold font-mono text-devsweep-success">{verifyResult?.passed ? 'PASSED' : 'FAILED'}</p>
                      <p className="text-xs text-devsweep-textMuted">Project Verified</p>
                    </div>
                  </div>

                  {verifyResult && (
                    <div className="p-4 bg-devsweep-success/10 border border-devsweep-success/20 rounded-lg">
                      <h4 className="font-medium text-devsweep-success flex items-center gap-2 mb-2">
                        <ShieldCheck className="w-4 h-4" />
                        Protected Files: {verifyResult.passed ? 'INTACT' : 'ISSUES DETECTED'}
                      </h4>
                      <ul className="list-disc list-inside text-sm text-devsweep-textSecondary space-y-1">
                        {verifyResult.checks.map((check, i) => (
                          <li key={i} className={check.passed ? 'text-devsweep-success' : 'text-devsweep-danger'}>
                            {check.name}: {check.message}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <button onClick={() => { setExecuted(false); setExecResult(null); setVerifyResult(null); setPlan(null); }} className="w-full px-6 py-2 bg-devsweep-accent text-devsweep-bg rounded-lg font-medium hover:bg-devsweep-accentHover transition-colors">
                    Run Another Cleanup
                  </button>
                </div>
              </div>
            )}

      {error && (
        <div className="p-4 bg-devsweep-danger/10 border border-devsweep-danger/20 rounded-lg flex items-center gap-3 text-devsweep-danger animate-in">
          <XCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}