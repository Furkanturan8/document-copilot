import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import { ChatView } from '@/components/chat/ChatView'
import { Button } from '@/components/ui/button'
import { Loader } from '@/components/ui/loader'
import { classifyChatError } from '@/lib/chat-errors'
import { getThreadMessages, type UIMessage } from '@/lib/chat'

type LoadState =
  | { status: 'ready'; messages: UIMessage[] }
  | { status: 'error'; error: Error }

export function ChatThreadPage() {
  const { threadId = '' } = useParams()
  // Keyed so each thread gets its own load state and its own navigation prompt.
  return <ThreadLoader key={threadId} threadId={threadId} />
}

function ThreadLoader({ threadId }: { threadId: string }) {
  const location = useLocation()
  const navigate = useNavigate()
  const [state, setState] = useState<LoadState | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [initialPrompt] = useState(() => (location.state as { initialPrompt?: string } | null)?.initialPrompt)

  useEffect(() => {
    // Drop the prompt from history so a reload or back-navigation doesn't send it again.
    if (initialPrompt) navigate(location.pathname, { replace: true, state: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once, on arrival
  }, [])

  useEffect(() => {
    let cancelled = false
    getThreadMessages(threadId)
      .then((messages) => !cancelled && setState({ status: 'ready', messages }))
      .catch(
        (error: unknown) =>
          !cancelled &&
          setState({ status: 'error', error: error instanceof Error ? error : new Error(String(error)) }),
      )
    return () => {
      cancelled = true
    }
  }, [threadId, reloadKey])

  if (!state) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <Loader variant="text-shimmer" text="Loading conversation…" />
      </div>
    )
  }
  if (state.status === 'error') {
    const { title, message, showLoginLink } = classifyChatError(state.error)
    return (
      <div role="alert" className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
        <p className="font-medium">{title}</p>
        <p className="max-w-md text-sm text-muted-foreground">{message}</p>
        {showLoginLink ? (
          <Button asChild variant="outline" size="sm" className="mt-2">
            <Link to="/login">Sign in again</Link>
          </Button>
        ) : (
          <Button variant="outline" size="sm" className="mt-2" onClick={() => setReloadKey((key) => key + 1)}>
            Try again
          </Button>
        )}
      </div>
    )
  }
  return (
    <ChatView
      threadId={threadId}
      initialMessages={state.messages}
      initialPrompt={state.messages.length === 0 ? initialPrompt : undefined}
    />
  )
}
