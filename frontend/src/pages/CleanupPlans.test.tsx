import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { CleanupPlans } from '../pages/CleanupPlans'
import { MemoryRouter } from 'react-router-dom'
import { setMockContext } from '../test/setup'

const testView = vi.hoisted(() => ({ mode: 'simple' as 'simple' | 'technical' }))
vi.mock('../context/ViewModeContext', async importOriginal => {
  const actual = await importOriginal<typeof import('../context/ViewModeContext')>()
  return { ...actual, useViewMode: () => ({ viewMode: testView.mode, setViewMode: vi.fn(), toggleViewMode: vi.fn() }) }
})

const mockCurrentProject = {
  project_path: '/test/project', project_type: 'node', framework: 'react', package_manager: 'npm', language: 'typescript', has_git: true, git_clean: true,
}
const mockPlan = {
  plan_id: 'test-plan-123',
  items: [
    { path: 'node_modules', action: 'DELETE', risk: 'SAFE', scanner_risk: 'SAFE', ai_risk: 'SAFE', effective_risk: 'SAFE', reason: 'Regenerable using package-lock.json', estimated_bytes: 100000000, regeneration_command: 'npm install' },
    { path: 'cache', action: 'DELETE', risk: 'CAUTION', scanner_risk: 'SAFE', ai_risk: 'CAUTION', effective_risk: 'CAUTION', reason: 'Cache files may have performance impact', estimated_bytes: 20000000 },
  ],
  total_safe_bytes: 100000000, total_caution_bytes: 20000000, total_dangerous_bytes: 0, requires_approval: true,
  warnings: ['CAUTION items require explicit approval'], verification_steps: ['Protected paths excluded from plan', 'DANGEROUS items blocked', 'Risk levels validated'],
}
const successfulExecution = { success: true, items_processed: 2, items_deleted: 2, items_failed: 0, bytes_freed: 120000000, bytes_freed_human: '114.4 MB', errors: [], duration_seconds: 0.2 }
const passedVerification = { passed: true, checks: [{ name: 'Protected files', passed: true, message: 'Intact' }], errors: [] }

function renderWithProviders(ui: React.ReactElement, project: typeof mockCurrentProject | null = mockCurrentProject) {
  setMockContext({ currentProject: project, currentPlan: null, aiProvider: 'nebius', aiModel: 'nvidia/nemotron-3-super-120b-a12b', realInferenceAvailable: true })
  return render(<MemoryRouter initialEntries={['/plans']}>{ui}</MemoryRouter>)
}
function queuePlan() {
  ;(global.fetch as vi.Mock).mockResolvedValueOnce({ ok: true, json: async () => mockPlan })
}
async function createPlan() {
  fireEvent.click(screen.getByRole('button', { name: 'Generate Cleanup Plan with AI' }))
  await screen.findByText('Review plan for project')
}
async function approvePlan() {
  fireEvent.click(screen.getByLabelText(/I reviewed the listed items/))
  fireEvent.click(screen.getByRole('button', { name: 'Approve & Execute Cleanup' }))
}

describe('CleanupPlans', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(global.fetch as vi.Mock).mockReset()
    setMockContext({})
    testView.mode = 'simple'
  })

  it('shows an empty state without a selected project', () => {
    renderWithProviders(<CleanupPlans />, null)
    expect(screen.getByText('No project selected')).toBeInTheDocument()
  })

  it('labels mock mode and disables plan generation without Nebius', () => {
    setMockContext({ currentProject: mockCurrentProject, aiProvider: 'mock', aiModel: 'devsweep-demo', realInferenceAvailable: false })
    render(<MemoryRouter><CleanupPlans /></MemoryRouter>)
    expect(screen.getByText('Mock/demo provider (mock)')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate Cleanup Plan with AI' })).toBeDisabled()
  })

  it('generates and reviews a plan with actual backend summary and items', async () => {
    queuePlan()
    renderWithProviders(<CleanupPlans />)
    await createPlan()
    expect(global.fetch).toHaveBeenCalledWith('/api/cleanup/generate-plan', expect.objectContaining({ method: 'POST', body: JSON.stringify({ project_path: '/test/project' }) }))
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('node_modules')).toBeInTheDocument()
    expect(screen.getByText('cache')).toBeInTheDocument()
    expect(screen.getByText(/1 caution item\(s\) require your explicit approval/)).toBeInTheDocument()
  })

  it('shows scanner, AI and effective risks plus regeneration details in Technical View', async () => {
    testView.mode = 'technical'
    queuePlan()
    renderWithProviders(<CleanupPlans />)
    await createPlan()
    expect(screen.getAllByText(/Scanner: Safe/)).toHaveLength(2)
    expect(screen.getByText(/AI: Caution/)).toBeInTheDocument()
    expect(screen.getByText('npm install')).toBeInTheDocument()
    expect(screen.getByText('Review plan for project')).toBeInTheDocument()
  })

  it('allows canceling before execution and returns to plan generation', async () => {
    queuePlan()
    renderWithProviders(<CleanupPlans />)
    await createPlan()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel and return' }))
    expect(screen.getByRole('button', { name: 'Generate Cleanup Plan with AI' })).toBeInTheDocument()
    expect(global.fetch).toHaveBeenCalledTimes(1)
  })

  it('does not generate plans when generation fails', async () => {
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({ ok: false, json: async () => ({ detail: 'AI analysis failed' }) })
    renderWithProviders(<CleanupPlans />)
    fireEvent.click(screen.getByRole('button', { name: 'Generate Cleanup Plan with AI' }))
    expect(await screen.findByText('AI analysis failed')).toBeInTheDocument()
  })

  it('requires explicit approval before execution', async () => {
    queuePlan()
    renderWithProviders(<CleanupPlans />)
    await createPlan()
    expect(screen.getByRole('button', { name: 'Approve & Execute Cleanup' })).toBeDisabled()
    fireEvent.click(screen.getByLabelText(/I reviewed the listed items/))
    expect(screen.getByRole('button', { name: 'Approve & Execute Cleanup' })).toBeEnabled()
  })

  it('blocks execution for a dangerous deletion', async () => {
    const dangerousPlan = { ...mockPlan, items: [{ ...mockPlan.items[0], risk: 'DANGEROUS', effective_risk: 'DANGEROUS' }] }
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({ ok: true, json: async () => dangerousPlan })
    renderWithProviders(<CleanupPlans />)
    await createPlan()
    expect(screen.getByText('This plan includes a dangerous deletion. Execution is blocked.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Approve & Execute Cleanup' })).toBeDisabled()
  })

  it('reports complete execution only when all planned items were deleted and verification passed', async () => {
    queuePlan()
    renderWithProviders(<CleanupPlans />)
    await createPlan()
    ;(global.fetch as vi.Mock)
      .mockResolvedValueOnce({ ok: true, json: async () => successfulExecution })
      .mockResolvedValueOnce({ ok: true, json: async () => passedVerification })
    await approvePlan()
    expect(await screen.findByText('Execution complete')).toBeInTheDocument()
    expect(screen.getByText('Verification passed')).toBeInTheDocument()
    expect(global.fetch).toHaveBeenCalledTimes(3)
    expect(global.fetch).not.toHaveBeenCalledWith('/api/demo/reset', expect.anything())
  })

  it('distinguishes partial execution and verification failure', async () => {
    queuePlan()
    renderWithProviders(<CleanupPlans />)
    await createPlan()
    ;(global.fetch as vi.Mock)
      .mockResolvedValueOnce({ ok: true, json: async () => ({ ...successfulExecution, success: false, items_deleted: 1, items_failed: 1, errors: ['cache: permission denied'] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ ...passedVerification, passed: false, checks: [{ name: 'Build', passed: false, message: 'Failed' }] }) })
    await approvePlan()
    expect(await screen.findByText('Execution partially completed')).toBeInTheDocument()
    expect(screen.getByText('Verification found issues')).toBeInTheDocument()
    expect(screen.getByText('cache: permission denied')).toBeInTheDocument()
  })

  it('distinguishes execution failure even when the HTTP request succeeds', async () => {
    queuePlan()
    renderWithProviders(<CleanupPlans />)
    await createPlan()
    ;(global.fetch as vi.Mock)
      .mockResolvedValueOnce({ ok: true, json: async () => ({ ...successfulExecution, success: false, items_deleted: 0, items_failed: 2, errors: ['deletion failed'] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ ...passedVerification, passed: false }) })
    await approvePlan()
    expect(await screen.findByText('Execution failed')).toBeInTheDocument()
    expect(screen.getByText('Verification found issues')).toBeInTheDocument()
  })

  it('reports verification request errors without fabricating a result', async () => {
    queuePlan()
    renderWithProviders(<CleanupPlans />)
    await createPlan()
    ;(global.fetch as vi.Mock)
      .mockResolvedValueOnce({ ok: true, json: async () => successfulExecution })
      .mockResolvedValueOnce({ ok: false, json: async () => ({ detail: 'Snapshot unavailable' }) })
    await approvePlan()
    expect(await screen.findByText('Verification unavailable')).toBeInTheDocument()
    expect(screen.getByText('Snapshot unavailable')).toBeInTheDocument()
    expect(screen.getByText('Execution complete')).toBeInTheDocument()
  })

  it('reports malformed verification data as unavailable, not a completed failure', async () => {
    queuePlan()
    renderWithProviders(<CleanupPlans />)
    await createPlan()
    ;(global.fetch as vi.Mock)
      .mockResolvedValueOnce({ ok: true, json: async () => successfulExecution })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ passed: false }) })
    await approvePlan()
    expect(await screen.findByText('Verification unavailable')).toBeInTheDocument()
    expect(screen.getByText('Verification returned an unusable response')).toBeInTheDocument()
    expect(screen.getByText('Execution complete')).toBeInTheDocument()
  })

  it('reports execution HTTP errors and does not claim cleanup occurred', async () => {
    queuePlan()
    renderWithProviders(<CleanupPlans />)
    await createPlan()
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({ ok: false, json: async () => ({ detail: 'Execution rejected' }) })
    await approvePlan()
    expect(await screen.findByText('Execution rejected')).toBeInTheDocument()
    expect(screen.queryByText('Execution complete')).not.toBeInTheDocument()
    expect(global.fetch).toHaveBeenCalledTimes(2)
  })

  it('prevents duplicate execution submissions while a request is in flight', async () => {
    queuePlan()
    renderWithProviders(<CleanupPlans />)
    await createPlan()
    let resolveExecution!: (value: unknown) => void
    ;(global.fetch as vi.Mock).mockReturnValueOnce(new Promise(resolve => { resolveExecution = resolve }))
    fireEvent.click(screen.getByLabelText(/I reviewed the listed items/))
    const execute = screen.getByRole('button', { name: 'Approve & Execute Cleanup' })
    fireEvent.click(execute)
    fireEvent.click(execute)
    expect(screen.getByText(/cannot be cancelled from the application/)).toBeInTheDocument()
    expect(global.fetch).toHaveBeenCalledTimes(2)
    resolveExecution({ ok: true, json: async () => successfulExecution })
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({ ok: true, json: async () => passedVerification })
    await screen.findByText('Execution complete')
  })
})
