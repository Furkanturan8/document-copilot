import { useCallback, useEffect, useState, type ReactNode } from 'react'

import { ThreadsContext } from '@/components/chat/threads-context'
import * as chat from '@/lib/chat'
import type { ThreadSummary } from '@/lib/chat'

export function ThreadsProvider({ children }: { children: ReactNode }) {
  const [threads, setThreads] = useState<ThreadSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refreshThreads = useCallback(async () => {
    try {
      setThreads(await chat.listThreads())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial fetch; state is set after the await
    void refreshThreads()
  }, [refreshThreads])

  const createThread = useCallback(async () => {
    const thread = await chat.createThread()
    setThreads((current) => [thread, ...current])
    return thread
  }, [])

  const deleteThread = useCallback(async (threadId: string) => {
    await chat.deleteThread(threadId)
    setThreads((current) => current.filter((thread) => thread.id !== threadId))
  }, [])

  return (
    <ThreadsContext.Provider value={{ threads, isLoading, error, refreshThreads, createThread, deleteThread }}>
      {children}
    </ThreadsContext.Provider>
  )
}
