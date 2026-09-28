import { request, type HttpMethod, type RequestOptions } from '@/lib/http'
import { supabase } from '@/lib/supabase'

type Options = Omit<RequestOptions, 'body' | 'accessToken'>

export type CurrentUser = {
  id: string
  email: string
}

// Exported for callers that don't go through `api`, e.g. the AI SDK chat transport.
export async function getAccessToken(): Promise<string | null> {
  // getSession refreshes an expired access token before returning it.
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}

async function withAuth<T>(method: HttpMethod, path: string, options: RequestOptions = {}): Promise<T> {
  return request<T>(method, path, { ...options, accessToken: await getAccessToken() })
}

export const api = {
  get: <T>(path: string, options?: Options) => withAuth<T>('GET', path, options),
  post: <T>(path: string, body?: unknown, options?: Options) => withAuth<T>('POST', path, { ...options, body }),
  put: <T>(path: string, body?: unknown, options?: Options) => withAuth<T>('PUT', path, { ...options, body }),
  patch: <T>(path: string, body?: unknown, options?: Options) => withAuth<T>('PATCH', path, { ...options, body }),
  delete: <T>(path: string, options?: Options) => withAuth<T>('DELETE', path, options),

  getCurrentUser: () => withAuth<CurrentUser>('GET', '/auth/me'),
}
