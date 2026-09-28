import { env } from '@/lib/env'

const DEFAULT_TIMEOUT_MS = 30_000

export class ApiError extends Error {
  readonly status: number | null
  // True when no HTTP response arrived: offline, DNS, CORS rejection, or timeout.
  readonly isNetworkError: boolean
  readonly isTimeout: boolean
  readonly body: unknown

  constructor(
    message: string,
    options: { status?: number; isNetworkError?: boolean; isTimeout?: boolean; body?: unknown } = {},
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = options.status ?? null
    this.isNetworkError = options.isNetworkError ?? false
    this.isTimeout = options.isTimeout ?? false
    this.body = options.body
  }
}

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export type RequestOptions = {
  body?: unknown
  accessToken?: string | null
  signal?: AbortSignal
  timeoutMs?: number
}

function errorMessage(body: unknown, fallback: string): string {
  // FastAPI errors look like {"detail": "..."}; validation errors carry a list instead.
  if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') {
    return body.detail
  }
  return fallback
}

async function readBody(response: Response): Promise<unknown> {
  const text = await response.text()
  if (!text) return undefined
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

export async function request<T>(
  method: HttpMethod,
  path: string,
  { body, accessToken, signal, timeoutMs = DEFAULT_TIMEOUT_MS }: RequestOptions = {},
): Promise<T> {
  const headers = new Headers({ Accept: 'application/json' })
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  if (body !== undefined) headers.set('Content-Type', 'application/json')

  const timeoutSignal = AbortSignal.timeout(timeoutMs)
  let response: Response
  try {
    response = await fetch(`${env.apiBaseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: signal ? AbortSignal.any([signal, timeoutSignal]) : timeoutSignal,
    })
  } catch (error) {
    // A caller-initiated abort is not an API failure; let the caller handle it.
    if (signal?.aborted) throw error
    if (timeoutSignal.aborted) {
      throw new ApiError(`Request timed out after ${timeoutMs} ms`, { isNetworkError: true, isTimeout: true })
    }
    throw new ApiError('Could not reach the server. Check your connection or the API URL/CORS settings.', {
      isNetworkError: true,
    })
  }

  const responseBody = await readBody(response)
  if (!response.ok) {
    throw new ApiError(errorMessage(responseBody, `Request failed with status ${response.status}`), {
      status: response.status,
      body: responseBody,
    })
  }
  return responseBody as T
}
