import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDevSweep } from '../context/DevSweepContext';
import { useViewMode } from '../context/ViewModeContext';
import { AdaptiveView, SimpleView, TechnicalView } from '../components/AdaptiveView';
import { Stepper } from '../components/ui/Stepper';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { RiskBadge, SimpleRiskBadge } from '../components/ui/RiskBadge';
import { ExpandableSection } from '../components/ui/ExpandableSection';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorAlert } from '../components/ui/ErrorAlert';
import { formatBytes, formatDuration, getRiskSemantics } from '../design-tokens';
import { apiErrorMessage, requestJson } from '../utils/api';
import {
  Search,
  FolderOpen,
  Brain,
  Trash2,
  Shield,
  AlertTriangle,
  CheckCircle,
  AlertCircle,
  XCircle,
  Loader2,
  Sparkles,
  Info,
  Zap,
  ChevronRight,
  Download,
  Cloud,
  Database,
  HardDrive,
  RefreshCw,
  Terminal,
  Eye,
  EyeOff,
} from 'lucide-react';

type ScanStep = 'scan' | 'review' | 'confirm';

interface ScanResult {
  scan_id?: string | null;
  project_id?: string | null;
  project_path: string;
  access_grant_id?: string | null;
  project_type: string;
  framework: string;
  package_manager: string;
  language: string;
  has_git: boolean;
  git_clean: boolean;
  cleanup_candidates: CleanupCandidate[];
  total_recoverable_bytes: number;
  total_recoverable_human: string;
  protected_paths: string[];
  notes: string;
}

interface CleanupCandidate {
  path: string;
  risk: 'SAFE' | 'CAUTION' | 'DANGEROUS';
  ai_risk?: 'SAFE' | 'CAUTION' | 'DANGEROUS';
  reason: string;
  size_bytes: number;
  size_human: string;
}

interface AIAnalysisResult {
  candidates: Array<{
    path: string;
    action: 'DELETE' | 'KEEP';
    risk: 'SAFE' | 'CAUTION' | 'DANGEROUS';
    ai_risk?: 'SAFE' | 'CAUTION' | 'DANGEROUS';
    reason: string;
    size_bytes: number;
    size_human: string;
  }>;
  ai_used: boolean;
  provider_name: string;
  model: string;
  analysis_id?: string;
  total_recoverable: number;
  total_recoverable_human: string;
}

const STEPS: Array<{ id: ScanStep; label: string; description: string; icon: React.ReactNode }> = [
  { id: 'scan', label: 'Scan', description: 'Select and scan a project', icon: <Search className="w-4 h-4" /> },
  { id: 'review', label: 'Review', description: 'Review cleanup candidates', icon: <Eye className="w-4 h-4" /> },
  { id: 'confirm', label: 'Confirm', description: 'Approve and execute cleanup', icon: <Shield className="w-4 h-4" /> },
];

export function ScanWorkspace() {
  const { currentProject, setCurrentProject, addScanToHistory, isScanning, setIsScanning, demoMode, setCurrentPlan, aiProvider } = useDevSweep();
  const { viewMode } = useViewMode();
  const navigate = useNavigate();

  const [customPath, setCustomPath] = useState('');
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [aiAnalysisResult, setAiAnalysisResult] = useState<AIAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creatingPlan, setCreatingPlan] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [currentStep, setCurrentStep] = useState<ScanStep>('scan');
  const [selectedCandidates, setSelectedCandidates] = useState<Set<string>>(new Set());

  // Auto-advance to review step after successful scan
  const handleScanComplete = useCallback((data: ScanResult) => {
    setScanResult(data);
    setCurrentStep('review');
    // Select all SAFE and CAUTION items by default
    const defaultSelected = new Set(
      data.cleanup_candidates
        .filter(c => c.risk !== 'DANGEROUS')
        .map(c => c.path)
    );
    setSelectedCandidates(defaultSelected);
  }, []);

  const handleScan = useCallback(async (path?: string) => {
    setIsScanning(true);
    setError(null);
    try {
      const data = await requestJson<ScanResult>('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      });
      setAiAnalysisResult(null);
      handleScanComplete(data);
      setCurrentProject(data);
      addScanToHistory(data);
    } catch (err) {
      setError(apiErrorMessage(err, viewMode));
    } finally {
      setIsScanning(false);
    }
  }, [setIsScanning, handleScanComplete, setCurrentProject, addScanToHistory, viewMode]);

  const handleDemoScan = useCallback(async () => {
    setIsScanning(true);
    setError(null);
    try {
      const data = await requestJson<ScanResult>('/api/scan/demo');
      setAiAnalysisResult(null);
      handleScanComplete(data);
      setCurrentProject(data);
      addScanToHistory(data);
    } catch (err) {
      setError(apiErrorMessage(err, viewMode));
    } finally {
      setIsScanning(false);
    }
  }, [setIsScanning, handleScanComplete, setCurrentProject, addScanToHistory, viewMode]);

  const handleAnalyze = useCallback(async () => {
    if (!scanResult) return;
    setAnalyzing(true);
    setError(null);
    try {
      const data = await requestJson<AIAnalysisResult>('/api/ai/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: scanResult.project_path,
          access_grant_id: scanResult.access_grant_id,
        }),
      });
      setAiAnalysisResult({
        candidates: data.candidates,
        ai_used: data.ai_used === true,
        provider_name: data.provider_name || 'unknown',
        model: data.model || 'unknown',
        analysis_id: data.analysis_id,
        total_recoverable: data.total_recoverable,
        total_recoverable_human: data.total_recoverable_human,
      });
    } catch (err) {
      setError(apiErrorMessage(err, viewMode));
      setAiAnalysisResult(null);
    } finally {
      setAnalyzing(false);
    }
  }, [scanResult, viewMode]);

  const handleCreatePlan = useCallback(async () => {
    if (!scanResult || !aiAnalysisResult || !aiAnalysisResult.ai_used || !aiAnalysisResult.analysis_id) {
      setError('AI analysis required before creating plan. Run AI analysis first.');
      return;
    }

    const selectedItems = aiAnalysisResult.candidates
      .filter(c => selectedCandidates.has(c.path))
      .filter(c => c.risk !== 'DANGEROUS')
      .map(c => ({
        path: c.path,
        action: c.action,
        risk: c.risk,
        scanner_risk: c.risk,
        ai_risk: c.ai_risk,
        effective_risk: c.ai_risk || c.risk,
        reason: c.reason,
        estimated_bytes: c.size_bytes,
      }));

    if (selectedItems.length === 0) {
      setError('No items selected for cleanup.');
      return;
    }

    setCreatingPlan(true);
    setError(null);
    try {
      const data = await requestJson('/api/cleanup/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: scanResult.project_path,
          analysis_id: aiAnalysisResult.analysis_id,
          scan_id: scanResult.scan_id,
          items: selectedItems,
        }),
      });
      setCurrentPlan(data);
      navigate('/plans');
    } catch (err) {
      setError(apiErrorMessage(err, viewMode));
    } finally {
      setCreatingPlan(false);
    }
  }, [scanResult, aiAnalysisResult, selectedCandidates, setCurrentPlan, navigate, viewMode]);

  const handleCandidateToggle = (path: string) => {
    const newSelection = new Set(selectedCandidates);
    if (newSelection.has(path)) {
      newSelection.delete(path);
    } else {
      newSelection.add(path);
    }
    setSelectedCandidates(newSelection);
  };

  const getSelectedStats = () => {
    if (!aiAnalysisResult) return { count: 0, bytes: 0 };
    const selected = aiAnalysisResult.candidates.filter(c => selectedCandidates.has(c.path) && c.action === 'DELETE');
    return {
      count: selected.length,
      bytes: selected.reduce((sum, c) => sum + c.size_bytes, 0),
    };
  };

  const canProceedToReview = scanResult !== null && scanResult.cleanup_candidates.length > 0;
  const canProceedToConfirm = aiAnalysisResult !== null && aiAnalysisResult.ai_used && selectedCandidates.size > 0;

  // Render Step 1: Scan
  const renderScanStep = () => (
    <Card variant="default" padding="lg">
      <CardHeader>
        <CardTitle>Step 1: Scan Workspace</CardTitle>
        <CardDescription>
          Select a project folder to analyze for cleanup opportunities. DevSweep will identify
          regenerable artifacts like caches, build outputs, and dependency directories.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <label className="block text-sm font-medium mb-2">Project Path</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={customPath}
              onChange={(e) => setCustomPath(e.target.value)}
              placeholder="Enter path or leave empty for workspace root"
              className="flex-1 px-4 py-2 bg-devsweep-bg border border-devsweep-border rounded-lg text-devsweep-text placeholder-devsweep-textMuted focus:border-devsweep-accent focus:outline-none focus:ring-1 focus:ring-devsweep-accent"
              disabled={isScanning}
            />
            <Button
              onClick={() => handleScan(customPath || undefined)}
              disabled={isScanning}
              icon={isScanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              size="lg"
            >
              {isScanning ? 'Scanning...' : 'Scan'}
            </Button>
          </div>
          <p className="text-xs text-devsweep-textMuted mt-1">Leave empty to scan the default workspace root</p>
        </div>

        {demoMode && (
          <div className="border-t border-devsweep-border pt-6">
            <p className="text-sm text-devsweep-textSecondary mb-3">
              Or try the demo project (deterministic 2+ GB recoverable):
            </p>
            <Button
              variant="secondary"
              onClick={handleDemoScan}
              disabled={isScanning}
              icon={<Sparkles className="w-4 h-4" />}
              size="lg"
              fullWidth
            >
              {isScanning ? 'Scanning...' : 'Scan Demo Project'}
            </Button>
          </div>
        )}

        {error && (
          <ErrorAlert
            title="Scan Failed"
            message={error}
            variant="error"
            dismissible
            onDismiss={() => setError(null)}
            action={{ label: 'Retry scan', onClick: () => void handleScan(customPath || undefined) }}
          />
        )}

        <div className="p-4 bg-devsweep-accent/10 border border-devsweep-accent/20 rounded-lg">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-devsweep-accent flex-shrink-0 mt-0.5" aria-hidden="true" />
            <div className="text-sm text-devsweep-textSecondary space-y-1">
              <p><strong>What DevSweep scans for:</strong> Dependency directories (node_modules, venv), build outputs (dist, build), cache directories (.vite, .next, __pycache__), log files, and temporary files.</p>
              <p><strong>What DevSweep NEVER touches:</strong> Source code, Git history, configuration files, environment files, credentials, databases, and any files matching protected patterns.</p>
              <p><strong>Safety:</strong> All deletions require your explicit approval. DANGEROUS items are never included in cleanup plans.</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );

  // Render Step 2: Review (Adaptive)
  const renderReviewStep = () => {
    if (!scanResult) return null;

    const candidates = aiAnalysisResult?.candidates || scanResult.cleanup_candidates.map(c => ({
      path: c.path,
      action: c.risk !== 'DANGEROUS' ? 'DELETE' : 'KEEP',
      risk: c.risk,
      ai_risk: c.ai_risk,
      reason: c.reason,
      size_bytes: c.size_bytes,
      size_human: c.size_human,
    }));

    const deletableCandidates = candidates.filter(c => c.action === 'DELETE');
    const dangerousCandidates = candidates.filter(c => c.risk === 'DANGEROUS');

    const renderSimpleCandidate = (candidate: typeof candidates[0], index: number) => {
      const semantics = getRiskSemantics(candidate.risk);
      const isSelected = selectedCandidates.has(candidate.path);
      const canDelete = candidate.risk !== 'DANGEROUS';
      const aiRisk = candidate.ai_risk;

      return (
        <Card key={index} variant="outlined" padding="md" className={isSelected ? 'border-devsweep-accent/50 bg-devsweep-accent/5' : ''}>
          <div className="flex items-start gap-4">
            <input
              type="checkbox"
              checked={isSelected}
              onChange={() => canDelete && handleCandidateToggle(candidate.path)}
              disabled={!canDelete}
              className="w-5 h-5 mt-0.5 rounded border-devsweep-border text-devsweep-accent focus:ring-devsweep-accent flex-shrink-0"
              aria-label={`Select ${candidate.path} for cleanup`}
            />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-2">
                <SimpleRiskBadge risk={candidate.risk} />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{candidate.path}</p>
                  <p className="text-xs text-devsweep-textMuted">{formatBytes(candidate.size_bytes)}</p>
                </div>
              </div>

              <ExpandableSection title="Why is this removable?" icon={<Info className="w-4 h-4" />}>
                <div className="space-y-2 text-sm text-devsweep-textSecondary">
                  <p><strong>What it is:</strong> {getPlainDescription(candidate.path, candidate.risk, scanResult.project_type)}</p>
                  <p><strong>Why it exists:</strong> {getWhyExists(candidate.path, scanResult.project_type, scanResult.framework)}</p>
                  <p><strong>Why it might be removable:</strong> {candidate.reason}</p>
                  <p><strong>Can it be recreated?</strong> {semantics.regenerable ? 'Yes' : 'No'}</p>
                  {semantics.regenerable && (
                    <p><strong>How to recreate:</strong> {getRegenerationCommand(candidate.path, scanResult.project_type, scanResult.package_manager)}</p>
                  )}
                  <p><strong>Consequences of removal:</strong> {semantics.consequences}</p>
                </div>
              </ExpandableSection>

              {aiRisk && aiRisk !== candidate.risk && (
                <ExpandableSection title="AI Risk Assessment" icon={<Brain className="w-4 h-4" />}>
                  <div className="space-y-2 text-sm text-devsweep-textSecondary">
                    <p>Scanner risk: <span className="font-mono">{candidate.risk}</span></p>
                    <p>AI risk: <span className="font-mono">{aiRisk}</span></p>
                    <p>Effective risk: <span className="font-mono">{candidate.risk === 'CAUTION' || aiRisk === 'CAUTION' ? 'CAUTION' : 'SAFE'}</span> (more restrictive wins)</p>
                  </div>
                </ExpandableSection>
              )}
            </div>
          </div>
        </Card>
      );
    };

    const renderTechnicalCandidate = (candidate: typeof candidates[0], index: number) => {
      const isSelected = selectedCandidates.has(candidate.path);
      const canDelete = candidate.risk !== 'DANGEROUS';
      const semantics = getRiskSemantics(candidate.risk);

      return (
        <Card key={index} variant="outlined" padding="sm" className={isSelected ? 'border-devsweep-accent/50 bg-devsweep-accent/5' : ''}>
          <div className="flex items-center gap-4">
            <input
              type="checkbox"
              checked={isSelected}
              onChange={() => canDelete && handleCandidateToggle(candidate.path)}
              disabled={!canDelete}
              className="w-5 h-5 rounded border-devsweep-border text-devsweep-accent focus:ring-devsweep-accent flex-shrink-0"
              aria-label={`Select ${candidate.path} for cleanup`}
            />
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <RiskBadge
                risk={candidate.risk}
                variant="technical"
                scannerRisk={candidate.risk}
                aiRisk={candidate.ai_risk}
                effectiveRisk={candidate.risk === 'CAUTION' || candidate.ai_risk === 'CAUTION' ? 'CAUTION' : 'SAFE'}
              />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm truncate font-mono">{candidate.path}</p>
                <p className="text-xs text-devsweep-textMuted">{candidate.reason}</p>
              </div>
              <span className="font-mono text-sm text-devsweep-textSecondary whitespace-nowrap">{formatBytes(candidate.size_bytes)}</span>
              {candidate.ai_risk && candidate.ai_risk !== candidate.risk && (
                <span className="px-2 py-0.5 text-xs bg-devsweep-accent/10 text-devsweep-accent rounded font-mono">
                  Scanner: {candidate.risk} → AI: {candidate.ai_risk}
                </span>
              )}
            </div>
          </div>
        </Card>
      );
    };

    return (
      <div className="space-y-6">
        <Card variant="default" padding="lg">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Step 2: Review Cleanup Candidates</CardTitle>
                <CardDescription>
                  {scanResult.cleanup_candidates.length} items found · {formatBytes(scanResult.total_recoverable_bytes)} total recoverable
                  {aiAnalysisResult && aiAnalysisResult.ai_used && (
                    <> · Analyzed by {aiAnalysisResult.provider_name} ({aiAnalysisResult.model})</>
                  )}
                </CardDescription>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold font-mono text-devsweep-success">{formatBytes(getSelectedStats().bytes)}</p>
                <p className="text-xs text-devsweep-textMuted">Selected for Cleanup</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4 p-3 bg-devsweep-bgTertiary/50 rounded-lg">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  ref={(el) => {
                    if (el) {
                      el.indeterminate = selectedCandidates.size > 0 && selectedCandidates.size < deletableCandidates.length;
                    }
                  }}
                  checked={selectedCandidates.size === deletableCandidates.length && deletableCandidates.length > 0}
                  onChange={() => {
                    if (selectedCandidates.size === deletableCandidates.length) {
                      setSelectedCandidates(new Set());
                    } else {
                      setSelectedCandidates(new Set(deletableCandidates.map(c => c.path)));
                    }
                  }}
                  className="w-4 h-4 rounded border-devsweep-border text-devsweep-accent focus:ring-devsweep-accent"
                />
                <span className="text-sm font-medium">Select all deletable items ({deletableCandidates.length})</span>
              </label>
            </div>

            <AdaptiveView
              simple={
                <div className="space-y-3 max-h-[500px] overflow-y-auto">
                  {deletableCandidates.map((c, i) => renderSimpleCandidate(c, i))}
                  {dangerousCandidates.map((c, i) => (
                    <Card key={`dangerous-${i}`} variant="subtle" padding="md">
                      <div className="flex items-center gap-3 text-devsweep-textMuted">
                        <XCircle className="w-5 h-5 text-devsweep-danger" />
                        <div>
                          <p className="font-medium text-sm">{c.path}</p>
                          <p className="text-xs">Protected - never deleted</p>
                        </div>
                        <RiskBadge risk="DANGEROUS" variant="simple" />
                      </div>
                    </Card>
                  ))}
                  {deletableCandidates.length === 0 && dangerousCandidates.length === 0 && (
                    <EmptyState
                      illustration="cleanup"
                      title="No cleanup candidates found"
                      description="Your workspace is clean! No regenerable artifacts were detected."
                    />
                  )}
                </div>
              }
              technical={
                <div className="space-y-2 max-h-[500px] overflow-y-auto">
                  {deletableCandidates.map((c, i) => renderTechnicalCandidate(c, i))}
                  {dangerousCandidates.map((c, i) => (
                    <Card key={`dangerous-${i}`} variant="subtle" padding="sm">
                      <div className="flex items-center gap-3 text-devsweep-textMuted">
                        <input type="checkbox" disabled className="w-5 h-5" />
                        <RiskBadge risk="DANGEROUS" variant="technical" scannerRisk="DANGEROUS" />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm font-mono truncate">{c.path}</p>
                          <p className="text-xs text-devsweep-textMuted">{c.reason}</p>
                        </div>
                        <span className="font-mono text-sm text-devsweep-textSecondary">{formatBytes(c.size_bytes)}</span>
                      </div>
                    </Card>
                  ))}
                  {deletableCandidates.length === 0 && dangerousCandidates.length === 0 && (
                    <EmptyState
                      illustration="cleanup"
                      title="No cleanup candidates found"
                      description="Your workspace is clean! No regenerable artifacts were detected."
                    />
                  )}
                </div>
              }
            />

            <div className="pt-4 border-t border-devsweep-border flex items-center justify-between">
              <div className="text-sm text-devsweep-textSecondary">
                {selectedCandidates.size} of {deletableCandidates.length} deletable items selected
                {dangerousCandidates.length > 0 && (
                  <> · {dangerousCandidates.length} protected items excluded</>
                )}
              </div>
              <Button
                variant={selectedCandidates.size > 0 ? 'primary' : 'secondary'}
                onClick={() => setCurrentStep('confirm')}
                disabled={selectedCandidates.size === 0 || !aiAnalysisResult?.ai_used}
                icon={<ChevronRight className="w-4 h-4" />}
                iconPosition="right"
              >
                {selectedCandidates.size === 0 ? 'Select items to continue' : 'Continue to Confirm'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* AI Analysis section */}
        <Card variant="outlined" padding="md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="w-5 h-5" />
              AI Analysis
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {error && !analyzing && (
              <ErrorAlert
                title="AI Analysis Failed"
                message={error}
                variant="error"
                dismissible
                onDismiss={() => setError(null)}
                action={{ label: 'Retry analysis', onClick: () => void handleAnalyze() }}
              />
            )}
            {aiAnalysisResult ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {aiAnalysisResult.ai_used ? (
                    <>
                      <CheckCircle className="w-5 h-5 text-devsweep-success" />
                      <span className="text-sm font-medium">Analyzed by {aiAnalysisResult.provider_name} ({aiAnalysisResult.model})</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="w-5 h-5 text-devsweep-warning" />
                      <span className="text-sm font-medium text-devsweep-warning">Mock analysis - real AI cleanup plans unavailable</span>
                    </>
                  )}
                </div>
                <Button
                  variant="secondary"
                  onClick={handleAnalyze}
                  disabled={analyzing}
                  icon={analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Brain className="w-4 h-4" />}
                >
                  {analyzing ? 'Re-analyzing...' : 'Re-run AI Analysis'}
                </Button>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <AlertCircle className="w-5 h-5 text-devsweep-warning" />
                  <span className="text-sm font-medium">AI analysis not run yet</span>
                </div>
                <Button
                  onClick={handleAnalyze}
                  disabled={analyzing || !canProceedToReview}
                  icon={analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Brain className="w-4 h-4" />}
                >
                  {analyzing ? 'Analyzing...' : 'Run AI Analysis'}
                </Button>
              </div>
            )}
            {aiProvider === 'mock' && !aiAnalysisResult && (
              <p className="text-sm text-devsweep-warning">Demo/mock provider active. AI analysis will be labeled as demo and cannot authorize cleanup plans.</p>
            )}
          </CardContent>
        </Card>
      </div>
    );
  };

  // Render Step 3: Confirm (Adaptive)
  const renderConfirmStep = () => {
    if (!scanResult || !aiAnalysisResult) return null;

    const selectedItems = aiAnalysisResult.candidates.filter(c => selectedCandidates.has(c.path) && c.action === 'DELETE');
    const totalBytes = selectedItems.reduce((sum, c) => sum + c.size_bytes, 0);
    const cautionItems = selectedItems.filter(c => c.risk === 'CAUTION' || c.ai_risk === 'CAUTION');
    const safeItems = selectedItems.filter(c => c.risk === 'SAFE' && c.ai_risk !== 'CAUTION');

    const renderSimpleConfirmItem = (item: typeof selectedItems[0]) => {
      const semantics = getRiskSemantics(item.risk);
      const aiRisk = item.ai_risk;

      return (
        <div key={item.path} className="flex items-start gap-3 p-3 bg-devsweep-bgTertiary/50 rounded-lg">
          <div className="flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center bg-devsweep-success/10 text-devsweep-success">
            <CheckCircle className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <SimpleRiskBadge risk={item.risk} />
              <span className="font-medium text-sm truncate">{item.path}</span>
            </div>
            <p className="text-xs text-devsweep-textMuted">{formatBytes(item.size_bytes)}</p>
            <ExpandableSection title="Details" className="mt-1">
              <div className="space-y-1 text-sm text-devsweep-textSecondary">
                <p><strong>What it is:</strong> {getPlainDescription(item.path, item.risk, scanResult.project_type)}</p>
                <p><strong>Regeneration:</strong> {getRegenerationCommand(item.path, scanResult.project_type, scanResult.package_manager)}</p>
                <p><strong>Consequences:</strong> {semantics.consequences}</p>
                {aiRisk && aiRisk !== item.risk && (
                  <p><strong>AI upgraded risk:</strong> {item.risk} → {aiRisk} (more restrictive)</p>
                )}
              </div>
            </ExpandableSection>
          </div>
        </div>
      );
    };

    const renderTechnicalConfirmItem = (item: typeof selectedItems[0]) => {
      return (
        <div key={item.path} className="flex items-center gap-3 p-3 bg-devsweep-bgTertiary/50 rounded-lg">
          <RiskBadge
            risk={item.risk}
            variant="technical"
            scannerRisk={item.risk}
            aiRisk={item.ai_risk}
            effectiveRisk={item.risk === 'CAUTION' || item.ai_risk === 'CAUTION' ? 'CAUTION' : 'SAFE'}
          />
          <div className="flex-1 min-w-0">
            <p className="font-medium text-sm font-mono truncate">{item.path}</p>
            <p className="text-xs text-devsweep-textMuted">{item.reason}</p>
          </div>
          <span className="font-mono text-sm text-devsweep-textSecondary">{formatBytes(item.size_bytes)}</span>
        </div>
      );
    };

    return (
      <div className="space-y-6">
        <Card variant="default" padding="lg">
          <CardHeader>
            <CardTitle>Step 3: Confirm Cleanup</CardTitle>
            <CardDescription>
              Review the items that will be deleted. This action cannot be undone automatically.
              Make sure you have committed any important changes to Git.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card variant="outlined" padding="md">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-devsweep-success/10 flex items-center justify-center">
                    <HardDrive className="w-5 h-5 text-devsweep-success" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold font-mono text-devsweep-success">{formatBytes(totalBytes)}</p>
                    <p className="text-xs text-devsweep-textMuted">Storage to Recover</p>
                  </div>
                </div>
              </Card>
              <Card variant="outlined" padding="md">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-devsweep-success/10 flex items-center justify-center">
                    <CheckCircle className="w-5 h-5 text-devsweep-success" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold font-mono text-devsweep-success">{safeItems.length}</p>
                    <p className="text-xs text-devsweep-textMuted">Safe Items</p>
                  </div>
                </div>
              </Card>
              <Card variant="outlined" padding="md">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-devsweep-warning/10 flex items-center justify-center">
                    <AlertTriangle className="w-5 h-5 text-devsweep-warning" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold font-mono text-devsweep-warning">{cautionItems.length}</p>
                    <p className="text-xs text-devsweep-textMuted">Caution Items</p>
                  </div>
                </div>
              </Card>
            </div>

            <div className="border-t border-devsweep-border pt-4">
              <h4 className="font-medium mb-3">Items to be Deleted</h4>
              <AdaptiveView
                simple={
                  <div className="space-y-2 max-h-[300px] overflow-y-auto">
                    {selectedItems.map(renderSimpleConfirmItem)}
                  </div>
                }
                technical={
                  <div className="space-y-2 max-h-[300px] overflow-y-auto">
                    {selectedItems.map(renderTechnicalConfirmItem)}
                  </div>
                }
              />
            </div>

            <div className="p-4 bg-devsweep-accent/10 border border-devsweep-accent/20 rounded-lg">
              <h4 className="font-medium text-devsweep-accent flex items-center gap-2 mb-3">
                <Shield className="w-4 h-4" />
                What Will Happen
              </h4>
              <ul className="list-disc list-inside text-sm text-devsweep-textSecondary space-y-2">
                <li>Selected items will be permanently deleted from disk</li>
                <li>Your source code, Git history, and configuration files are PROTECTED</li>
                <li>Next build will regenerate build outputs (dist, build, .next, etc.)</li>
                <li>Next <code className="font-mono bg-devsweep-bgTertiary px-1 rounded">{getPackageManagerCommand(scanResult.package_manager)}</code> will reinstall dependencies</li>
                <li>Cache directories will be recreated automatically on next run</li>
                {cautionItems.length > 0 && (
                  <li className="text-devsweep-warning"><strong>Caution items:</strong> May require manual reconfiguration. Verify project works after cleanup.</li>
                )}
              </ul>
            </div>

            <div className="p-4 bg-devsweep-success/10 border border-devsweep-success/20 rounded-lg">
              <h4 className="font-medium text-devsweep-success flex items-center gap-2 mb-3">
                <CheckCircle className="w-4 h-4" />
                Safety Guarantees
              </h4>
              <ul className="list-disc list-inside text-sm text-devsweep-textSecondary space-y-1">
                <li>No source code, .git, .env, or credentials will be touched</li>
                <li>Protected paths are enforced by the backend (not just UI)</li>
                <li>DANGEROUS items are never included in cleanup plans</li>
                <li>CAUTION items require this explicit approval</li>
                <li>Project verification runs automatically after cleanup</li>
              </ul>
            </div>
          </CardContent>
          <CardFooter className="flex flex-col sm:flex-row gap-3 justify-end">
            <Button variant="ghost" onClick={() => setCurrentStep('review')}>
              <ChevronRight className="w-4 h-4" style={{ transform: 'rotate(180deg)' }} />
              Back to Review
            </Button>
            <Button
              variant="danger"
              onClick={handleCreatePlan}
              disabled={creatingPlan}
              icon={creatingPlan ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
              size="lg"
            >
              {creatingPlan ? 'Creating Plan...' : 'Approve & Create Cleanup Plan'}
            </Button>
          </CardFooter>
        </Card>

        {error && (
          <ErrorAlert
            title="Error"
            message={error}
            variant="error"
            dismissible
            onDismiss={() => setError(null)}
            action={{ label: 'Retry plan request', onClick: () => void handleCreatePlan() }}
          />
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6 animate-in max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold">Scan Workspace</h1>
        <p className="text-devsweep-textSecondary mt-1">Analyze a project for cleanup opportunities</p>
      </div>

      <Stepper
        steps={STEPS}
        currentStep={currentStep}
        onStepClick={(step: string) => {
          if (step === 'review' && !canProceedToReview) return;
          if (step === 'confirm' && !canProceedToConfirm) return;
          setCurrentStep(step as ScanStep);
        }}
        variant="horizontal"
      />

      {currentStep === 'scan' && renderScanStep()}
      {currentStep === 'review' && renderReviewStep()}
      {currentStep === 'confirm' && renderConfirmStep()}
    </div>
  );
}

// Helper functions for plain-language descriptions
function getPlainDescription(path: string, risk: string, projectType: string): string {
  const descriptions: Record<string, string> = {
    'node_modules': 'Project dependencies downloaded by your package manager',
    'dist': 'Compiled/build output generated from your source code',
    'build': 'Compiled/build output generated from your source code',
    '.next': 'Next.js build cache and compiled output',
    '.vite': 'Vite development server cache',
    '.parcel-cache': 'Parcel bundler cache',
    '__pycache__': 'Python bytecode cache for faster imports',
    '.pytest_cache': 'Pytest test runner cache',
    '.mypy_cache': 'MyPy type checker cache',
    '.ruff_cache': 'Ruff linter cache',
    'venv': 'Python virtual environment with installed packages',
    '.venv': 'Python virtual environment with installed packages',
    'env': 'Python virtual environment with installed packages',
    '.tox': 'Tox test environment directories',
    'htmlcov': 'HTML coverage reports',
    '.coverage': 'Coverage data file',
    'target': 'Rust/Cargo build output',
    'CMakeFiles': 'CMake build system files',
    'cmake-build-debug': 'CLion/CMake debug build output',
    'cmake-build-release': 'CLion/CMake release build output',
    'coverage': 'Test coverage reports',
    '.nyc_output': 'NYC coverage output',
    '.eslintcache': 'ESLint cache',
    '.stylelintcache': 'Stylelint cache',
    'logs': 'Application log files',
    'tmp': 'Temporary directory',
    'temp': 'Temporary directory',
  };

  const baseName = path.split('/').pop() || path;
  return descriptions[baseName] || `${baseName} (${risk.toLowerCase()} - ${getRiskSemantics(risk).description.toLowerCase()})`;
}

function getWhyExists(path: string, projectType: string, framework: string): string {
  const baseName = path.split('/').pop() || path;

  const explanations: Record<string, string> = {
    'node_modules': 'Created by npm/pnpm/yarn when you run install. Contains all project dependencies.',
    'dist': `Created when you run build. Contains compiled ${projectType === 'node' ? 'JavaScript/TypeScript' : 'code'}.`,
    'build': 'Created when you compile/build the project.',
    '.next': 'Created by Next.js during development and build. Stores compiled pages and cache.',
    '.vite': 'Created by Vite dev server for fast hot module replacement.',
    '.parcel-cache': 'Created by Parcel bundler for incremental builds.',
    '__pycache__': 'Created by Python interpreter for faster module loading.',
    '.pytest_cache': 'Created by pytest to speed up test runs.',
    '.mypy_cache': 'Created by MyPy type checker for incremental checking.',
    '.ruff_cache': 'Created by Ruff linter for faster linting.',
    'venv': 'Created by Python venv module. Isolated environment for project packages.',
    '.venv': 'Created by Python venv module. Isolated environment for project packages.',
    'env': 'Created by Python venv module. Isolated environment for project packages.',
    '.tox': 'Created by tox for testing across multiple Python environments.',
    'target': 'Created by Cargo (Rust) when building the project.',
  };

  return explanations[baseName] || 'Created by development tools during normal operation.';
}

function getRegenerationCommand(path: string, projectType: string, packageManager: string): string {
  const baseName = path.split('/').pop() || path;

  const commands: Record<string, string> = {
    'node_modules': `${packageManager} install`,
    'dist': 'npm run build',
    'build': 'npm run build',
    '.next': 'npm run build',
    '.vite': 'npm run dev',
    '.parcel-cache': 'npm run dev',
    '__pycache__': 'python -m compileall .',
    '.pytest_cache': 'pytest',
    '.mypy_cache': 'mypy .',
    '.ruff_cache': 'ruff check .',
    'venv': 'python -m venv venv && pip install -r requirements.txt',
    '.venv': 'python -m venv .venv && pip install -r requirements.txt',
    'env': 'python -m venv env && pip install -r requirements.txt',
    '.tox': 'tox',
    'target': 'cargo build',
    'CMakeFiles': 'cmake --build .',
  };

  return commands[baseName] || 'Run your project\'s build/install command';
}

function getPackageManagerCommand(packageManager: string): string {
  const commands: Record<string, string> = {
    'npm': 'npm install',
    'yarn': 'yarn install',
    'pnpm': 'pnpm install',
    'pip': 'pip install -r requirements.txt',
    'poetry': 'poetry install',
    'pipenv': 'pipenv install',
    'uv': 'uv pip install -r requirements.txt',
    'cargo': 'cargo build',
  };
  return commands[packageManager] || 'your package manager install command';
}
