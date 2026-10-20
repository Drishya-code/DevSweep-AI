export type ApiErrorKind = 'connection' | 'invalid-response' | 'http'

export class ApiError extends Error {
  constructor(
    message: string,
    readonly kind: ApiErrorKind,
    readonly endpoint: string,
    readonly status?: number,
    readonly diagnostic?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function errorText(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}

const configuredApiBase = (import.meta as ImportMeta & { env?: { VITE_API_BASE_URL?: string; PROD?: boolean } }).env?.VITE_API_BASE_URL?.trim() || ''
const isProductionBuild = (import.meta as ImportMeta & { env?: { PROD?: boolean } }).env?.PROD === true
if (isProductionBuild && configuredApiBase) {
  let apiOrigin: URL
  try { apiOrigin = new URL(configuredApiBase) }
  catch { throw new Error('Production API configuration must be an absolute HTTPS URL.') }
  const hostname = apiOrigin.hostname.toLowerCase()
  if (apiOrigin.protocol !== 'https:' || hostname === 'localhost' || hostname.endsWith('.localhost') || hostname.startsWith('127.') || hostname === '[::1]') {
    throw new Error('Production API configuration must use a public HTTPS origin, not a local development server.')
  }
}

export function apiUrl(endpoint: string) {
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  return `${configuredApiBase.replace(/\/$/, '')}${path}`
}

export async function requestJson<T>(endpoint: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    const isDemoRequest = endpoint.startsWith('/api/demo/') && endpoint !== '/api/demo/sessions'
    const headers = new Headers(init?.headers)
    if (isDemoRequest) {
      const session = localStorage.getItem('devsweep-demo-session')
      if (session) headers.set('X-DevSweep-Session', session)
    }
    const requestInit = isDemoRequest || init?.headers ? { ...init, headers } : init
    response = await fetch(apiUrl(endpoint), requestInit)
  } catch (error) {
    throw new ApiError('DevSweep could not reach the backend. Check that it is running, then retry.', 'connection', endpoint, undefined, errorText(error))
  }

  let data: unknown
  try {
    data = await response.json()
  } catch (error) {
    throw new ApiError(
      'The backend returned an empty or unreadable response. Check the backend and retry.',
      'invalid-response', endpoint, response.status, errorText(error),
    )
  }

  if (!response.ok) {
    const detail = data && typeof data === 'object' && 'detail' in data && typeof data.detail === 'string'
      ? data.detail
      : `The backend rejected the request (HTTP ${response.status}).`
    throw new ApiError(detail, 'http', endpoint, response.status)
  }
  return data as T
}

export function apiErrorMessage(error: unknown, viewMode: 'simple' | 'technical'): string {
  if (!(error instanceof ApiError)) return errorText(error) || 'The request failed. Please retry.'
  if (viewMode === 'simple') return error.message
  const status = error.status === undefined ? '' : ` · HTTP ${error.status}`
  const diagnostic = error.diagnostic ? ` · ${error.diagnostic}` : ''
  return `${error.message} (${error.endpoint}${status}${diagnostic})`
}
