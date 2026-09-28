import { createContext, useContext } from 'react'

import type { ThreadSummary } from '@/lib/chat'

export type ThreadsState = {
  threads: ThreadSummary[]
  isLoading: boolean
  error: string | null
  refreshThreads: () => Promise<void>
  createThread: () => Promise<ThreadSummary>
  deleteThread: (threadId: string) => Promise<void>
}

export const ThreadsContext = createContext<ThreadsState | null>(null)

export function useThreads(): ThreadsState {
  const value = useContext(ThreadsContext)
  if (!value) throw new Error('useThreads must be used inside <ThreadsProvider>')
  return value
}
