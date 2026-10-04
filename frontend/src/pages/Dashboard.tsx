import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle, CheckCircle, Database, FolderGit2, HardDrive, Search, ShieldAlert, Sparkles } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useDevSweep } from '../context/DevSweepContext'
import { useViewMode } from '../context/ViewModeContext'
import { Button } from '../components/ui/Button'
import { Card, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { LoadingState } from '../components/ui/LoadingState'
import { RiskBadge } from '../components/ui/RiskBadge'
import { cn, formatBytes } from '../utils/helpers'
import { apiErrorMessage, requestJson } from '../utils/api'
import type { ScanResponse } from '../types/api'

type Risk = 'SAFE' | 'CAUTION' | 'DANGEROUS'

export function Dashboard() {
  const { currentProject, setCurrentProject, scanHistory, addScanToHistory, isScanning, setIsScanning, demoMode } = useDevSweep()
  const { viewMode } = useViewMode()
  const [error, setError] = useState<string | null>(null)
  const [failedScanRequest, setFailedScanRequest] = useState<{ endpoint: string; body?: object } | null>(null)
  const [historySummary, setHistorySummary] = useState<{ projects: number; scans: number; plans: number; executions: number } | null>(null)
  const [historyLoading, setHistoryLoading] = useState(true)
  const [historyError, setHistoryError] = useState<string | null>(null)

  const loadHistorySummary = async () => {
    setHistoryLoading(true)
    setHistoryError(null)
    try {
      setHistorySummary(await requestJson<{ projects: number; scans: number; plans: number; executions: number }>('/api/cleanup/history/summary'))
    } catch (summaryError) {
      setHistoryError(apiErrorMessage(summaryError, viewMode))
    } finally {
      setHistoryLoading(false)
    }
  }

  useEffect(() => { void loadHistorySummary() }, [])

  const latestScans = useMemo(() => {
    const byPath = new Map<string, ScanResponse>()
    scanHistory.forEach(scan => { if (!byPath.has(scan.project_path)) byPath.set(scan.project_path, scan) })
    if (currentProject && !byPath.has(currentProject.project_path)) byPath.set(currentProject.project_path, currentProject)
    return [...byPath.values()]
  }, [scanHistory, currentProject])

  const totals = useMemo(() => latestScans.reduce((result, scan) => {
    result.recoverableBytes += scan.total_recoverable_bytes
    result.candidates += scan.cleanup_candidates.length
    return result
  }, { recoverableBytes: 0, candidates: 0 }), [latestScans])

  const candidateBreakdown = useMemo(() => {
    const summary: Record<Risk, { count: number; bytes: number }> = {
      SAFE: { count: 0, bytes: 0 }, CAUTION: { count: 0, bytes: 0 }, DANGEROUS: { count: 0, bytes: 0 },
    }
    currentProject?.cleanup_candidates.forEach(candidate => {
      const risk = candidate.risk as Risk
      if (risk in summary) {
        summary[risk].count += 1
        summary[risk].bytes += candidate.size_bytes
      }
    })
    return summary
  }, [currentProject])

  const runScan = async (endpoint: string, body?: object) => {
    if (isScanning) return
    setIsScanning(true)
    setError(null)
    setFailedScanRequest(null)
    try {
      const result = await requestJson<ScanResponse>(endpoint, body ? {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      } : undefined)
      setCurrentProject(result)
      addScanToHistory(result)
    } catch (scanError) {
      setFailedScanRequest({ endpoint, body })
      setError(apiErrorMessage(scanError, viewMode))
    } finally {
      setIsScanning(false)
    }
  }

  const healthMessage = !currentProject
    ? 'Scan a project to see its current status.'
    : !currentProject.has_git
      ? 'Git metadata was not detected in this project.'
      : currentProject.git_clean
        ? 'The working tree was clean at the time of this scan.'
        : 'The working tree had uncommitted changes at the time of this scan.'
  const dangerousCount = currentProject?.cleanup_candidates.filter(item => item.risk === 'DANGEROUS').length || 0

  return (
    <div className="space-y-6 animate-in">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="mt-1 text-devsweep-textSecondary">A current view of scanned workspaces and detected cleanup opportunities.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          {demoMode && <Button variant="secondary" onClick={() => runScan('/api/scan/demo')} disabled={isScanning} icon={<Sparkles className="h-4 w-4" />}>Scan Demo Project</Button>}
          <Button onClick={() => runScan('/api/scan', {})} disabled={isScanning} loading={isScanning} icon={<Search className="h-4 w-4" />}>Scan Workspace</Button>
        </div>
      </header>

      {error && <ErrorAlert title="Scan failed" message={error} dismissible onDismiss={() => setError(null)} action={{ label: 'Retry scan', onClick: () => failedScanRequest && runScan(failedScanRequest.endpoint, failedScanRequest.body) }} />}
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-3"><div><CardTitle as="h2">Persistent activity</CardTitle><CardDescription>Records stored by this backend across restarts. Candidate sizes are not total disk usage; verification records are not backups.</CardDescription></div><Button size="sm" variant="secondary" onClick={() => void loadHistorySummary()}>Refresh</Button></div>
        {historyError ? <ErrorAlert title="Persistent activity unavailable" message={historyError} action={{ label: 'Retry', onClick: () => void loadHistorySummary() }} /> : historyLoading ? <LoadingState variant="inline" text="Loading saved history…" /> : historySummary && <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">{Object.entries({ Projects: historySummary.projects, Scans: historySummary.scans, 'Cleanup plans': historySummary.plans, Executions: historySummary.executions }).map(([label, value]) => <div key={label} className="rounded-lg border border-devsweep-border p-3"><p className="text-xs text-devsweep-textMuted">{label}</p><p className="font-mono text-lg font-semibold">{value}</p></div>)}</div>}
      </Card>
      {isScanning && <Card role="status" padding="sm"><LoadingState variant="inline" text="Scanning workspace…" /></Card>}

      <section aria-label="Workspace statistics" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Projects scanned this session" value={String(latestScans.length)} icon={FolderGit2} />
        <Stat label="Cleanup candidates in selected scan" value={String(currentProject?.cleanup_candidates.length ?? '—')} icon={Database} />
        <Stat label="Recoverable in selected scan" value={currentProject?.total_recoverable_human ?? '—'} icon={HardDrive} />
        <Stat label="Recoverable across latest session scans" value={latestScans.length ? formatBytes(totals.recoverableBytes) : '—'} icon={Sparkles} />
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2" padding="none">
          <CardHeader className="p-5 pb-0">
            <CardTitle as="h2">Cleanup opportunities</CardTitle>
            <CardDescription>{currentProject ? `Candidate data from the scan of ${currentProject.project_path}` : 'Scan a project to see measured candidate sizes and risks.'}</CardDescription>
          </CardHeader>
          {!currentProject ? (
            <EmptyState illustration="scan" title="No scan selected" description="Workspace storage totals are not available. Scan a workspace to view actual cleanup candidates." />
          ) : currentProject.cleanup_candidates.length === 0 ? (
            <EmptyState illustration="cleanup" title="No cleanup candidates found" description="The latest scan found no cleanup candidates in this project." />
          ) : (
            <div className="grid grid-cols-1 gap-3 p-5 sm:grid-cols-3">
              {(['SAFE', 'CAUTION', 'DANGEROUS'] as Risk[]).map(risk => (
                <div key={risk} className="rounded-lg border border-devsweep-border bg-devsweep-bg p-4">
                  <RiskBadge risk={risk} />
                  <p className="mt-3 text-2xl font-bold font-mono">{formatBytes(candidateBreakdown[risk].bytes)}</p>
                  <p className="text-sm text-devsweep-textSecondary">{candidateBreakdown[risk].count} {risk.toLowerCase()} candidate{candidateBreakdown[risk].count === 1 ? '' : 's'}</p>
                  {viewMode === 'simple' && <p className="mt-2 text-xs text-devsweep-textMuted">{risk === 'SAFE' ? 'Typically regenerable files.' : risk === 'CAUTION' ? 'Review impact before approval.' : 'Blocked from cleanup.'}</p>}
                </div>
              ))}
            </div>
          )}
          {currentProject && viewMode === 'technical' && currentProject.cleanup_candidates.length > 0 && (
            <div className="border-t border-devsweep-border p-5">
              <h3 className="mb-3 font-medium">Scanned candidate details</h3>
              <div className="space-y-2">
                {currentProject.cleanup_candidates.map((candidate, index) => (
                  <div key={`${candidate.path}-${index}`} className="flex flex-col gap-2 rounded-lg border border-devsweep-border bg-devsweep-bg p-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0"><p className="break-all font-mono text-sm">{candidate.path}</p><p className="mt-1 text-sm text-devsweep-textSecondary">{candidate.reason}</p></div>
                    <div className="flex shrink-0 items-center gap-3"><RiskBadge risk={candidate.risk} /><span className="font-mono text-sm">{formatBytes(candidate.size_bytes)}</span></div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {currentProject && <p className="border-t border-devsweep-border px-5 py-3 text-xs text-devsweep-textMuted">Candidate sizes are measured by the scanner; this is not total project disk usage.</p>}
        </Card>

        <Card>
          <CardHeader>
            <CardTitle as="h2">Selected project status</CardTitle>
            <CardDescription>{currentProject ? `${projectName(currentProject.project_path)} · facts reported by the latest scan.` : 'Facts reported by the latest scan; no synthetic health score.'}</CardDescription>
          </CardHeader>
          {currentProject ? (
            <div className="space-y-4">
              <div className={cn('rounded-lg border p-4', !currentProject.has_git ? 'border-devsweep-border bg-devsweep-bgTertiary/50' : currentProject.git_clean ? 'border-devsweep-success/20 bg-devsweep-success/10' : 'border-devsweep-warning/20 bg-devsweep-warning/10')}>
                <div className="flex items-start gap-3">{!currentProject.has_git ? <AlertCircle className="h-5 w-5 text-devsweep-textMuted" /> : currentProject.git_clean ? <CheckCircle className="h-5 w-5 text-devsweep-success" /> : <AlertCircle className="h-5 w-5 text-devsweep-warning" />}<p className="text-sm">{healthMessage}</p></div>
              </div>
              {dangerousCount > 0 && <div className="flex items-start gap-2 text-sm text-devsweep-danger"><ShieldAlert className="h-4 w-4 shrink-0" />{dangerousCount} dangerous candidate{dangerousCount === 1 ? '' : 's'} detected; backend cleanup safety blocks deletion.</div>}
              <div className="space-y-2 text-sm">
                <Detail label="Project type" value={currentProject.project_type} />
                {viewMode === 'technical' && <>
                  <Detail label="Framework" value={currentProject.framework} />
                  <Detail label="Language" value={currentProject.language} />
                  <Detail label="Package manager" value={currentProject.package_manager} />
                  <Detail label="Git detected" value={currentProject.has_git ? 'Yes' : 'No'} />
                  {currentProject.has_git && <Detail label="Git working tree" value={currentProject.git_clean ? 'Clean' : 'Uncommitted changes'} />}
                  <Detail label="Candidates across session scans" value={String(totals.candidates)} />
                </>}
              </div>
              <p className="break-all text-xs text-devsweep-textMuted">{currentProject.project_path}</p>
              {currentProject.notes && <p className="text-sm text-devsweep-textSecondary">{currentProject.notes}</p>}
            </div>
          ) : <EmptyState illustration="project" title="No project selected" description="Project health details appear after a successful scan." />}
        </Card>
      </div>

      <Card>
        <CardTitle as="h2">Quick actions</CardTitle>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Link to="/scan" className="rounded-lg border border-devsweep-border p-4 transition-colors hover:border-devsweep-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-devsweep-accent"><span className="flex items-center gap-2 font-medium"><Search className="h-5 w-5 text-devsweep-accent" />Scan workspace</span><p className="mt-1 text-sm text-devsweep-textMuted">Choose a project path and inspect its cleanup candidates.</p></Link>
          <Link to="/projects" className="rounded-lg border border-devsweep-border p-4 transition-colors hover:border-devsweep-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-devsweep-accent"><span className="flex items-center gap-2 font-medium"><FolderGit2 className="h-5 w-5 text-devsweep-accent" />View scanned projects</span><p className="mt-1 text-sm text-devsweep-textMuted">Select or refresh a project scanned in this session.</p></Link>
        </div>
      </Card>
    </div>
  )
}

function Stat({ label, value, icon: Icon }: { label: string; value: string; icon: LucideIcon }) {
  return <Card padding="sm"><div className="flex items-center gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-lg bg-devsweep-accent/10"><Icon className="h-5 w-5 text-devsweep-accent" /></div><div className="min-w-0"><p className="text-xs text-devsweep-textMuted">{label}</p><p className="break-words font-mono text-lg font-bold">{value}</p></div></div></Card>
}

function Detail({ label, value }: { label: string; value: string }) {
  return <div className="flex justify-between gap-3"><span className="text-devsweep-textSecondary">{label}</span><span className="text-right font-mono">{value}</span></div>
}

function projectName(path: string) {
  return path.replace(/[\\/]+$/, '').split(/[\\/]/).pop() || path
}
