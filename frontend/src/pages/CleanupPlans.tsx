import { useEffect, useRef, useState } from 'react'
import { AlertCircle, Bot, CheckCircle, FileText, ShieldCheck, Trash2, XCircle } from 'lucide-react'
import { useDevSweep } from '../context/DevSweepContext'
import { useViewMode } from '../context/ViewModeContext'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { LoadingState } from '../components/ui/LoadingState'
import { RiskBadge } from '../components/ui/RiskBadge'
import { cn, formatBytes } from '../utils/helpers'

type Risk = 'SAFE' | 'CAUTION' | 'DANGEROUS'
type PlanItem = {
  path: string
  action: 'DELETE' | 'KEEP'
  risk: Risk
  scanner_risk?: Risk
  ai_risk?: Risk
  effective_risk?: Risk
  reason: string
  estimated_bytes: number
  regeneration_command?: string
}
type CleanupPlan = {
  plan_id: string
  items: PlanItem[]
  total_safe_bytes: number
  total_caution_bytes: number
  total_dangerous_bytes: number
  requires_approval: boolean
  warnings: string[]
  verification_steps: string[]
}
type ExecutionResult = {
  success: boolean
  items_processed: number
  items_deleted: number
  items_failed: number
  bytes_freed: number
  bytes_freed_human: string
  errors: string[]
  duration_seconds: number
}
type VerifyResult = {
  passed: boolean
  checks: Array<{ name: string; passed: boolean; message: string }>
  errors: string[]
}

async function responseError(response: Response, fallback: string) {
  try {
    const body = await response.json()
    return body.detail || fallback
  } catch {
    return fallback
  }
}

export function CleanupPlans() {
  const { currentProject, currentPlan: contextPlan, setCurrentPlan, addCleanupToHistory, aiProvider, aiModel, realInferenceAvailable } = useDevSweep()
  const { viewMode } = useViewMode()
  const [plan, setPlan] = useState<CleanupPlan | null>(contextPlan)
  const [loading, setLoading] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [execution, setExecution] = useState<ExecutionResult | null>(null)
  const [verification, setVerification] = useState<VerifyResult | null>(null)
  const [verificationError, setVerificationError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [approved, setApproved] = useState(false)
  const executionLock = useRef(false)

  useEffect(() => {
    if (contextPlan && contextPlan.plan_id !== plan?.plan_id) {
      setPlan(contextPlan)
      setExecution(null)
      setVerification(null)
      setVerificationError(null)
      setApproved(false)
      setError(null)
    }
  }, [contextPlan, plan?.plan_id])

  const generatePlan = async () => {
    if (!currentProject || !realInferenceAvailable || loading) return
    setLoading(true)
    setError(null)
    setApproved(false)
    try {
      const response = await fetch('/api/cleanup/generate-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_path: currentProject.project_path }),
      })
      if (!response.ok) throw new Error(await responseError(response, 'Failed to generate plan'))
      const data: CleanupPlan = await response.json()
      setPlan(data)
      setCurrentPlan(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate plan')
    } finally {
      setLoading(false)
    }
  }

  const cancelReview = () => {
    setPlan(null)
    setCurrentPlan(null)
    setApproved(false)
    setError(null)
  }

  const verifyProject = async (planId: string) => {
    if (!currentProject) throw new Error('No project is selected for verification')
    const response = await fetch('/api/cleanup/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_path: currentProject.project_path, project_type: currentProject.project_type, plan_id: planId }),
    })
    if (!response.ok) throw new Error(await responseError(response, 'Project verification failed'))
    const result: unknown = await response.json()
    if (!isVerifyResult(result)) throw new Error('Verification returned an unusable response')
    return result
  }

  const executePlan = async () => {
    if (!plan || !approved || executing || executionLock.current || hasDangerousDelete) return
    executionLock.current = true
    setExecuting(true)
    setError(null)
    setVerificationError(null)
    try {
      const response = await fetch('/api/cleanup/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_id: plan.plan_id, approved }),
      })
      if (!response.ok) throw new Error(await responseError(response, 'Execution failed'))
      const data: ExecutionResult = await response.json()
      setExecution(data)
      if (data.items_deleted > 0 || data.items_failed > 0) {
        addCleanupToHistory({
          plan_id: plan.plan_id,
          items_deleted: data.items_deleted,
          items_failed: data.items_failed,
          bytes_freed: data.bytes_freed,
          bytes_freed_human: data.bytes_freed_human,
          success: data.success && data.items_failed === 0 && data.items_deleted === data.items_processed,
          timestamp: new Date().toISOString(),
        })
      }
      try {
        setVerification(await verifyProject(plan.plan_id))
      } catch (verifyError) {
        setVerificationError(verifyError instanceof Error ? verifyError.message : 'Project verification failed')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Execution failed')
    } finally {
      executionLock.current = false
      setExecuting(false)
    }
  }

  const hasDangerousDelete = Boolean(plan?.items.some(item => item.action === 'DELETE' && (item.effective_risk || item.risk) === 'DANGEROUS'))
  const cautionCount = plan?.items.filter(item => item.action === 'DELETE' && (item.effective_risk || item.risk) === 'CAUTION').length || 0
  const executionSucceeded = Boolean(execution && execution.success && execution.items_failed === 0 && execution.items_deleted === execution.items_processed)
  const executionPartial = Boolean(execution && execution.items_deleted > 0 && !executionSucceeded)

  const renderPlanItem = (item: PlanItem, index: number) => {
    const effectiveRisk = item.effective_risk || item.risk
    const displayPath = viewMode === 'technical' && currentProject && !item.path.startsWith(currentProject.project_path)
      ? `${currentProject.project_path.replace(/[\\/]+$/, '')}/${item.path.replace(/^[\\/]+/, '')}`
      : item.path
    const riskExplanation = effectiveRisk === 'SAFE'
      ? 'Usually safe to remove and can be recreated if needed.'
      : effectiveRisk === 'CAUTION'
        ? 'Review the possible impact before allowing this item to be removed.'
        : 'This item is dangerous and cannot be removed.'
    return (
      <div key={`${item.path}-${index}`} className="rounded-lg border border-devsweep-border bg-devsweep-bg p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="break-all font-medium">{displayPath}</p>
            <p className="mt-1 text-sm text-devsweep-textSecondary">{item.reason}</p>
            {viewMode === 'simple' && <p className="mt-1 text-xs text-devsweep-textMuted">{riskExplanation}</p>}
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded bg-devsweep-accent/10 px-2 py-0.5 text-xs font-medium text-devsweep-accent">{item.action}</span>
            <RiskBadge risk={effectiveRisk} variant={viewMode === 'technical' ? 'technical' : 'simple'} scannerRisk={item.scanner_risk} aiRisk={item.ai_risk} effectiveRisk={item.effective_risk} />
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm text-devsweep-textMuted">
          <span>{formatBytes(item.estimated_bytes)}</span>
          {viewMode === 'technical' && item.regeneration_command && <code className="rounded bg-devsweep-bgTertiary px-2 py-1">{item.regeneration_command}</code>}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-5xl space-y-6 animate-in">
      <header>
        <h1 className="text-2xl font-bold">Cleanup Plans</h1>
        <p className="mt-1 text-devsweep-textSecondary">Review the proposed changes, approve them, then inspect execution and verification results.</p>
      </header>

      {!currentProject ? (
        <Card padding="none"><EmptyState icon={<FileText className="h-16 w-16 text-devsweep-textMuted opacity-50" />} title="No project selected" description="Scan a workspace first to generate a cleanup plan." /></Card>
      ) : !plan ? (
        <Card className="space-y-5 text-center">
          <Bot className="mx-auto h-12 w-12 text-devsweep-accent opacity-70" />
          <div>
            <h2 className="text-lg font-semibold">{realInferenceAvailable ? `Nebius configured (${aiModel})` : `Mock/demo provider (${aiProvider})`}</h2>
            <p className="mt-1 text-sm text-devsweep-textSecondary">{realInferenceAvailable ? 'Generate a cleanup plan using real Nebius inference.' : 'Mock analysis is for development and cannot authorize cleanup plans.'}</p>
          </div>
          <Button onClick={generatePlan} disabled={!realInferenceAvailable || loading} loading={loading} fullWidth>Generate Cleanup Plan with AI</Button>
        </Card>
      ) : !execution ? (
        <>
          <Card padding="none" className="overflow-hidden">
            <div className="border-b border-devsweep-border bg-devsweep-bgTertiary/50 p-5">
              <h2 className="font-semibold">Review plan for {currentProject.project_path.split(/[\\/]/).filter(Boolean).pop()}</h2>
              <p className="mt-1 text-sm text-devsweep-textSecondary">These are the exact items the backend plan may remove.</p>
              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <Summary label="Items" value={String(plan.items.filter(item => item.action === 'DELETE').length)} />
                <Summary label="Safe recovery" value={formatBytes(plan.total_safe_bytes)} />
                <Summary label="Caution recovery" value={formatBytes(plan.total_caution_bytes)} />
              </div>
            </div>
            <div className="space-y-3 p-5">{plan.items.map(renderPlanItem)}</div>
            {plan.warnings.length > 0 && <div className="mx-5 mb-5 rounded-lg border border-devsweep-warning/20 bg-devsweep-warning/10 p-4 text-sm text-devsweep-warning"><h3 className="mb-2 flex items-center gap-2 font-medium"><AlertCircle className="h-4 w-4" />Plan warnings</h3><ul className="list-disc space-y-1 pl-5">{plan.warnings.map((warning, i) => <li key={i}>{warning}</li>)}</ul></div>}
            <div className="border-t border-devsweep-border bg-devsweep-bgTertiary/30 p-5">
              <h3 className="flex items-center gap-2 font-medium"><ShieldCheck className="h-4 w-4 text-devsweep-accent" />Application safety checks remain active</h3>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-devsweep-textSecondary">{plan.verification_steps.map((step, i) => <li key={i}>{step}</li>)}</ul>
              {cautionCount > 0 && <p className="mt-3 text-sm text-devsweep-warning">{cautionCount} caution item(s) require your explicit approval.</p>}
              {hasDangerousDelete && <p role="alert" className="mt-3 text-sm text-devsweep-danger">This plan includes a dangerous deletion. Execution is blocked.</p>}
              <label className="mt-4 flex cursor-pointer items-start gap-3 text-sm">
                <input type="checkbox" className="mt-0.5 h-4 w-4 accent-devsweep-accent" checked={approved} onChange={event => setApproved(event.target.checked)} disabled={hasDangerousDelete} />
                <span>I reviewed the listed items and approve execution{cautionCount > 0 ? ', including the caution items' : ''}.</span>
              </label>
              <div className="mt-4 flex flex-wrap justify-end gap-3">
                <Button variant="secondary" onClick={cancelReview} disabled={loading || executing}>Cancel and return</Button>
                <Button variant="danger" onClick={executePlan} disabled={!approved || executing || hasDangerousDelete} loading={executing} icon={<Trash2 />}>
                  {executing ? 'Executing cleanup…' : 'Approve & Execute Cleanup'}
                </Button>
              </div>
              {executing && <div className="mt-4" role="status"><LoadingState variant="inline" text="Cleanup is running. This operation cannot be cancelled from the application." /></div>}
            </div>
          </Card>
        </>
      ) : (
        <div className="space-y-5" aria-live="polite">
          <Card>
            <div className="flex items-start gap-3">
              {executionSucceeded ? <CheckCircle className="mt-0.5 h-6 w-6 text-devsweep-success" /> : executionPartial ? <AlertCircle className="mt-0.5 h-6 w-6 text-devsweep-warning" /> : <XCircle className="mt-0.5 h-6 w-6 text-devsweep-danger" />}
              <div className="min-w-0 flex-1">
                <h2 className="text-lg font-semibold">{executionSucceeded ? 'Execution complete' : executionPartial ? 'Execution partially completed' : 'Execution failed'}</h2>
                <p className="mt-1 text-sm text-devsweep-textSecondary">{execution.items_deleted} of {execution.items_processed} item(s) deleted; {execution.items_failed} failed. Storage reported freed: {execution.bytes_freed_human}.</p>
                {execution.errors.length > 0 && <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-devsweep-danger">{execution.errors.map((itemError, i) => <li key={i}>{itemError}</li>)}</ul>}
              </div>
            </div>
            <p className="mt-3 text-xs text-devsweep-textMuted">Execution duration: {execution.duration_seconds.toFixed(2)} seconds</p>
          </Card>
          <Card>
            <div className="flex items-start gap-3">
              {verificationError ? <AlertCircle className="mt-0.5 h-6 w-6 text-devsweep-warning" /> : verification?.passed ? <CheckCircle className="mt-0.5 h-6 w-6 text-devsweep-success" /> : <XCircle className="mt-0.5 h-6 w-6 text-devsweep-danger" />}
              <div>
                <h2 className="font-semibold">{verificationError ? 'Verification unavailable' : verification?.passed ? 'Verification passed' : 'Verification found issues'}</h2>
                <p className="mt-1 text-sm text-devsweep-textSecondary">{verificationError || (verification?.passed ? 'The backend verification checks passed.' : 'One or more backend verification checks reported issues.')}</p>
              </div>
            </div>
            {verification?.checks && <ul className="mt-4 space-y-2">{verification.checks.map((check, i) => <li key={`${check.name}-${i}`} className={cn('text-sm', check.passed ? 'text-devsweep-success' : 'text-devsweep-danger')}><span className="font-medium">{check.name}:</span> {check.message}</li>)}</ul>}
            {verification?.errors && verification.errors.length > 0 && <ul className="mt-3 list-disc pl-5 text-sm text-devsweep-danger">{verification.errors.map((verifyError, i) => <li key={i}>{verifyError}</li>)}</ul>}
          </Card>
          <Button variant="secondary" onClick={cancelReview}>Return to plans</Button>
        </div>
      )}
      {error && <ErrorAlert title="Cleanup request failed" message={error} />}
    </div>
  )
}

function Summary({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-devsweep-border bg-devsweep-bg p-3"><p className="text-xs text-devsweep-textMuted">{label}</p><p className="mt-1 font-mono font-semibold">{value}</p></div>
}

function isVerifyResult(value: unknown): value is VerifyResult {
  if (!value || typeof value !== 'object') return false
  const result = value as Partial<VerifyResult>
  return typeof result.passed === 'boolean'
    && Array.isArray(result.checks)
    && result.checks.every(check => check && typeof check.name === 'string' && typeof check.passed === 'boolean' && typeof check.message === 'string')
    && Array.isArray(result.errors)
    && result.errors.every(error => typeof error === 'string')
}
