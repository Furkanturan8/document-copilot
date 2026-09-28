import { DefaultChatTransport, type UIMessage } from 'ai'

import { api, getAccessToken } from '@/lib/api'
import { env } from '@/lib/env'

export type { UIMessage }

export type ThreadSummary = {
  id: string
  title: string
  createdAt: string
  updatedAt: string
}

export async function listThreads(): Promise<ThreadSummary[]> {
  const response = await api.get<{ threads: ThreadSummary[] }>('/chat/threads')
  return response.threads
}

export async function createThread(): Promise<ThreadSummary> {
  return api.post<ThreadSummary>('/chat/threads', {})
}

export async function deleteThread(threadId: string): Promise<void> {
  await api.delete<void>(`/chat/threads/${threadId}`)
}

export async function getThreadMessages(threadId: string): Promise<UIMessage[]> {
  const response = await api.get<{ messages: UIMessage[] }>(`/chat/threads/${threadId}/messages`)
  return response.messages
}

// Streams bypass the `api` client (the AI SDK owns that fetch), so the token is attached here.
export function createChatTransport(): DefaultChatTransport<UIMessage> {
  return new DefaultChatTransport({
    api: `${env.apiBaseUrl}/chat/stream`,
    headers: async (): Promise<Record<string, string>> => {
      const token = await getAccessToken()
      return token ? { Authorization: `Bearer ${token}` } : {}
    },
    // The backend loads history from the database, so only the new message is sent.
    prepareSendMessagesRequest: ({ id, messages }) => ({
      body: { threadId: id, messages: messages.slice(-1) },
    }),
  })
}

export function messageText(message: UIMessage): string {
  return message.parts.map((part) => (part.type === 'text' ? part.text : '')).join('')
}
