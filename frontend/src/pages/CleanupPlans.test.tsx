import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { CleanupPlans } from '../pages/CleanupPlans'
import { MemoryRouter } from 'react-router-dom'
import { setMockContext } from '../test/setup'

const mockCurrentProject = {
  project_path: '/test/project',
  project_type: 'node',
  framework: 'react',
  package_manager: 'npm',
  language: 'typescript',
  has_git: true,
  git_clean: true,
}

const mockPlan = {
  plan_id: 'test-plan-123',
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
      regeneration_command: 'npm install',
    },
    {
      path: 'cache',
      action: 'DELETE',
      risk: 'CAUTION',
      scanner_risk: 'SAFE',
      ai_risk: 'CAUTION',
      effective_risk: 'CAUTION',
      reason: 'Cache files may have performance impact',
      estimated_bytes: 20000000,
    },
  ],
  total_safe_bytes: 100000000,
  total_caution_bytes: 20000000,
  total_dangerous_bytes: 0,
  requires_approval: true,
  warnings: ['CAUTION items require explicit approval'],
  verification_steps: [
    'Protected paths excluded from plan',
    'DANGEROUS items blocked',
    'Risk levels validated',
  ],
}

function renderWithProviders(ui: React.ReactElement, project = mockCurrentProject) {
  // Set the mock context with the current project
  setMockContext({ currentProject: project, aiProvider: 'nebius', aiModel: 'nvidia/nemotron-3-super-120b-a12b', realInferenceAvailable: true })
  
  return render(
    <MemoryRouter initialEntries={['/plans']}>
      {ui}
    </MemoryRouter>
  )
}

describe('CleanupPlans', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(global.fetch as vi.Mock).mockReset()
    // Reset to default mock context
    setMockContext({})
  })

  it('shows "No project selected" when no currentProject', () => {
    renderWithProviders(<CleanupPlans />, null)
    
    expect(screen.getByText('No project selected')).toBeInTheDocument()
    expect(screen.getByText('Generate Plan')).toBeInTheDocument()
  })

  it('shows "Generate Cleanup Plan with AI" button when project exists but no plan', () => {
    renderWithProviders(<CleanupPlans />, mockCurrentProject)
    
    expect(screen.getByText('Nebius configured (nvidia/nemotron-3-super-120b-a12b)')).toBeInTheDocument()
    expect(screen.getByText('Generate Cleanup Plan with AI')).toBeInTheDocument()
  })

  it('labels mock mode and disables plan generation without Nebius', () => {
    setMockContext({ currentProject: mockCurrentProject, aiProvider: 'mock', aiModel: 'devsweep-demo', realInferenceAvailable: false })
    render(<MemoryRouter initialEntries={['/plans']}><CleanupPlans /></MemoryRouter>)

    expect(screen.getByText('Mock/demo provider (mock)')).toBeInTheDocument()
    expect(screen.getByText('Generate Cleanup Plan with AI')).toBeDisabled()
  })

  it('calls /api/cleanup/generate-plan when Generate Plan is clicked', async () => {
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockPlan,
    })

    renderWithProviders(<CleanupPlans />, mockCurrentProject)
    
    fireEvent.click(screen.getByText('Generate Cleanup Plan with AI'))

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/cleanup/generate-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_path: '/test/project' }),
      })
    })

    await waitFor(() => {
      expect(screen.getByText('Cleanup Plan for project')).toBeInTheDocument()
    })
  })

  it('displays plan items with correct risk badges', async () => {
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockPlan,
    })

    renderWithProviders(<CleanupPlans />, mockCurrentProject)
    
    fireEvent.click(screen.getByText('Generate Cleanup Plan with AI'))

    await waitFor(() => {
      expect(screen.getByText('node_modules')).toBeInTheDocument()
      expect(screen.getByText('cache')).toBeInTheDocument()
    })

    // Check risk badges
    expect(screen.getByText('SAFE')).toBeInTheDocument()
    expect(screen.getByText('CAUTION')).toBeInTheDocument()
  })

  it('shows scanner → AI risk upgrade indicator', async () => {
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockPlan,
    })

    renderWithProviders(<CleanupPlans />, mockCurrentProject)
    
    fireEvent.click(screen.getByText('Generate Cleanup Plan with AI'))

    await waitFor(() => {
      expect(screen.getByText('SAFE → CAUTION')).toBeInTheDocument()
    })
  })

  it('disables execute button until approval checkbox is checked', async () => {
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockPlan,
    })

    renderWithProviders(<CleanupPlans />, mockCurrentProject)
    
    fireEvent.click(screen.getByText('Generate Cleanup Plan with AI'))

    await waitFor(() => {
      const executeBtn = screen.getByText('Approve & Execute Cleanup')
      expect(executeBtn).toBeDisabled()
    })

    // Check the checkbox
    fireEvent.click(screen.getByLabelText(/I understand this will delete/i))

    await waitFor(() => {
      const executeBtn = screen.getByText('Approve & Execute Cleanup')
      expect(executeBtn).not.toBeDisabled()
    })
  })

  it('shows error when generate plan fails', async () => {
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'AI analysis failed' }),
    })

    renderWithProviders(<CleanupPlans />, mockCurrentProject)
    
    fireEvent.click(screen.getByText('Generate Cleanup Plan with AI'))

    await waitFor(() => {
      expect(screen.getByText('AI analysis failed')).toBeInTheDocument()
    })
  })

  it('shows error when execution fails', async () => {
    ;(global.fetch as vi.Mock)
      .mockResolvedValueOnce({ ok: true, json: async () => mockPlan })
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Execution failed: permission denied' }),
      })

    renderWithProviders(<CleanupPlans />, mockCurrentProject)
    
    fireEvent.click(screen.getByText('Generate Cleanup Plan with AI'))

    await waitFor(() => {
      expect(screen.getByText('Approve & Execute Cleanup')).toBeInTheDocument()
    })

    // Check approval checkbox
    fireEvent.click(screen.getByLabelText(/I understand this will delete/i))

    fireEvent.click(screen.getByText('Approve & Execute Cleanup'))

    await waitFor(() => {
      expect(screen.getByText('Execution failed: permission denied')).toBeInTheDocument()
    })
  })
})
