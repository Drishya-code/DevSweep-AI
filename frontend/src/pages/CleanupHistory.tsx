import { useEffect, useState } from 'react'
import { AlertTriangle, History } from 'lucide-react'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { LoadingState } from '../components/ui/LoadingState'
import { useViewMode } from '../context/ViewModeContext'
import { apiErrorMessage, requestJson } from '../utils/api'
import { formatBytes } from '../utils/helpers'

type Verification = { status: string; verified_at: string; summary: string }
type ItemOutcome = { item_id: string; path: string; action: string; risk: string; outcome: string; error_summary: string; bytes_processed: number; verification_status: string }
type Execution = {
  execution_id: string; plan_id: string; project_id: string; started_at: string; ended_at: string | null
  status: 'completed' | 'partial' | 'failed' | 'interrupted' | 'unknown' | string
  approved_candidates: number; items_processed: number; items_deleted: number; items_skipped: number
  items_failed: number; items_unknown: number; bytes_processed: number; error_summary: string
  outcomes: ItemOutcome[]; verifications: Verification[]
}

function statusText(status: string) {
  if (status === 'completed') return 'Complete'
  if (status === 'partial') return 'Partial success'
  if (status === 'failed') return 'Failed'
  if (status === 'interrupted') return 'Interrupted'
  return 'Outcome unknown'
}

export function CleanupHistory() {
  const { viewMode } = useViewMode()
  const [executions, setExecutions] = useState<Execution[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await requestJson<{ executions: Execution[] }>('/api/cleanup/history/executions')
      setExecutions(data.executions)
    } catch (err) {
      setError(apiErrorMessage(err, viewMode))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  return (
    <div className="space-y-6 animate-in">
      <div>
        <h1 className="text-2xl font-bold">Cleanup History</h1>
        <p className="mt-1 text-devsweep-textSecondary">Persistent execution records from this backend. Verification records describe checks performed; they are not file backups.</p>
      </div>
      {error && <ErrorAlert title="Cleanup history unavailable" message={error} action={{ label: 'Retry', onClick: () => void load() }} />}
      {loading ? <Card role="status"><LoadingState text="Loading cleanup history…" /></Card> : error ? null : executions.length === 0 ? (
        <Card><EmptyState icon={<History className="h-12 w-12 text-devsweep-textMuted" />} title="No cleanup executions recorded" description="Completed or interrupted cleanup attempts will appear here." /></Card>
      ) : <div className="space-y-4">{executions.map(item => (
        <Card key={item.execution_id}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0"><h2 className="font-semibold">{statusText(item.status)}</h2><p className="mt-1 text-xs text-devsweep-textMuted">{new Date(item.started_at).toLocaleString()}</p><p className="mt-1 break-all font-mono text-xs text-devsweep-textMuted">Execution {item.execution_id} · Plan {item.plan_id}</p></div>
            {item.status === 'interrupted' || item.status === 'unknown' ? <AlertTriangle className="h-5 w-5 text-devsweep-warning" aria-label="Outcome needs review" /> : null}
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-3 lg:grid-cols-6">
            <Count label="Approved" value={item.approved_candidates} />
            <Count label="Processed" value={item.items_processed} />
            <Count label="Deleted" value={item.items_deleted} />
            <Count label="Failed" value={item.items_failed} />
            <Count label="Unknown" value={item.items_unknown} />
            <Count label="Bytes deleted" value={formatBytes(item.bytes_processed)} />
          </div>
          {item.error_summary && <p className="mt-3 text-sm text-devsweep-warning">{item.error_summary}</p>}
          {item.outcomes.length > 0 && <div className="mt-4 space-y-2"><h3 className="text-sm font-medium">Item outcomes</h3>{item.outcomes.map(outcome => <div key={outcome.item_id} className="flex flex-col gap-1 rounded-lg border border-devsweep-border p-3 text-sm sm:flex-row sm:items-center sm:justify-between"><div className="min-w-0"><p className="break-all font-mono">{outcome.path}</p><p className="text-xs text-devsweep-textMuted">{outcome.action} · {outcome.risk}{viewMode === 'technical' && ` · ${outcome.item_id}`}</p></div><span className="shrink-0">{outcome.outcome === 'completed' ? 'Deleted' : outcome.outcome === 'unknown' || outcome.outcome === 'in_progress' ? 'Outcome unknown' : 'Failed'} · verification {outcome.verification_status}</span>{outcome.error_summary && <p className="text-xs text-devsweep-warning">{outcome.error_summary}</p>}</div>)}</div>}
          {item.verifications.map((verification, index) => <div key={`${verification.verified_at}-${index}`} className="mt-3 rounded-lg border border-devsweep-border p-3 text-sm"><p>Verification: {verification.status === 'passed' ? 'Passed' : 'Completed with issues'} · {new Date(verification.verified_at).toLocaleString()}</p><p className="mt-1 text-xs text-devsweep-textMuted">{verification.summary}</p>{viewMode === 'technical' && <pre className="mt-2 overflow-auto text-xs">{JSON.stringify(verification, null, 2)}</pre>}</div>)}
          {item.status === 'interrupted' && <p className="mt-3 text-sm text-devsweep-warning">The backend restarted during this operation. Some file outcomes may be unknown; the operation was not resumed.</p>}
        </Card>
      ))}</div>}
    </div>
  )
}

function Count({ label, value }: { label: string; value: number | string }) {
  return <div className="rounded-lg border border-devsweep-border p-3"><p className="text-xs text-devsweep-textMuted">{label}</p><p className="mt-1 font-mono font-semibold">{value}</p></div>
}
