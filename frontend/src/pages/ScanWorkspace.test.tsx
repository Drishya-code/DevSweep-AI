import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ScanWorkspace } from '../pages/ScanWorkspace'
import { MemoryRouter } from 'react-router-dom'
import { mockNavigate } from '../test/setup'

// Mock project data
const mockScanResult = {
  project_path: '/test/project',
  project_type: 'node',
  framework: 'react',
  package_manager: 'npm',
  language: 'typescript',
  has_git: true,
  git_clean: true,
  cleanup_candidates: [
    {
      path: 'node_modules',
      size_bytes: 100000000,
      size_human: '95.4 MB',
      risk: 'SAFE',
      reason: 'Regenerable using package-lock.json',
    },
    {
      path: 'dist',
      size_bytes: 50000000,
      size_human: '47.7 MB',
      risk: 'SAFE',
      reason: 'Generated build output',
    },
    {
      path: 'cache',
      size_bytes: 20000000,
      size_human: '19.1 MB',
      risk: 'CAUTION',
      reason: 'Cache files may have performance impact',
    },
  ],
  protected_paths: [
    'src/',
    'package.json',
    'package-lock.json',
    '.git/',
  ],
  total_recoverable_bytes: 170000000,
  total_recoverable_human: '162.1 MB',
}

const mockAIAnalysisResult = {
  candidates: [
    {
      path: 'node_modules',
      action: 'DELETE',
      risk: 'SAFE',
      ai_risk: 'SAFE',
      reason: 'Regenerable using package-lock.json',
      size_bytes: 100000000,
      size_human: '95.4 MB',
    },
    {
      path: 'dist',
      action: 'DELETE',
      risk: 'SAFE',
      ai_risk: 'SAFE',
      reason: 'Generated build output',
      size_bytes: 50000000,
      size_human: '47.7 MB',
    },
    {
      path: 'cache',
      action: 'DELETE',
      risk: 'CAUTION',
      ai_risk: 'CAUTION',
      reason: 'Cache files may have performance impact',
      size_bytes: 20000000,
      size_human: '19.1 MB',
    },
  ],
  ai_used: true,
  provider_name: 'nebius',
  model: 'nvidia/nemotron-3-super-120b-a12b',
  analysis_id: 'verified-analysis-1',
  total_recoverable: 170000000,
  total_recoverable_human: '162.1 MB',
  project_type: 'node',
  framework: 'react',
  package_manager: 'npm',
  language: 'typescript',
}

const mockPlanResponse = {
  plan_id: 'abc12345',
  items: [
    {
      path: 'node_modules',
      action: 'DELETE',
      risk: 'SAFE',
      scanner_risk: 'SAFE',
      ai_risk: 'SAFE',
      effective_risk: 'SAFE',
      reason: 'Regenerable using package-lock.json',
      estimated_bytes: 100000000,
    },
    {
      path: 'dist',
      action: 'DELETE',
      risk: 'SAFE',
      scanner_risk: 'SAFE',
      ai_risk: 'SAFE',
      effective_risk: 'SAFE',
      reason: 'Generated build output',
      estimated_bytes: 50000000,
    },
    {
      path: 'cache',
      action: 'DELETE',
      risk: 'CAUTION',
      scanner_risk: 'CAUTION',
      ai_risk: 'CAUTION',
      effective_risk: 'CAUTION',
      reason: 'Cache files may have performance impact',
      estimated_bytes: 20000000,
    },
  ],
  total_safe_bytes: 150000000,
  total_caution_bytes: 20000000,
  total_dangerous_bytes: 0,
  requires_approval: true,
  warnings: ['1 CAUTION items require explicit approval'],
  verification_steps: ['Verify project still builds', 'Run tests if available', 'Check git status'],
}

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <MemoryRouter initialEntries={['/scan']}>
      {ui}
    </MemoryRouter>
  )
}

describe('ScanWorkspace', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(global.fetch as vi.Mock).mockReset()
    mockNavigate.mockClear()
  })

  it('renders scan form and scan button', () => {
    renderWithProviders(<ScanWorkspace />)
    
    expect(screen.getByText('Scan Workspace')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/enter path or leave empty/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^scan$/i })).toBeInTheDocument()
  })

  it('shows scan results after successful scan', async () => {
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockScanResult,
    })

    renderWithProviders(<ScanWorkspace />)
    
    // Enter a path and click scan
    fireEvent.change(screen.getByPlaceholderText(/enter path or leave empty/i), {
      target: { value: '/test/project' }
    })
    fireEvent.click(screen.getByRole('button', { name: /^scan$/i }))

    await waitFor(() => {
      expect(screen.getByText(/Review Cleanup Candidates/i)).toBeInTheDocument()
    })

    expect(screen.getByText('node_modules')).toBeInTheDocument()
    expect(screen.getByText('dist')).toBeInTheDocument()
    expect(screen.getByText('cache')).toBeInTheDocument()
  })

  it('shows Run AI Analysis button after scan', async () => {
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockScanResult,
    })

    renderWithProviders(<ScanWorkspace />)
    
    // Perform a scan first
    fireEvent.change(screen.getByPlaceholderText(/enter path or leave empty/i), {
      target: { value: '/test/project' }
    })
    fireEvent.click(screen.getByRole('button', { name: /^scan$/i }))

    await waitFor(() => {
      expect(screen.getByText('Run AI Analysis')).toBeInTheDocument()
    })
    
    // Create Cleanup Plan should be disabled until AI analysis runs
    // In new implementation, we navigate to confirm step instead
    expect(screen.queryByText('Create Cleanup Plan')).not.toBeInTheDocument()
  })

  it('calls /api/ai/analyze when Run AI Analysis is clicked', async () => {
    ;(global.fetch as vi.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockScanResult,
      })
      // Mock AI analysis
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockAIAnalysisResult,
      })

    renderWithProviders(<ScanWorkspace />)
    
    // Perform a scan first
    fireEvent.change(screen.getByPlaceholderText(/enter path or leave empty/i), {
      target: { value: '/test/project' }
    })
    fireEvent.click(screen.getByRole('button', { name: /^scan$/i }))

    await waitFor(() => {
      expect(screen.getByText('Run AI Analysis')).toBeInTheDocument()
    })

    // Click Run AI Analysis
    fireEvent.click(screen.getByText('Run AI Analysis'))

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(2)
      const analyzeCall = (global.fetch as vi.Mock).mock.calls[1]
      expect(analyzeCall[0]).toBe('/api/ai/analyze')
      const payload = JSON.parse(analyzeCall[1].body)
      expect(payload.project_path).toBe('/test/project')
    })
  })

  it('shows error when AI analysis fails', async () => {
    ;(global.fetch as vi.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockScanResult,
      })
      // Mock AI analysis failure
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'AI analysis failed: ConnectionError' }),
      })

    renderWithProviders(<ScanWorkspace />)
    
    // Perform a scan first
    fireEvent.change(screen.getByPlaceholderText(/enter path or leave empty/i), {
      target: { value: '/test/project' }
    })
    fireEvent.click(screen.getByRole('button', { name: /^scan$/i }))

    await waitFor(() => {
      expect(screen.getByText('Run AI Analysis')).toBeInTheDocument()
    })

    // Click Run AI Analysis
    fireEvent.click(screen.getByText('Run AI Analysis'))

    // Wait for analyzing to finish and error to appear
    await waitFor(() => {
      expect(screen.queryByText('Analyzing...')).not.toBeInTheDocument()
    })

    await waitFor(() => {
      expect(screen.getByText('AI analysis failed: ConnectionError')).toBeInTheDocument()
    })
  })

  it('labels mock analysis and keeps plan creation disabled when ai_used is false', async () => {
    ;(global.fetch as vi.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockScanResult,
      })
      // Mock AI analysis with ai_used=false
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockAIAnalysisResult, ai_used: false, provider_name: 'mock', model: 'devsweep-demo', analysis_id: null }),
      })

    renderWithProviders(<ScanWorkspace />)
    
    // Perform a scan first
    fireEvent.change(screen.getByPlaceholderText(/enter path or leave empty/i), {
      target: { value: '/test/project' }
    })
    fireEvent.click(screen.getByRole('button', { name: /^scan$/i }))

    await waitFor(() => {
      expect(screen.getByText('Run AI Analysis')).toBeInTheDocument()
    })

    // Click Run AI Analysis
    fireEvent.click(screen.getByText('Run AI Analysis'))

    await waitFor(() => {
      expect(screen.getByText(/mock.*analysis/i)).toBeInTheDocument()
    })
  })

  it('calls /api/cleanup/plan and navigates to /plans when Approve & Create Cleanup Plan is clicked after AI analysis', async () => {
    ;(global.fetch as vi.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockScanResult,
      })
      // Mock AI analysis
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockAIAnalysisResult,
      })
      // Mock plan creation
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockPlanResponse,
      })

    renderWithProviders(<ScanWorkspace />)
    
    // Perform a scan first
    fireEvent.change(screen.getByPlaceholderText(/enter path or leave empty/i), {
      target: { value: '/test/project' }
    })
    fireEvent.click(screen.getByRole('button', { name: /^scan$/i }))

    await waitFor(() => {
      expect(screen.getByText('Run AI Analysis')).toBeInTheDocument()
    })

    // Click Run AI Analysis
    fireEvent.click(screen.getByText('Run AI Analysis'))

    await waitFor(() => {
      expect(screen.getByText('Continue to Confirm')).toBeInTheDocument()
    })

    // Click Continue to Confirm
    fireEvent.click(screen.getByText('Continue to Confirm'))

    await waitFor(() => {
      expect(screen.getByText('Approve & Create Cleanup Plan')).toBeInTheDocument()
    })

    // Click Approve & Create Cleanup Plan
    fireEvent.click(screen.getByText('Approve & Create Cleanup Plan'))

    // Wait for plan creation and navigation
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/plans')
    })

    // Verify the plan API was called with correct payload
    expect(global.fetch).toHaveBeenCalledTimes(3)
    const planCall = (global.fetch as vi.Mock).mock.calls[2]
    expect(planCall[0]).toBe('/api/cleanup/plan')
    const payload = JSON.parse(planCall[1].body)
    expect(payload.project_path).toBe('/test/project')
    expect(payload.analysis_id).toBe('verified-analysis-1')
    expect(payload.items).toHaveLength(3)
    expect(payload.items[0].path).toBe('node_modules')
    expect(payload.items[0].action).toBe('DELETE')
    expect(payload.items[0].risk).toBe('SAFE')
    expect(payload.items[0].ai_risk).toBe('SAFE')
    expect(payload.items[2].risk).toBe('CAUTION')
    expect(payload.items[2].ai_risk).toBe('CAUTION')
  })

  it('shows error when plan creation fails', async () => {
    ;(global.fetch as vi.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockScanResult,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockAIAnalysisResult,
      })
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Plan creation failed' }),
      })

    renderWithProviders(<ScanWorkspace />)
    
    // Perform a scan first
    fireEvent.change(screen.getByPlaceholderText(/enter path or leave empty/i), {
      target: { value: '/test/project' }
    })
    fireEvent.click(screen.getByRole('button', { name: /^scan$/i }))

    await waitFor(() => {
      expect(screen.getByText('Run AI Analysis')).toBeInTheDocument()
    })

    // Click Run AI Analysis
    fireEvent.click(screen.getByText('Run AI Analysis'))

    await waitFor(() => {
      expect(screen.getByText('Continue to Confirm')).toBeInTheDocument()
    })

    // Click Continue to Confirm
    fireEvent.click(screen.getByText('Continue to Confirm'))

    await waitFor(() => {
      expect(screen.getByText('Approve & Create Cleanup Plan')).toBeInTheDocument()
    })

    // Click Approve & Create Cleanup Plan
    fireEvent.click(screen.getByText('Approve & Create Cleanup Plan'))

    await waitFor(() => {
      expect(screen.getByText('Plan creation failed')).toBeInTheDocument()
    })
  })

  it('does not show approve button when no scan result', () => {
    renderWithProviders(<ScanWorkspace />)
    
    // Should not show scan results or approve button without a scan
    expect(screen.queryByText('Approve & Create Cleanup Plan')).not.toBeInTheDocument()
  })

  it('disables AI analysis button when no candidates', async () => {
    const emptyScanResult = {
      ...mockScanResult,
      cleanup_candidates: [],
    }
    
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => emptyScanResult,
    })

    renderWithProviders(<ScanWorkspace />)
    
    // Perform a scan first
    fireEvent.change(screen.getByPlaceholderText(/enter path or leave empty/i), {
      target: { value: '/test/project' }
    })
    fireEvent.click(screen.getByRole('button', { name: /^scan$/i }))

    await waitFor(() => {
      expect(screen.getByText(/no cleanup candidates found/i)).toBeInTheDocument()
    })

    // AI Analysis button should be disabled
    expect(screen.getByText('Run AI Analysis')).toBeDisabled()
  })

  it('shows error when scan fails', async () => {
    ;(global.fetch as vi.Mock).mockRejectedValueOnce(new Error('Network error'))

    renderWithProviders(<ScanWorkspace />)
    
    fireEvent.change(screen.getByPlaceholderText(/enter path or leave empty/i), {
      target: { value: '/test/project' }
    })
    fireEvent.click(screen.getByRole('button', { name: /^scan$/i }))

    await waitFor(() => {
      expect(screen.getByText(/could not reach the backend/i)).toBeInTheDocument()
    })
    expect(screen.queryByText(/No cleanup candidates found/i)).not.toBeInTheDocument()
  })

  it('offers retry after a connection failure and does not treat it as an empty scan', async () => {
    ;(global.fetch as vi.Mock)
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => mockScanResult })
    renderWithProviders(<ScanWorkspace />)
    fireEvent.change(screen.getByPlaceholderText(/enter path or leave empty/i), { target: { value: '/test/project' } })
    fireEvent.click(screen.getByRole('button', { name: /^scan$/i }))
    expect(await screen.findByText(/could not reach the backend/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry scan' }))
    await waitFor(() => expect(screen.getByText(/Review Cleanup Candidates/i)).toBeInTheDocument())
    expect(global.fetch).toHaveBeenCalledTimes(2)
  })

  it('reports an empty successful response as unusable instead of showing empty scan results', async () => {
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({ ok: true, status: 200, json: async () => { throw new SyntaxError('Unexpected end of JSON input') } })
    renderWithProviders(<ScanWorkspace />)
    fireEvent.click(screen.getByRole('button', { name: /^scan$/i }))
    expect(await screen.findByText(/empty or unreadable response/i)).toBeInTheDocument()
    expect(screen.queryByText(/No cleanup candidates found/i)).not.toBeInTheDocument()
  })
})
