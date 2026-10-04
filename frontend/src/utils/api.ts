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

export async function requestJson<T>(endpoint: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(endpoint, init)
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
