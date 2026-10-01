import { useState } from 'react'
import { cn, formatBytes } from '../utils/helpers'
import { useDevSweep } from '../context/DevSweepContext'
import { useNavigate } from 'react-router-dom'
import {
  Search,
  FolderOpen,
  X,
  CheckCircle,
  AlertCircle,
  XCircle,
  Loader2,
  Sparkles,
  Trash2,
  Info,
  Brain,
  Zap,
} from 'lucide-react'

export function ScanWorkspace() {
  const { currentProject, setCurrentProject, addScanToHistory, isScanning, setIsScanning, demoMode, setCurrentPlan } = useDevSweep()
  const navigate = useNavigate()
  const [customPath, setCustomPath] = useState('')
  const [scanResult, setScanResult] = useState<typeof currentProject | null>(null)
  const [aiAnalysisResult, setAiAnalysisResult] = useState<{ candidates: any[], ai_used: boolean } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [creatingPlan, setCreatingPlan] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)

  const handleAnalyze = async () => {
    if (!scanResult) return
    setAnalyzing(true)
    setError(null)
    try {
      const res = await fetch('/api/ai/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_path: scanResult.project_path }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'AI analysis failed')
      }
      const data = await res.json()
      if (!data.ai_used) {
        throw new Error('AI analysis unavailable: real model inference did not succeed')
      }
      setAiAnalysisResult({ candidates: data.candidates, ai_used: data.ai_used })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'AI analysis failed')
      setAiAnalysisResult(null)
    } finally {
      setAnalyzing(false)
    }
  }

  const handleCreatePlan = async () => {
    if (!scanResult) return
    if (!aiAnalysisResult || !aiAnalysisResult.ai_used) {
      setError('AI analysis required before creating plan. Run AI analysis first.')
      return
    }
    setCreatingPlan(true)
    setError(null)
    try {
      // Create cleanup plan from AI analysis results
      const items = aiAnalysisResult.candidates
        .filter(c => c.risk !== 'DANGEROUS') // Never include DANGEROUS items
        .map(c => ({
          path: c.path,
          action: c.action,
          risk: c.risk,
          scanner_risk: c.risk,
          ai_risk: c.ai_risk,
          effective_risk: c.ai_risk, // effective_risk will be calculated server-side as max(scanner, ai)
          reason: c.reason,
          estimated_bytes: c.size_bytes,
        }))
      
      const res = await fetch('/api/cleanup/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          project_path: scanResult.project_path,
          items,
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to create cleanup plan')
      }
      const data = await res.json()
      // Store plan in context for CleanupPlans page
      setCurrentPlan(data)
      // Navigate to plans page
      navigate('/plans')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create cleanup plan')
    } finally {
      setCreatingPlan(false)
    }
  }

  const handleScan = async (path?: string) => {
    setIsScanning(true)
    setError(null)
    try {
      const res = await fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Scan failed')
      }
      const data = await res.json()
      setScanResult(data)
      setCurrentProject(data)
      addScanToHistory(data)
      setIsScanning(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scan failed')
      setIsScanning(false)
    }
  }

  const handleDemoScan = async () => {
    setIsScanning(true)
    setError(null)
    try {
      const res = await fetch('/api/scan/demo')
      if (!res.ok) throw new Error('Demo scan failed')
      const data = await res.json()
      setScanResult(data)
      setCurrentProject(data)
      addScanToHistory(data)
      setIsScanning(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Demo scan failed')
      setIsScanning(false)
    }
  }

  const getRiskIcon = (risk: string) => {
    switch (risk) {
      case 'SAFE': return <CheckCircle className="w-4 h-4 text-devsweep-success" />
      case 'CAUTION': return <AlertCircle className="w-4 h-4 text-devsweep-warning" />
      case 'DANGEROUS': return <XCircle className="w-4 h-4 text-devsweep-danger" />
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
        <h1 className="text-2xl font-bold">Scan Workspace</h1>
        <p className="text-devsweep-textSecondary mt-1">Analyze a project for cleanup opportunities</p>
      </div>

      <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-xl p-6 space-y-6">
        <div>
          <label className="block text-sm font-medium mb-2">Project Path</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={customPath}
              onChange={(e) => setCustomPath(e.target.value)}
              placeholder="Enter path or leave empty for workspace root"
              className="flex-1 px-4 py-2 bg-devsweep-bg border border-devsweep-border rounded-lg text-devsweep-text placeholder-devsweep-textMuted focus:border-devsweep-accent focus:outline-none focus:ring-1 focus:ring-devsweep-accent"
            />
            <button
              onClick={() => handleScan(customPath || undefined)}
              disabled={isScanning}
              className="px-6 py-2 bg-devsweep-accent text-devsweep-bg rounded-lg font-medium hover:bg-devsweep-accentHover transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isScanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              {isScanning ? 'Scanning...' : 'Scan'}
            </button>
          </div>
          <p className="text-xs text-devsweep-textMuted mt-1">Leave empty to scan the default workspace root</p>
        </div>

        {demoMode && (
          <div className="border-t border-devsweep-border pt-6">
            <p className="text-sm text-devsweep-textSecondary mb-3">Or try the demo project (deterministic 2+ GB recoverable):</p>
            <button
              onClick={handleDemoScan}
              disabled={isScanning}
              className="px-6 py-2 bg-devsweep-warning/10 text-devsweep-warning border border-devsweep-warning/20 rounded-lg font-medium hover:bg-devsweep-warning/20 transition-colors flex items-center gap-2"
            >
              <Sparkles className="w-4 h-4" />
              {isScanning ? 'Scanning...' : 'Scan Demo Project'}
            </button>
          </div>
        )}

        {error && (
          <div className="p-4 bg-devsweep-danger/10 border border-devsweep-danger/20 rounded-lg flex items-center gap-3 text-devsweep-danger">
            <XCircle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {scanResult && (
          <div className="border-t border-devsweep-border pt-6 space-y-6 animate-in">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">{scanResult.project_path.split('/').pop()}</h2>
                <div className="flex items-center gap-3 mt-1 text-sm text-devsweep-textSecondary">
                  <span className="px-2 py-0.5 bg-devsweep-bgTertiary rounded font-mono">{scanResult.project_type}</span>
                  <span className="px-2 py-0.5 bg-devsweep-accent/10 text-devsweep-accent rounded font-mono">{scanResult.framework}</span>
                  <span className="px-2 py-0.5 bg-devsweep-bgTertiary rounded font-mono">{scanResult.language}</span>
                  <span className="px-2 py-0.5 bg-devsweep-bgTertiary rounded font-mono">{scanResult.package_manager}</span>
                </div>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold font-mono text-devsweep-success">{scanResult.total_recoverable_human}</p>
                <p className="text-xs text-devsweep-textMuted">Total Recoverable</p>
              </div>
            </div>

            <div>
              <h3 className="font-medium mb-3">Cleanup Candidates</h3>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {scanResult.cleanup_candidates.map((candidate, i) => (
                  <div key={i} className="bg-devsweep-bg border border-devsweep-border rounded-lg p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-1">
                          <span className={cn('w-6 h-6 rounded flex items-center justify-center text-xs font-medium', 
                            candidate.risk === 'SAFE' && 'bg-devsweep-success/20 text-devsweep-success',
                            candidate.risk === 'CAUTION' && 'bg-devsweep-warning/20 text-devsweep-warning',
                            candidate.risk === 'DANGEROUS' && 'bg-devsweep-danger/20 text-devsweep-danger'
                          )}>
                            {getRiskIcon(candidate.risk)}
                          </span>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-sm truncate">{candidate.path}</p>
                            <p className="text-xs text-devsweep-textMuted">{candidate.reason}</p>
                          </div>
                          <span className="font-mono text-sm text-devsweep-textSecondary whitespace-nowrap">{candidate.size_human}</span>
                        </div>
                        <div className="ml-9 flex items-center gap-2">
                          {getRiskBadge(candidate.risk)}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                {scanResult.cleanup_candidates.length === 0 && (
                  <div className="text-center py-8 text-devsweep-textMuted">
                    <CheckCircle className="w-12 h-12 mx-auto mb-2 text-devsweep-success" />
                    <p>No cleanup candidates found. Your workspace is clean!</p>
                  </div>
                )}
              </div>
            </div>

            <div className="border-t border-devsweep-border pt-4">
              <h3 className="font-medium mb-3">Protected Paths (Never Deleted)</h3>
              <div className="flex flex-wrap gap-2">
                {scanResult.protected_paths.slice(0, 20).map((path, i) => (
                  <span key={i} className="px-2 py-1 text-xs bg-devsweep-bgTertiary text-devsweep-textMuted rounded font-mono">{path}</span>
                ))}
                {scanResult.protected_paths.length > 20 && (
                  <span className="px-2 py-1 text-xs text-devsweep-textMuted">+{scanResult.protected_paths.length - 20} more</span>
                )}
              </div>
            </div>

            <div className="flex gap-3 pt-4 border-t border-devsweep-border">
              {/* AI Analyze button - must run before creating plan */}
              <button
                onClick={handleAnalyze}
                disabled={analyzing || creatingPlan || !scanResult || scanResult.cleanup_candidates.length === 0}
                className="px-6 py-2 bg-devsweep-warning/10 text-devsweep-warning border border-devsweep-warning/20 rounded-lg font-medium hover:bg-devsweep-warning/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Brain className="w-4 h-4" />}
                {analyzing ? 'Analyzing with AI...' : 'Run AI Analysis'}
              </button>
              
              {/* Create Cleanup Plan button - requires AI analysis first */}
              <button
                onClick={handleCreatePlan}
                disabled={creatingPlan || !aiAnalysisResult || !aiAnalysisResult.ai_used}
                className="px-6 py-2 bg-devsweep-accent text-devsweep-bg rounded-lg font-medium hover:bg-devsweep-accentHover transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {creatingPlan ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                {creatingPlan ? 'Creating Plan...' : 'Create Cleanup Plan'}
              </button>
              <button className="px-6 py-2 bg-devsweep-bg border border-devsweep-border rounded-lg font-medium hover:border-devsweep-accent/50 transition-colors flex items-center gap-2">
                <Info className="w-4 h-4" />
                View Details
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}