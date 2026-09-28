import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { ChatView } from '@/components/chat/ChatView'
import { getThreadMessages, type UIMessage } from '@/lib/chat'
import { ApiError } from '@/lib/http'

type LoadState =
  | { threadId: string; status: 'ready'; messages: UIMessage[] }
  | { threadId: string; status: 'error'; message: string }

function loadErrorMessage(error: unknown): string {
  if (error instanceof ApiError && (error.status === 404 || error.status === 403)) {
    return 'This conversation does not exist or you do not have access to it.'
  }
  return error instanceof Error ? error.message : String(error)
}

export function ChatThreadPage() {
  const { threadId = '' } = useParams()
  const [state, setState] = useState<LoadState | null>(null)

  useEffect(() => {
    let cancelled = false
    getThreadMessages(threadId)
      .then((messages) => !cancelled && setState({ threadId, status: 'ready', messages }))
      .catch((error: unknown) => !cancelled && setState({ threadId, status: 'error', message: loadErrorMessage(error) }))
    return () => {
      cancelled = true
    }
  }, [threadId])

  // Ignore a result that belongs to the previously opened thread.
  if (!state || state.threadId !== threadId) {
    return <p className="p-4 text-muted-foreground">Loading conversation…</p>
  }
  if (state.status === 'error') {
    return (
      <p role="alert" className="p-4 text-destructive">
        {state.message}
      </p>
    )
  }
  // Keyed so switching threads starts a fresh useChat instance with that thread's history.
  return <ChatView key={threadId} threadId={threadId} initialMessages={state.messages} />
}
