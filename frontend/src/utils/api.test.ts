import { describe, expect, it, vi } from 'vitest'
import { apiErrorMessage, requestJson } from './api'

describe('requestJson', () => {
  it('classifies connection failures and preserves the underlying diagnostic', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(requestJson('/api/scan')).rejects.toMatchObject({
      kind: 'connection', endpoint: '/api/scan', diagnostic: 'Failed to fetch',
    })
    try { await requestJson('/api/scan') } catch (error) {
      expect(apiErrorMessage(error, 'simple')).toMatch(/backend.*retry/i)
      expect(apiErrorMessage(error, 'technical')).toContain('Failed to fetch')
    }
  })

  it.each(['empty', 'invalid'])('classifies %s JSON separately from a successful empty result', async kind => {
    const parseError = kind === 'empty' ? new SyntaxError('Unexpected end of JSON input') : new SyntaxError('Unexpected token')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json: () => Promise.reject(parseError) }))
    await expect(requestJson('/api/scan')).rejects.toMatchObject({ kind: 'invalid-response', status: 200 })
  })

  it('uses a valid API error detail and actual status', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({ detail: 'Scanner unavailable' }) }))
    await expect(requestJson('/api/scan')).rejects.toMatchObject({ kind: 'http', status: 503, message: 'Scanner unavailable' })
  })
})
