import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { setMockContext } from '../test/setup'
import type { ScanResponse } from '../types/api'
import { RestoreCenter } from './RestoreCenter'

const project: ScanResponse = {
  project_id: 'project-1', project_path: '/workspace/project', project_type: 'node', framework: 'vite',
  package_manager: 'npm', language: 'typescript', has_git: true, git_clean: true, cleanup_candidates: [],
  total_recoverable_bytes: 0, total_recoverable_human: '0 B', protected_paths: [], notes: '',
}
const backup = { backup_id: 'backup-1', execution_id: 'execution-1', project_id: 'project-1', path: 'dist', size_bytes: 8, sha256: 'a'.repeat(64), entry_count: 2, created_at: '2026-10-04T00:00:00Z', status: 'verified' }

function jsonResponse(data: unknown) {
  return { ok: true, status: 200, json: async () => data }
}

describe('RestoreCenter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.confirm = vi.fn(() => true)
    setMockContext({ currentProject: project })
  })

  it('shows only backend-provided verified backup records and restores after confirmation', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url === '/api/config') return jsonResponse({ demo_mode: false }) as Response
      if (url === '/api/ai/models') return jsonResponse({ provider_name: 'mock', model: 'mock', real_inference_available: false }) as Response
      if (url === '/api/cleanup/backups') return jsonResponse({ backups: [backup] }) as Response
      if (url.startsWith('/api/cleanup/backups/backup-1?')) return jsonResponse({ ...backup, offset: 0, limit: 100, has_more: false, entries: [{ path: '.', type: 'directory', size: 0 }, { path: 'index.html', type: 'file', size: 8, sha256: 'a'.repeat(64) }] }) as Response
      if (url === '/api/cleanup/restore/history') return jsonResponse({ restores: [] }) as Response
      if (url === '/api/cleanup/restore') {
        expect(init?.method).toBe('POST')
        expect(JSON.parse(String(init?.body))).toMatchObject({ backup_id: 'backup-1', approved: true, project_path: project.project_path })
        return jsonResponse({ restore_id: 'restore-1', status: 'completed', summary: 'Restored safely.' }) as Response
      }
      throw new Error(`Unexpected request: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<RestoreCenter />)
    expect(await screen.findByText('dist')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Review contents' }))
    expect(await screen.findByText(/full backup passed SHA-256 verification/)).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Restore dist' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Restore dist' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/cleanup/restore', expect.anything()))
    expect(await screen.findByText('Restored safely.')).toBeInTheDocument()
  })

  it('shows a real empty state when there are no verified backups', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url === '/api/config') return jsonResponse({ demo_mode: false })
      if (url === '/api/ai/models') return jsonResponse({ provider_name: 'mock', model: 'mock', real_inference_available: false })
      if (url === '/api/cleanup/backups') return jsonResponse({ backups: [] })
      if (url === '/api/cleanup/restore/history') return jsonResponse({ restores: [] })
      throw new Error(`Unexpected request: ${url}`)
    }))
    setMockContext({ currentProject: project })
    render(<RestoreCenter />)
    expect(await screen.findByText('No verified backups available')).toBeInTheDocument()
    expect(screen.queryByText(/Preview only/)).not.toBeInTheDocument()
  })
})
