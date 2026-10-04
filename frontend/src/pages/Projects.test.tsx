import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { Projects } from './Projects'
import { mockNavigate, setMockContext } from '../test/setup'

const testView = vi.hoisted(() => ({ mode: 'simple' as 'simple' | 'technical' }))
vi.mock('../context/ViewModeContext', async importOriginal => {
  const actual = await importOriginal<typeof import('../context/ViewModeContext')>()
  return { ...actual, useViewMode: () => ({ viewMode: testView.mode, setViewMode: vi.fn(), toggleViewMode: vi.fn() }) }
})

const project = {
  project_path: 'C:\\work\\demo-app', project_type: 'node', framework: 'react', package_manager: 'npm', language: 'typescript',
  has_git: true, git_clean: true,
  cleanup_candidates: [{ path: 'dist', risk: 'SAFE' as const, reason: 'Build files', size_bytes: 2048, size_human: '2.0 KB' }],
  total_recoverable_bytes: 2048, total_recoverable_human: '2.0 KB', protected_paths: ['.git', '.env'], notes: 'Latest scanner note',
}

function renderPage(overrides = {}) {
  setMockContext({ scanHistory: [project], currentProject: null, ...overrides })
  return render(<MemoryRouter><Projects /></MemoryRouter>)
}

describe('Projects', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(global.fetch as vi.Mock).mockReset()
    ;(global.fetch as vi.Mock).mockImplementation((url: string) => url === '/api/cleanup/history/projects'
      ? Promise.resolve({ ok: true, json: async () => ({ projects: [] }) })
      : Promise.resolve(undefined))
    testView.mode = 'simple'
    setMockContext({})
  })

  it('shows an empty state and navigates to scanning when no projects have been scanned', () => {
    renderPage({ scanHistory: [] })
    expect(screen.getByText('No projects scanned yet')).toBeInTheDocument()
    const scanAction = screen.getByRole('button', { name: 'Scan a project' })
    expect(scanAction.parentElement).toHaveClass('justify-center')
    fireEvent.click(scanAction)
    expect(mockNavigate).toHaveBeenCalledWith('/scan')
  })

  it('shows simple project cards with scan status and selection state', () => {
    renderPage({ currentProject: project, scanHistory: [project, { ...project, framework: 'old' }] })
    expect(screen.getByRole('heading', { name: 'demo-app' })).toBeInTheDocument()
    expect(screen.getByText('C:\\work\\demo-app')).toBeInTheDocument()
    expect(screen.getByText('Git working tree was clean at scan time.')).toBeInTheDocument()
    expect(screen.getByText('Selected')).toBeInTheDocument()
    expect(screen.getAllByText('react')).toHaveLength(1)
  })

  it('shows technical metadata and protected paths in Technical View', () => {
    testView.mode = 'technical'
    renderPage({ currentProject: project })
    expect(screen.getByText('Technical details reflect scan responses only. Paths are refreshed before selection; inaccessible paths return an error and are not selected.')).toBeInTheDocument()
    expect(screen.getByText('Protected paths detected')).toBeInTheDocument()
    expect(screen.getByText('.git, .env')).toBeInTheDocument()
    expect(screen.getByText('Latest scanner note')).toBeInTheDocument()
  })

  it('refreshes and selects an accessible project, then navigates to the dashboard', async () => {
    const setCurrentProject = vi.fn()
    const addScanToHistory = vi.fn()
    renderPage({ setCurrentProject, addScanToHistory })
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({ ok: true, json: async () => ({ ...project, git_clean: false }) })
    fireEvent.click(screen.getByRole('button', { name: 'Refresh & select' }))
    await waitFor(() => {
      expect(setCurrentProject).toHaveBeenCalledWith({ ...project, git_clean: false })
      expect(addScanToHistory).toHaveBeenCalledWith({ ...project, git_clean: false })
      expect(mockNavigate).toHaveBeenCalledWith('/')
    })
    expect(global.fetch).toHaveBeenCalledWith('/api/scan', expect.objectContaining({ method: 'POST', body: JSON.stringify({ path: project.project_path }) }))
  })

  it('reports missing or inaccessible project paths and leaves selection unchanged', async () => {
    const setCurrentProject = vi.fn()
    renderPage({ currentProject: null, setCurrentProject })
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({ ok: false, status: 404, json: async () => ({ detail: 'Path not found: C:\\work\\demo-app' }) })
    fireEvent.click(screen.getByRole('button', { name: 'Refresh & select' }))
    expect(await screen.findByText('Path not found: C:\\work\\demo-app')).toBeInTheDocument()
    expect(screen.getByText('demo-app')).toBeInTheDocument()
    expect(setCurrentProject).not.toHaveBeenCalled()
    expect(mockNavigate).not.toHaveBeenCalledWith('/')
  })

  it('shows loading while a path is checked', async () => {
    let resolveScan!: (result: unknown) => void
    renderPage()
    ;(global.fetch as vi.Mock).mockReturnValueOnce(new Promise(resolve => { resolveScan = resolve }))
    fireEvent.click(screen.getByRole('button', { name: 'Refresh & select' }))
    expect(screen.getAllByRole('status').some(status => status.textContent?.includes('Checking access and refreshing C:\\work\\demo-app'))).toBe(true)
    await act(async () => { resolveScan({ ok: true, json: async () => project }) })
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
