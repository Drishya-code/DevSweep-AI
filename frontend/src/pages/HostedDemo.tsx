import { useEffect, useState } from 'react'
import { requestJson } from '../utils/api'

type DemoFile = { path: string; size_bytes: number; risk: string; reason: string }
type Workspace = { name: string; read_only: boolean; files: DemoFile[] }
type Preview = { preview_id: string; items: DemoFile[]; total_bytes: number; requires_confirmation: boolean; will_modify_files: boolean }
type AIRecommendation = { path: string; action: 'DELETE'|'KEEP'; risk: string; reason: string }

function humanBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  return `${(bytes / 1024).toFixed(1)} KB`
}

export function HostedDemo() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [preview, setPreview] = useState<Preview | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [restoreId, setRestoreId] = useState('')
  const [analysis, setAnalysis] = useState('')
  const [aiRecommendations, setAiRecommendations] = useState<AIRecommendation[]>([])

  async function ensureSession() {
    if (!localStorage.getItem('devsweep-demo-session')) {
      const session = await requestJson<{session_id: string}>('/api/demo/sessions', { method: 'POST' })
      localStorage.setItem('devsweep-demo-session', session.session_id)
    }
  }

  async function loadWorkspace() {
    setBusy(true); setError('')
    try { await ensureSession(); setWorkspace(await requestJson<Workspace>('/api/demo/workspace')) }
    catch (e) { setError(e instanceof Error ? e.message : 'The demo workspace could not be loaded.') }
    finally { setBusy(false) }
  }
  useEffect(() => { void loadWorkspace() }, [])

  function toggle(path: string) {
    setSelected(current => current.includes(path) ? current.filter(item => item !== path) : [...current, path])
    setPreview(null); setMessage('')
  }

  async function makePreview() {
    setBusy(true); setError(''); setMessage('')
    try { setPreview(await requestJson<Preview>('/api/demo/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ paths: selected }) })) }
    catch (e) { setError(e instanceof Error ? e.message : 'Preview failed.') }
    finally { setBusy(false) }
  }

  async function analyzeFiles() {
    if (!workspace) return
    setBusy(true); setError(''); setAnalysis(''); setAiRecommendations([])
    try {
      const result = await requestJson<{analysis: string}>('/api/demo/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ files: workspace.files.map(({path,size_bytes,risk,reason}) => ({path,size_bytes,risk,reason})) }) })
      setAnalysis(result.analysis)
      const json = result.analysis.match(/\{[\s\S]*\}/)?.[0]
      if (!json) throw new Error('Nebius returned an unreadable recommendation. No files can be selected from AI output.')
      const parsed = JSON.parse(json) as {recommendations?: AIRecommendation[]}
      const listed = new Set(workspace.files.filter(file=>file.risk==='SAFE').map(file=>file.path))
      setAiRecommendations((parsed.recommendations || []).filter(item=>listed.has(item.path) && item.action==='DELETE' && item.risk==='SAFE' && typeof item.reason==='string'))
    } catch (e) { setError(e instanceof Error ? e.message : 'AI analysis failed.') }
    finally { setBusy(false) }
  }

  async function executeCleanup() {
    setBusy(true); setError('')
    try {
      if (!preview) throw new Error('Review a preview before confirming.')
      const result = await requestJson<{ message: string; restore_id: string }>('/api/demo/confirm', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ paths: selected, preview_id: preview.preview_id, approved: true }) })
      setMessage(result.message); setRestoreId(result.restore_id); setPreview(null); setSelected([]); await loadWorkspace()
    } catch (e) { setError(e instanceof Error ? e.message : 'Cleanup could not be completed.') }
    finally { setBusy(false) }
  }

  async function resetWorkspace() {
    setBusy(true); setError('')
    try { await requestJson('/api/demo/reset', { method: 'POST' }); setSelected([]); setPreview(null); setRestoreId(''); setMessage('Your synthetic workspace was reset.'); await loadWorkspace() }
    catch (e) { setError(e instanceof Error ? e.message : 'Reset failed.') }
    finally { setBusy(false) }
  }

  async function restoreWorkspace() {
    setBusy(true); setError('')
    try { await requestJson(`/api/demo/restore/${restoreId}`, { method: 'POST' }); setRestoreId(''); setMessage('Your files were restored.'); await loadWorkspace() }
    catch (e) { setError(e instanceof Error ? e.message : 'Restore failed.') }
    finally { setBusy(false) }
  }

  return <section className="mx-auto max-w-4xl space-y-6">
    <div className="rounded-2xl border border-devsweep-border bg-devsweep-card p-6 sm:p-8">
      <p className="text-sm font-semibold uppercase tracking-wide text-devsweep-accent">Hosted safe demo</p>
      <h1 className="mt-2 text-3xl font-bold text-devsweep-text">See a cleanup plan in action</h1>
      <p className="mt-3 max-w-2xl text-devsweep-textMuted">Explore your isolated synthetic workspace, inspect generated artifacts, and confirm a real cleanup. Removed files stay in your private restore area until you reset your sample.</p>
    </div>

    {error && <div role="alert" className="rounded-xl border border-red-300 bg-red-50 p-4 text-red-800">{error} <button className="ml-2 underline" onClick={() => void loadWorkspace()}>Retry</button></div>}
    {message && <div role="status" className="rounded-xl border border-emerald-300 bg-emerald-50 p-4 text-emerald-800">{message}</div>}

    <div className="rounded-2xl border border-devsweep-border bg-devsweep-bgSecondary p-6">
      <div className="flex items-center justify-between gap-3">
        <div><h2 className="text-xl font-semibold text-devsweep-text">{workspace?.name || 'Synthetic workspace'}</h2><p className="mt-1 text-sm text-devsweep-textMuted">Isolated persistent sample · synthetic files only</p></div>
        <button className="rounded-lg border border-devsweep-border px-3 py-2 text-sm text-devsweep-text disabled:opacity-50" onClick={() => void loadWorkspace()} disabled={busy}>Refresh</button>
      </div>
      <div className="mt-5 divide-y divide-devsweep-border">
        {workspace?.files.map(file => <label key={file.path} className="flex cursor-pointer items-start gap-3 py-4">
          <input type="checkbox" className="mt-1" checked={selected.includes(file.path)} onChange={() => toggle(file.path)} disabled={file.risk !== 'SAFE' || !aiRecommendations.some(item=>item.path===file.path)} />
          <span className="min-w-0 flex-1"><span className="block font-mono text-sm text-devsweep-text">{file.path}</span><span className="mt-1 block text-sm text-devsweep-textMuted">{file.reason}</span></span>
          <span className="whitespace-nowrap text-sm text-devsweep-textMuted">{humanBytes(file.size_bytes)}</span>
        </label>)}
        {workspace && workspace.files.length === 0 && <p className="py-5 text-sm text-devsweep-textMuted">No sample files are available.</p>}
      </div>
      <div className="mt-3 flex flex-wrap gap-2"><button className="rounded-lg bg-devsweep-accent px-4 py-2.5 font-medium text-white disabled:cursor-not-allowed disabled:opacity-50" onClick={() => void analyzeFiles()} disabled={busy || !workspace}>Ask Nebius to analyze metadata</button><button className="rounded-lg bg-devsweep-accent px-4 py-2.5 font-medium text-white disabled:cursor-not-allowed disabled:opacity-50" onClick={() => void makePreview()} disabled={busy || selected.length === 0}>Preview selected cleanup</button><button className="rounded-lg border border-devsweep-border px-4 py-2.5 text-devsweep-text" onClick={() => void resetWorkspace()} disabled={busy}>Reset sample</button>{restoreId && <button className="rounded-lg border border-devsweep-border px-4 py-2.5 text-devsweep-text" onClick={() => void restoreWorkspace()} disabled={busy}>Undo last cleanup</button>}</div>
    </div>

    {analysis && <div className="rounded-2xl border border-devsweep-border bg-devsweep-card p-6"><h2 className="font-semibold text-devsweep-text">Nebius recommendations</h2>{aiRecommendations.length ? <ul className="mt-3 space-y-2 text-sm text-devsweep-textMuted">{aiRecommendations.map(item=><li key={item.path}><span className="font-mono text-devsweep-text">{item.path}</span> — {item.reason}</li>)}</ul> : <p className="mt-2 text-sm text-devsweep-textMuted">Nebius did not approve any listed SAFE files for cleanup.</p>}<p className="mt-3 text-xs text-devsweep-textMuted">Only listed SAFE recommendations can be selected; preview shows the expected bytes and asks for confirmation.</p></div>}

    {preview && <div className="rounded-2xl border border-amber-300 bg-amber-50 p-6 text-amber-950">
      <h2 className="text-lg font-semibold">Confirm cleanup</h2>
      <p className="mt-2 text-sm">{preview.items.length} synthetic file(s), {humanBytes(preview.total_bytes)} will be moved into this session’s private restore area.</p>
      <ul className="my-3 list-inside list-disc text-sm">{preview.items.map(item => <li key={item.path} className="font-mono">{item.path}</li>)}</ul>
      {preview.requires_confirmation && <button className="rounded-lg bg-amber-900 px-4 py-2.5 font-medium text-white disabled:opacity-50" onClick={() => void executeCleanup()} disabled={busy}>I understand — clean selected files</button>}
    </div>}
    <p className="text-center text-xs text-devsweep-textMuted">DevSweep AI · Clean. Keep. Restore.</p>
  </section>
}
