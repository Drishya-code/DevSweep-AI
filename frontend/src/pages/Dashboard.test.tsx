import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { Dashboard } from './Dashboard'
import { setMockContext } from '../test/setup'

const testView = vi.hoisted(() => ({ mode: 'simple' as 'simple' | 'technical' }))
vi.mock('../context/ViewModeContext', async importOriginal => {
  const actual = await importOriginal<typeof import('../context/ViewModeContext')>()
  return { ...actual, useViewMode: () => ({ viewMode: testView.mode, setViewMode: vi.fn(), toggleViewMode: vi.fn() }) }
})

const project = {
  project_path: 'C:\\work\\demo-app', project_type: 'node', framework: 'react', package_manager: 'npm', language: 'typescript',
  has_git: true, git_clean: false,
  cleanup_candidates: [
    { path: 'dist', risk: 'SAFE' as const, reason: 'Generated build output', size_bytes: 2048, size_human: '2.0 KB' },
    { path: 'cache', risk: 'CAUTION' as const, reason: 'Review cache usage', size_bytes: 1024, size_human: '1.0 KB' },
  ],
  total_recoverable_bytes: 3072, total_recoverable_human: '3.0 KB', protected_paths: ['.git'], notes: 'Scan facts',
}

function renderPage(overrides = {}) {
  setMockContext({ currentProject: null, scanHistory: [], isScanning: false, demoMode: false, ...overrides })
  return render(<MemoryRouter><Dashboard /></MemoryRouter>)
}

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(global.fetch as vi.Mock).mockReset()
    testView.mode = 'simple'
    setMockContext({})
  })

  it('shows an empty state without inventing storage totals', () => {
    renderPage()
    expect(screen.getByText('No scan selected')).toBeInTheDocument()
    expect(screen.getByText('Scan a project to see measured candidate sizes and risks.')).toBeInTheDocument()
    expect(screen.getAllByText('—')).toHaveLength(3)
    expect(screen.queryByText('0 B')).not.toBeInTheDocument()
  })

  it('shows simple health, selected scan data and risk-based storage summary', () => {
    renderPage({ currentProject: project, scanHistory: [project] })
    expect(screen.getByText(/working tree had uncommitted changes at the time of this scan/)).toBeInTheDocument()
    expect(screen.getByText('Safe')).toBeInTheDocument()
    expect(screen.getByText('2 KB')).toBeInTheDocument()
    expect(screen.queryByText('Total Storage Used')).not.toBeInTheDocument()
  })

  it('shows technical scan detail and uses only candidate measurements', () => {
    testView.mode = 'technical'
    renderPage({ currentProject: project, scanHistory: [project] })
    expect(screen.getByText('C:\\work\\demo-app')).toBeInTheDocument()
    expect(screen.getByText('Scanned candidate details')).toBeInTheDocument()
    expect(screen.getByText('Generated build output')).toBeInTheDocument()
    expect(screen.getByText('Candidate sizes are measured by the scanner; this is not total project disk usage.')).toBeInTheDocument()
  })

  it('shows scan progress and updates context with a successful scan', async () => {
    let resolveScan!: (result: unknown) => void
    const setCurrentProject = vi.fn()
    const addScanToHistory = vi.fn()
    const setIsScanning = vi.fn()
    setMockContext({ currentProject: null, scanHistory: [], isScanning: false, demoMode: false, setCurrentProject, addScanToHistory, setIsScanning })
    ;(global.fetch as vi.Mock).mockReturnValueOnce(new Promise(resolve => { resolveScan = resolve }))
    render(<MemoryRouter><Dashboard /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: 'Scan Workspace' }))
    expect(setIsScanning).toHaveBeenCalledWith(true)
    await act(async () => { resolveScan({ ok: true, json: async () => project }) })
    await waitFor(() => {
      expect(setCurrentProject).toHaveBeenCalledWith(project)
      expect(addScanToHistory).toHaveBeenCalledWith(project)
    })
    expect(setIsScanning).toHaveBeenLastCalledWith(false)
  })

  it('renders the shared loading state while a scan is already active', () => {
    renderPage({ isScanning: true })
    expect(screen.getByRole('status')).toHaveTextContent('Scanning workspace')
  })

  it('reports scan API failures without losing the current view', async () => {
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({ ok: false, json: async () => ({ detail: 'Workspace unavailable' }) })
    renderPage({ currentProject: project })
    fireEvent.click(screen.getByRole('button', { name: 'Scan Workspace' }))
    expect(await screen.findByText('Workspace unavailable')).toBeInTheDocument()
  })

  it('links to scanning from the quick action', () => {
    renderPage()
    expect(screen.getByRole('link', { name: /Scan workspace/ })).toHaveAttribute('href', '/scan')
  })
})
