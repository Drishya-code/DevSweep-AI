import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, History, RotateCcw } from 'lucide-react'
import { useDevSweep } from '../context/DevSweepContext'
import { useViewMode } from '../context/ViewModeContext'
import { Button } from '../components/ui/Button'
import { Card, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { LoadingState } from '../components/ui/LoadingState'
import { apiErrorMessage, requestJson } from '../utils/api'
import { formatBytes } from '../utils/helpers'

type Backup = {
  backup_id: string; execution_id: string; project_id: string; path: string
  size_bytes: number; sha256: string; entry_count: number; created_at: string; status: string
}
type BackupEntry = { path: string; type: 'file' | 'directory'; size: number; sha256?: string }
type BackupDetails = {
  backup_id: string; path: string; size_bytes: number; sha256: string; entry_count: number
  offset: number; limit: number; entries: BackupEntry[]; has_more: boolean
}
type RestoreRecord = {
  restore_id: string; backup_id: string; project_id: string; status: string
  started_at: string; finished_at: string | null; summary: string
}

export function RestoreCenter() {
  const { currentProject } = useDevSweep()
  const { viewMode } = useViewMode()
  const navigate = useNavigate()
  const [backups, setBackups] = useState<Backup[]>([])
  const [restores, setRestores] = useState<RestoreRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [restoring, setRestoring] = useState<string | null>(null)
  const [inspecting, setInspecting] = useState<string | null>(null)
  const [details, setDetails] = useState<BackupDetails | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [backupData, historyData] = await Promise.all([
        requestJson<{ backups: Backup[] }>('/api/cleanup/backups'),
        requestJson<{ restores: RestoreRecord[] }>('/api/cleanup/restore/history'),
      ])
      setBackups(backupData.backups)
      setRestores(historyData.restores)
    } catch (err) {
      setError(apiErrorMessage(err, viewMode))
    } finally {
      setLoading(false)
    }
  }, [viewMode])

  useEffect(() => { void load() }, [load])

  const restore = async (backup: Backup) => {
    if (!currentProject || currentProject.project_id !== backup.project_id || restoring || details?.backup_id !== backup.backup_id) return
    const confirmed = window.confirm(`Restore “${backup.path}” (${details.entry_count} entries, ${formatBytes(backup.size_bytes)}) from its verified backup? Existing files will never be overwritten.`)
    if (!confirmed) return
    setRestoring(backup.backup_id)
    setError(null)
    setNotice(null)
    try {
      const result = await requestJson<{ status: string; summary: string }>('/api/cleanup/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ backup_id: backup.backup_id, project_path: currentProject.project_path, access_grant_id: currentProject.access_grant_id, approved: true }),
      })
      setNotice(result.summary)
      await load()
    } catch (err) {
      setError(apiErrorMessage(err, viewMode))
      await load()
    } finally {
      setRestoring(null)
    }
  }

  const inspect = async (backupId: string, offset = 0) => {
    setInspecting(backupId)
    setError(null)
    try {
      const page = await requestJson<BackupDetails>(`/api/cleanup/backups/${encodeURIComponent(backupId)}?offset=${offset}&limit=100`)
      setDetails(previous => offset > 0 && previous?.backup_id === backupId
        ? { ...page, entries: [...previous.entries, ...page.entries] }
        : page)
    } catch (err) {
      setDetails(null)
      setError(apiErrorMessage(err, viewMode))
    } finally {
      setInspecting(null)
    }
  }

  const visibleBackups = currentProject?.project_id
    ? backups.filter(backup => backup.project_id === currentProject.project_id)
    : backups

  return (
    <div className="space-y-6 animate-in max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold">Restore Center</h1>
        <p className="mt-1 text-devsweep-textSecondary">Restore verified contents saved before cleanup. Files are never overwritten, and backups are not automatically removed.</p>
      </div>
      {error && <ErrorAlert title="Recovery data unavailable" message={error} action={{ label: 'Retry', onClick: () => void load() }} />}
      {notice && <div role="status" className="rounded-lg border border-devsweep-success/30 bg-devsweep-success/10 p-4 text-sm text-devsweep-success">{notice}</div>}
      {currentProject ? (
        <Card>
          <CardHeader><CardTitle as="h2">Selected project</CardTitle><CardDescription className="break-all font-mono">{currentProject.project_path}</CardDescription></CardHeader>
        </Card>
      ) : (
        <div className="rounded-lg border border-devsweep-warning/30 bg-devsweep-warning/10 p-4 text-sm text-devsweep-textSecondary"><AlertTriangle className="mr-2 inline h-4 w-4 text-devsweep-warning" />Select and refresh a project before restoring. Backups remain listed for review.</div>
      )}
      {loading ? <Card role="status"><LoadingState text="Loading verified backups…" /></Card> : error ? null : visibleBackups.length === 0 ? (
        <Card><EmptyState icon={<RotateCcw className="h-12 w-12 text-devsweep-textMuted" />} title="No verified backups available" description="A backup appears here only after its cleanup item was recorded deleted and its saved content passed integrity checks." /></Card>
      ) : (
        <section aria-labelledby="backup-heading" className="space-y-3">
          <h2 id="backup-heading" className="text-lg font-semibold">Verified backups</h2>
          {visibleBackups.map(backup => {
            const canRestore = Boolean(currentProject && currentProject.project_id === backup.project_id)
            return <Card key={backup.backup_id}>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="break-all font-mono text-sm">{backup.path}</p>
                  <p className="mt-1 text-sm text-devsweep-textSecondary">{formatBytes(backup.size_bytes)} · saved {new Date(backup.created_at).toLocaleString()}</p>
                  <p className="mt-1 text-xs text-devsweep-textMuted">Cleanup execution {backup.execution_id}</p>
                  {viewMode === 'technical' && <p className="mt-1 break-all font-mono text-xs text-devsweep-textMuted">Backup {backup.backup_id} · SHA-256 {backup.sha256}</p>}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button variant="secondary" onClick={() => void inspect(backup.backup_id)} disabled={Boolean(inspecting) || Boolean(restoring)} loading={inspecting === backup.backup_id}>Review contents</Button>
                  <Button onClick={() => canRestore ? void restore(backup) : navigate('/projects')} disabled={Boolean(restoring) || details?.backup_id !== backup.backup_id} loading={restoring === backup.backup_id} aria-label={canRestore ? `Restore ${backup.path}` : 'Select matching project'}>
                    {canRestore ? 'Restore' : 'Select project'}
                  </Button>
                </div>
              </div>
              {details?.backup_id === backup.backup_id && <div className="mt-4 border-t border-devsweep-border pt-3">
                <p className="mb-2 text-sm font-medium">Backup contents ({details.entry_count} entries; the full backup passed SHA-256 verification)</p>
                <ul className="max-h-64 space-y-1 overflow-auto rounded-lg bg-devsweep-bgTertiary/40 p-3 text-xs">
                  {details.entries.map((entry, index) => <li key={`${entry.path}-${index}`} className="flex flex-wrap justify-between gap-x-4 gap-y-1"><span className="break-all font-mono">{entry.path === '.' ? '(item root)' : entry.path}{entry.type === 'directory' ? '/' : ''}</span><span className="shrink-0 text-devsweep-textMuted">{entry.type}{entry.type === 'file' ? ` · ${formatBytes(entry.size)}` : ''}{viewMode === 'technical' && entry.sha256 ? ` · SHA-256 ${entry.sha256}` : ''}</span></li>)}
                </ul>
                {details.has_more && <Button className="mt-2" variant="ghost" size="sm" onClick={() => void inspect(backup.backup_id, details.entries.length)} loading={inspecting === backup.backup_id}>Show more contents</Button>}
              </div>}
            </Card>
          })}
        </section>
      )}
      <section aria-labelledby="restore-history-heading" className="space-y-3">
        <h2 id="restore-history-heading" className="flex items-center gap-2 text-lg font-semibold"><History className="h-5 w-5" />Restore history</h2>
        {!loading && !error && restores.length === 0 ? <Card><EmptyState title="No restore attempts recorded" description="Approved restore requests and their outcomes will appear here." /></Card> : restores.map(record => (
          <Card key={record.restore_id} padding="sm">
            <div className="flex flex-wrap items-center justify-between gap-2"><span className="font-medium capitalize">{record.status}</span><time className="text-xs text-devsweep-textMuted">{new Date(record.started_at).toLocaleString()}</time></div>
            <p className="mt-1 text-sm text-devsweep-textSecondary">{record.summary}</p>
            {viewMode === 'technical' && <p className="mt-1 break-all font-mono text-xs text-devsweep-textMuted">Restore {record.restore_id} · Backup {record.backup_id}</p>}
          </Card>
        ))}
      </section>
    </div>
  )
}
