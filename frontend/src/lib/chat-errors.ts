import { ApiError } from '@/lib/http'

export type ClassifiedChatError = {
  title: string
  message: string
  showLoginLink: boolean
}

const NETWORK_ERROR: ClassifiedChatError = {
  title: 'Connection problem',
  message: "Can't reach the server. Check your connection and that the backend is running.",
  showLoginLink: false,
}

const AUTH_ERROR: ClassifiedChatError = {
  title: 'Session expired',
  message: 'Your sign-in session has expired. Please sign in again.',
  showLoginLink: true,
}

function includesAny(text: string, needles: string[]): boolean {
  const lower = text.toLowerCase()
  return needles.some((needle) => lower.includes(needle))
}

// Stream errors arrive as plain Errors: the AI SDK transport throws the raw response body for
// HTTP failures, and the backend's `error` chunks carry the orchestrator's message text.
export function classifyChatError(error: Error): ClassifiedChatError {
  if (error instanceof ApiError) {
    if (error.isNetworkError) return NETWORK_ERROR
    if (error.status === 401) return AUTH_ERROR
    if (error.status === 403 || error.status === 404) {
      return {
        title: 'Conversation unavailable',
        message: 'This conversation does not exist or you do not have access to it.',
        showLoginLink: false,
      }
    }
  }

  const text = error.message || ''
  if (includesAny(text, ['invalid or expired token', 'missing bearer token'])) return AUTH_ERROR
  if (includesAny(text, ['failed to fetch', 'load failed', 'networkerror'])) return NETWORK_ERROR
  if (includesAny(text, ['could not verify the answer'])) {
    return { title: 'Answer not verified', message: text, showLoginLink: false }
  }
  if (includesAny(text, ['could not complete this answer'])) {
    return { title: 'Search failed', message: text, showLoginLink: false }
  }
  return {
    title: 'Something went wrong',
    message: text || 'Something went wrong while sending your message. Please try again.',
    showLoginLink: false,
  }
}
