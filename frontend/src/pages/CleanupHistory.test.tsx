import { act, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CleanupHistory } from './CleanupHistory'

describe('CleanupHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(global.fetch as vi.Mock).mockReset()
  })

  it('shows persisted complete and interrupted executions with unknown outcomes', async () => {
    let resolveHistory!: (value: unknown) => void
    ;(global.fetch as vi.Mock).mockReturnValueOnce(new Promise(resolve => { resolveHistory = resolve }))
    render(<CleanupHistory />)
    expect(screen.getByRole('status')).toBeInTheDocument()
    await act(async () => resolveHistory({ ok: true, json: async () => ({ executions: [
      { execution_id: 'e1', plan_id: 'p1', project_id: 'x', started_at: '2026-01-01T00:00:00Z', ended_at: '2026-01-01T00:01:00Z', status: 'completed', approved_candidates: 1, items_processed: 1, items_deleted: 1, items_skipped: 0, items_failed: 0, items_unknown: 0, bytes_processed: 20, error_summary: '', outcomes: [], verifications: [] },
      { execution_id: 'e2', plan_id: 'p2', project_id: 'y', started_at: '2026-01-02T00:00:00Z', ended_at: null, status: 'interrupted', approved_candidates: 2, items_processed: 1, items_deleted: 1, items_skipped: 0, items_failed: 0, items_unknown: 1, bytes_processed: 20, error_summary: 'Restarted; unfinished outcomes are unknown.', outcomes: [], verifications: [] },
    ] }) }))
    expect(await screen.findByText('Complete')).toBeInTheDocument()
    expect(screen.getByText('Interrupted')).toBeInTheDocument()
    expect(screen.getAllByText('1', { selector: 'p' }).length).toBeGreaterThan(0)
    expect(screen.getByText(/Some file outcomes may be unknown/)).toBeInTheDocument()
  })

  it('shows an API error instead of a false empty-history state', async () => {
    ;(global.fetch as vi.Mock).mockResolvedValueOnce({ ok: false, status: 503, json: async () => ({ detail: 'History unavailable' }) })
    render(<CleanupHistory />)
    expect(await screen.findByText('History unavailable')).toBeInTheDocument()
    expect(screen.queryByText('No cleanup executions recorded')).not.toBeInTheDocument()
  })
})
