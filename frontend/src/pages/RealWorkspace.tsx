import { useState } from 'react'
import { requestJson } from '../utils/api'

type DirHandle = FileSystemDirectoryHandle & { entries: () => AsyncIterableIterator<[string, FileSystemDirectoryHandle|FileSystemFileHandle]>; requestPermission?: (d: {mode:'readwrite'}) => Promise<PermissionState>; queryPermission?: (d: {mode:'readwrite'}) => Promise<PermissionState> }
type Entry = { path: string; size_bytes: number; modified: number; safe: boolean }
type Recommendation = { path: string; action: 'DELETE'|'KEEP'; risk: string; reason: string }
const safePattern = /(^|\/)(node_modules|dist|build|coverage|\.next|\.cache|__pycache__|\.venv|venv|tmp|temp)(\/|$)|\.log$/i

async function walk(dir: DirHandle, prefix = ''): Promise<Entry[]> {
  const out: Entry[] = []
  for await (const [name, handle] of dir.entries()) {
    if (name === '.git' || name.startsWith('.devsweep-trash')) continue
    const path = prefix ? `${prefix}/${name}` : name
    if (handle.kind === 'directory') out.push(...await walk(handle as DirHandle, path))
    else { const f = await handle.getFile(); out.push({path,size_bytes:f.size,modified:f.lastModified,safe:safePattern.test(path)}) }
    if (out.length > 500) throw new Error('This folder contains more than 500 files. Select a smaller folder.')
  }
  return out
}

function findDir(root: DirHandle, parts: string[]) {
  return (async () => { let current = root; for (const part of parts.slice(0,-1)) current = await current.getDirectoryHandle(part) as DirHandle; return current })()
}

export function RealWorkspace() {
  const [root,setRoot] = useState<DirHandle|null>(null)
  const [label,setLabel] = useState('')
  const [files,setFiles] = useState<Entry[]>([])
  const [plans,setPlans] = useState<Recommendation[]>([])
  const [error,setError] = useState('')
  const [message,setMessage] = useState('')
  const [busy,setBusy] = useState(false)
  const [restoreId,setRestoreId] = useState('')
  const supported = typeof window !== 'undefined' && 'showDirectoryPicker' in window

  async function chooseFolder() {
    setError(''); setMessage(''); setPlans([])
    if (!supported) { setError('This browser does not support secure folder selection. Try a current Chromium browser over HTTPS, or use the synthetic demo. Your files are not uploaded.'); return }
    try {
      const picker = (window as unknown as {showDirectoryPicker: (options:{mode:'readwrite'})=>Promise<DirHandle>}).showDirectoryPicker
      const selected = await picker({mode:'readwrite'})
      const permission = selected.requestPermission ? await selected.requestPermission({mode:'readwrite'}) : 'granted'
      if (permission !== 'granted') { setRoot(null); setFiles([]); setError('Folder access was denied. Select the folder again and allow read and write access to continue.'); return }
      const selectedDir = selected as DirHandle
      setRoot(selectedDir); setLabel(selected.name)
      const inventory = await walk(selectedDir); setFiles(inventory); setMessage(`${inventory.length} file(s) inventoried in the selected folder. File contents stay on this device.`)
    } catch (e) { if (e instanceof DOMException && e.name === 'AbortError') return; setError(e instanceof Error ? e.message : 'Could not read that folder. Access may have been revoked; select it again.') }
  }

  async function analyze() {
    if (!root) return
    setBusy(true); setError(''); setPlans([])
    try {
      const result = await requestJson<{analysis:string}>('/api/ai/metadata',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({files:files.map(({path,size_bytes,modified})=>({path,size_bytes,modified}))})})
      const raw = result.analysis.match(/\{[\s\S]*\}/)?.[0]
      if (!raw) throw new Error('Nebius returned an unreadable recommendation. No files were changed.')
      const parsed = JSON.parse(raw) as {recommendations?: Recommendation[]}
      const listed = new Set(files.map(f=>f.path))
      setPlans((parsed.recommendations||[]).filter(x=>listed.has(x.path) && files.some(f=>f.path===x.path && f.safe) && x.action==='DELETE' && x.risk==='SAFE'))
      setMessage('Nebius reviewed only relative paths, sizes, and timestamps. Protected and unrecognized paths were excluded from the plan.')
    } catch(e) { setError(e instanceof Error ? e.message : 'Nebius analysis failed.') }
    finally { setBusy(false) }
  }

  async function execute() {
    if (!root || !plans.length) return
    if (!window.confirm(`Move ${plans.length} listed generated file(s) into .devsweep-trash for undo?`)) return
    setBusy(true); setError(''); const id = crypto.randomUUID(); const moved: string[] = []
    try {
      const trash = await root.getDirectoryHandle('.devsweep-trash',{create:true}) as DirHandle
      for (const item of plans) {
        if (!files.some(f=>f.path===item.path && f.safe)) continue
        const parts=item.path.split('/'); const parent=await findDir(root,parts); const name=parts[parts.length-1]
        const src=await parent.getFileHandle(name); const file=await src.getFile(); const bytes=await file.arrayBuffer()
        let dest=trash
        for (const part of [id,...parts.slice(0,-1)]) dest=await dest.getDirectoryHandle(part,{create:true}) as DirHandle
        const target=await dest.getFileHandle(name,{create:true}); const writer=await target.createWritable(); await writer.write(bytes); await writer.close(); await parent.removeEntry(name); moved.push(item.path)
      }
      setRestoreId(id); setPlans([]); setFiles(await walk(root)); setMessage(`${moved.length} file(s) moved into this folder’s .devsweep-trash/${id} restore area.`)
    } catch(e) { setError(`${e instanceof Error ? e.message : 'Operation failed.'} Completed moves are retained in the restore area.`); setRestoreId(id); setFiles(await walk(root)) }
    finally { setBusy(false) }
  }

  async function undo() {
    if (!root || !restoreId) return
    setBusy(true); setError('')
    try {
      const trash=await root.getDirectoryHandle('.devsweep-trash') as DirHandle; const restore=await trash.getDirectoryHandle(restoreId) as DirHandle
      async function restoreTree(dir: DirHandle, prefix=''): Promise<void> {
        for await (const [name,handle] of dir.entries()) {
          const path=prefix?`${prefix}/${name}`:name
          if(handle.kind==='directory') await restoreTree(handle as DirHandle,path)
          else { const parts=path.split('/'); let dest=root!; for(const part of parts.slice(0,-1)) dest=await dest.getDirectoryHandle(part,{create:true}) as DirHandle; try { await dest.getFileHandle(parts[parts.length-1]); throw new Error(`Cannot restore ${path}: a file now exists at that path.`) } catch(e) { if (!(e instanceof DOMException && e.name === 'NotFoundError')) throw e }; const source=await dir.getFileHandle(name); const data=await (await source.getFile()).arrayBuffer(); const target=await dest.getFileHandle(parts[parts.length-1],{create:true}); const w=await target.createWritable(); await w.write(data); await w.close(); await dir.removeEntry(name) }
        }
      }
      await restoreTree(restore); await trash.removeEntry(restoreId,{recursive:true}); setRestoreId(''); setFiles(await walk(root)); setMessage('Files restored to their original relative paths.')
    } catch(e) { setError(e instanceof Error?e.message:'Restore could not finish. Check that the selected folder remains writable.') }
    finally { setBusy(false) }
  }

  return <section className="mx-auto max-w-5xl space-y-6">
    <header className="rounded-2xl border border-devsweep-border bg-devsweep-card p-6"><p className="text-sm font-semibold uppercase tracking-wide text-devsweep-accent">Real workspace · browser permission</p><h1 className="mt-2 text-3xl font-bold text-devsweep-text">Clean a folder you choose</h1><p className="mt-3 text-devsweep-textMuted">Your browser opens its native folder picker. DevSweep can inspect and change files only inside the folder you choose. The server receives relative paths, sizes, and modification times for AI analysis; file contents stay in your browser. Use HTTPS and a supported Chromium browser.</p><button onClick={()=>void chooseFolder()} disabled={busy} className="mt-5 rounded-lg bg-devsweep-accent px-4 py-2.5 font-medium text-white">{root?`Choose another folder · ${label}`:'Choose folder and grant access'}</button></header>
    {error&&<div role="alert" className="rounded-xl border border-red-300 bg-red-50 p-4 text-red-800">{error}</div>}{message&&<div role="status" className="rounded-xl border border-emerald-300 bg-emerald-50 p-4 text-emerald-800">{message}</div>}
    {root&&<section className="rounded-2xl border border-devsweep-border bg-devsweep-bgSecondary p-6"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-semibold text-devsweep-text">{label}</h2><p className="text-sm text-devsweep-textMuted">{files.length} inventoried files · {files.filter(f=>f.safe).length} known generated artifacts</p></div><button onClick={()=>void analyze()} disabled={busy||files.length===0} className="rounded-lg bg-devsweep-accent px-4 py-2.5 text-white disabled:opacity-50">Analyze metadata with Nebius</button></div><ul className="mt-4 max-h-96 divide-y divide-devsweep-border overflow-auto">{files.map(f=><li key={f.path} className="flex justify-between gap-4 py-3 text-sm"><span className="break-all font-mono text-devsweep-text">{f.path}</span><span className="shrink-0 text-devsweep-textMuted">{f.safe?'Generated candidate':'Protected'} · {f.size_bytes.toLocaleString()} B</span></li>)}</ul>
      {plans.length>0&&<div className="mt-5 rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-950"><h3 className="font-semibold">Review before cleanup</h3><ul className="my-3 list-disc pl-5">{plans.map(p=><li key={p.path}><span className="font-mono">{p.path}</span> — {p.reason}</li>)}</ul><button onClick={()=>void execute()} disabled={busy} className="rounded-lg bg-amber-900 px-4 py-2 text-white">Confirm move to local restore area</button></div>}
      {restoreId&&<button onClick={()=>void undo()} disabled={busy} className="mt-4 rounded-lg border border-devsweep-border px-4 py-2 text-devsweep-text">Undo last cleanup</button>}
    </section>}
  </section>
}
