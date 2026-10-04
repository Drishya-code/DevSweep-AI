import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, CheckCircle, FolderGit2, RefreshCw } from 'lucide-react'
import { useDevSweep } from '../context/DevSweepContext'
import { useViewMode } from '../context/ViewModeContext'
import { Button } from '../components/ui/Button'
import { Card, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { DataTable, type Column } from '../components/ui/DataTable'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { LoadingState } from '../components/ui/LoadingState'
import { cn } from '../utils/helpers'
import { apiErrorMessage, requestJson } from '../utils/api'
import type { ScanResponse } from '../types/api'

type StoredProject = {
  project_id: string; project_path: string; name: string; project_type: string
  created_at: string; last_accessed_at: string; latest_scan: ScanResponse | null
  latest_scan_at: string | null; availability: 'available' | 'missing' | 'identity_changed' | 'requires_grant'
}

function projectName(path: string) {
  return path.replace(/[\\/]+$/, '').split(/[\\/]/).pop() || path
}

export function Projects() {
  const { scanHistory, currentProject, setCurrentProject, addScanToHistory } = useDevSweep()
  const { viewMode } = useViewMode()
  const navigate = useNavigate()
  const [selectingPath, setSelectingPath] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [retryProject, setRetryProject] = useState<Pick<ScanResponse, 'project_path' | 'access_grant_id'> | null>(null)
  const [storedProjects, setStoredProjects] = useState<StoredProject[]>([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [historyError, setHistoryError] = useState<string | null>(null)

  const loadStoredProjects = async () => {
    setHistoryLoading(true)
    setHistoryError(null)
    try {
      const data = await requestJson<{ projects: StoredProject[] }>('/api/cleanup/history/projects')
      setStoredProjects(data.projects)
    } catch (err) {
      setHistoryError(apiErrorMessage(err, viewMode))
    } finally {
      setHistoryLoading(false)
    }
  }

  useEffect(() => { void loadStoredProjects() }, [])

  // addScanToHistory prepends each result; retain the newest scan for each path.
  const projects = scanHistory.reduce<ScanResponse[]>((unique, scan) => {
    if (!unique.some(item => item.project_path === scan.project_path)) unique.push(scan)
    return unique
  }, [])

  const refreshAndSelect = async (project: Pick<ScanResponse, 'project_path' | 'access_grant_id'>) => {
    if (selectingPath) return
    setSelectingPath(project.project_path)
    setError(null)
    setRetryProject(project)
    try {
      const refreshed = await requestJson<ScanResponse>('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: project.project_path,
          access_grant_id: project.access_grant_id,
        }),
      })
      setCurrentProject(refreshed)
      addScanToHistory(refreshed)
      navigate('/')
    } catch (selectError) {
      setError(apiErrorMessage(selectError, viewMode))
    } finally {
      setSelectingPath(null)
    }
  }

  const columns: Column<ScanResponse>[] = [
    { key: 'name', header: 'Project', render: scan => <div className="min-w-48"><p className="font-medium">{projectName(scan.project_path)}</p><p className="mt-1 break-all font-mono text-xs text-devsweep-textMuted">{scan.project_path}</p></div> },
    { key: 'type', header: 'Type', render: scan => <span>{scan.project_type}</span> },
    { key: 'framework', header: 'Framework', render: scan => <span>{scan.framework || 'Not detected'}</span> },
    { key: 'metadata', header: 'Metadata', render: scan => <div className="space-y-1 text-xs"><p>{scan.language || 'Language not detected'}</p><p>{scan.package_manager || 'Package manager not detected'}</p></div> },
    { key: 'scan', header: 'Latest scan data', render: scan => <div className="space-y-1 text-xs"><p>{scan.cleanup_candidates.length} candidates</p><p>{scan.total_recoverable_human} recoverable</p><p>{scan.has_git ? (scan.git_clean ? 'Git clean at scan' : 'Uncommitted at scan') : 'Git not detected'}</p></div> },
    { key: 'actions', header: 'Action', align: 'right', render: scan => <Button size="sm" variant="secondary" onClick={() => refreshAndSelect(scan)} disabled={Boolean(selectingPath)} loading={selectingPath === scan.project_path} icon={<RefreshCw className="h-4 w-4" />}>Refresh & select</Button> },
  ]

  return (
    <div className="space-y-6 animate-in">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div><h1 className="text-2xl font-bold">Projects</h1><p className="mt-1 text-devsweep-textSecondary">Projects scanned during this session, using the latest scan available for each path.</p></div>
        <Button onClick={() => navigate('/scan')} icon={<FolderGit2 className="h-4 w-4" />}>Open scan workspace</Button>
      </header>

      {error && <ErrorAlert title="Project could not be selected" message={error} dismissible onDismiss={() => setError(null)} action={retryProject ? { label: 'Retry', onClick: () => void refreshAndSelect(retryProject) } : undefined} />}
      {historyError && <ErrorAlert title="Saved project history unavailable" message={historyError} action={{ label: 'Retry', onClick: () => void loadStoredProjects() }} />}
      <section className="space-y-3" aria-labelledby="saved-projects-heading">
        <div><h2 id="saved-projects-heading" className="text-lg font-semibold">Saved projects</h2><p className="text-sm text-devsweep-textMuted">Project metadata and successful scans stored by this backend.</p></div>
        {historyLoading ? <Card role="status"><LoadingState text="Loading saved projects…" /></Card> : storedProjects.length === 0 ? <Card padding="sm"><p className="text-sm text-devsweep-textMuted">No persistent project records yet.</p></Card> : <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">{storedProjects.map(project => {
          const sessionProject = projects.find(item => item.project_path === project.project_path)
          const availability = sessionProject?.access_grant_id ? 'available' : project.availability
          const latest = sessionProject || project.latest_scan
          const availabilityText = availability === 'available' ? 'Available for a fresh scan' : availability === 'requires_grant' ? 'External folder requires a new access grant' : availability === 'identity_changed' ? 'Folder identity changed; review before using' : 'Folder is missing or inaccessible'
          return <Card key={project.project_id}>
            <CardHeader className="mb-3"><CardTitle as="h3" className="break-words">{project.name}</CardTitle><CardDescription className="break-all font-mono">{project.project_path}</CardDescription></CardHeader>
            <div className="space-y-2 text-sm"><p>{project.project_type} · {availabilityText}</p><p className="text-xs text-devsweep-textMuted">Last accessed {new Date(project.last_accessed_at).toLocaleString()}{project.latest_scan_at ? ` · Latest successful scan ${new Date(project.latest_scan_at).toLocaleString()}` : ' · No successful scan recorded'}</p>
              {latest && <p className="text-devsweep-textSecondary">Latest scan: {latest.cleanup_candidates.length} cleanup candidates · {latest.total_recoverable_human} candidate size</p>}
              {viewMode === 'technical' && <p className="break-all font-mono text-xs text-devsweep-textMuted">Project ID: {project.project_id}</p>}
            </div>
            <div className="mt-3 flex justify-end"><Button size="sm" variant="secondary" onClick={() => refreshAndSelect({ project_path: project.project_path, access_grant_id: sessionProject?.access_grant_id })} disabled={Boolean(selectingPath) || availability !== 'available'} loading={selectingPath === project.project_path} icon={<RefreshCw className="h-4 w-4" />}>{availability === 'available' ? 'Refresh & select' : 'Unavailable'}</Button></div>
          </Card>
        })}</div>}
      </section>
      {selectingPath && <Card role="status" padding="sm"><LoadingState variant="inline" text={`Checking access and refreshing ${selectingPath}…`} /></Card>}

      {projects.length === 0 ? (
        <Card padding="none"><EmptyState illustration="project" title="No projects scanned yet" description="Scanned projects appear here for this session. No persistent project registry is available." action={{ label: 'Scan a project', onClick: () => navigate('/scan') }} /></Card>
      ) : viewMode === 'technical' ? (
        <>
          <p className="text-sm text-devsweep-textSecondary">Technical details reflect scan responses only. Paths are refreshed before selection; inaccessible paths return an error and are not selected.</p>
          <DataTable data={projects} columns={columns} keyExtractor={scan => scan.project_path} emptyState={<EmptyState title="No projects scanned" />} />
        </>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {projects.map(project => {
            const isSelected = currentProject?.project_path === project.project_path
            return (
              <Card key={project.project_path} className={cn(isSelected && 'border-devsweep-accent/50')}>
                <CardHeader className="mb-3 flex flex-row items-start justify-between gap-3">
                  <div className="min-w-0"><CardTitle as="h2" className="break-words">{projectName(project.project_path)}</CardTitle><CardDescription className="break-all font-mono">{project.project_path}</CardDescription></div>
                  {isSelected && <span className="shrink-0 rounded-full bg-devsweep-accent/10 px-2 py-1 text-xs font-medium text-devsweep-accent">Selected</span>}
                </CardHeader>
                <div className="space-y-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-devsweep-bgTertiary px-2 py-1 text-xs">{project.project_type}</span>{project.framework && project.framework !== 'unknown' && <span className="rounded-full bg-devsweep-accent/10 px-2 py-1 text-xs text-devsweep-accent">{project.framework}</span>}</div>
                  <p className="text-devsweep-textSecondary">{project.cleanup_candidates.length} cleanup candidate{project.cleanup_candidates.length === 1 ? '' : 's'} · {project.total_recoverable_human} identified as recoverable in the last scan.</p>
                  <div className={cn('flex items-start gap-2 rounded-lg border p-3 text-xs', !project.has_git ? 'border-devsweep-border bg-devsweep-bgTertiary/50 text-devsweep-textSecondary' : project.git_clean ? 'border-devsweep-success/20 bg-devsweep-success/10 text-devsweep-success' : 'border-devsweep-warning/20 bg-devsweep-warning/10 text-devsweep-warning')}>
                    {!project.has_git ? <AlertCircle className="h-4 w-4 shrink-0" /> : project.git_clean ? <CheckCircle className="h-4 w-4 shrink-0" /> : <AlertCircle className="h-4 w-4 shrink-0" />}
                    {project.has_git ? (project.git_clean ? 'Git working tree was clean at scan time.' : 'Uncommitted Git changes were present at scan time.') : 'Git metadata was not detected.'}
                  </div>
                </div>
                <div className="mt-4 flex justify-end"><Button size="sm" variant={isSelected ? 'primary' : 'secondary'} onClick={() => refreshAndSelect(project)} disabled={Boolean(selectingPath)} loading={selectingPath === project.project_path} icon={<RefreshCw className="h-4 w-4" />}>Refresh & select</Button></div>
              </Card>
            )
          })}
        </div>
      )}
      {projects.length > 0 && viewMode === 'technical' && currentProject && <Card><CardTitle as="h2">Selected project details</CardTitle><div className="mt-3 space-y-2 text-sm"><Detail label="Path" value={currentProject.project_path} /><Detail label="Project type" value={currentProject.project_type} /><Detail label="Framework" value={currentProject.framework} /><Detail label="Language" value={currentProject.language} /><Detail label="Package manager" value={currentProject.package_manager} /><Detail label="Git detected" value={currentProject.has_git ? 'Yes' : 'No'} />{currentProject.has_git && <Detail label="Git working tree at scan" value={currentProject.git_clean ? 'Clean' : 'Uncommitted changes'} />}<Detail label="Recoverable bytes reported" value={`${currentProject.total_recoverable_bytes} (${currentProject.total_recoverable_human})`} /><Detail label="Protected paths detected" value={currentProject.protected_paths.join(', ') || 'None reported'} />{currentProject.notes && <p className="pt-2 text-devsweep-textSecondary">{currentProject.notes}</p>}</div></Card>}
    </div>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return <div className="flex flex-col gap-1 sm:flex-row sm:justify-between sm:gap-4"><span className="shrink-0 text-devsweep-textSecondary">{label}</span><span className="break-all text-right font-mono">{value}</span></div>
}
