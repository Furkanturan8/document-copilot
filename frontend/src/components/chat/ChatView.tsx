import { useChat } from '@ai-sdk/react'
import { useState } from 'react'

import { ChatInput } from '@/components/chat/ChatInput'
import { MessageList } from '@/components/chat/MessageList'
import { useThreads } from '@/components/chat/threads-context'
import { createChatTransport, type UIMessage } from '@/lib/chat'

type ChatViewProps = {
  threadId: string
  initialMessages: UIMessage[]
}

export function ChatView({ threadId, initialMessages }: ChatViewProps) {
  const { refreshThreads } = useThreads()
  const [transport] = useState(createChatTransport)
  const { messages, sendMessage, status, error, stop } = useChat({
    id: threadId,
    messages: initialMessages,
    transport,
    // The backend renames the thread after its first turn and bumps updatedAt; resync the sidebar.
    onFinish: () => void refreshThreads(),
  })

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {messages.length === 0 ? (
        <div className="flex flex-1 items-center justify-center p-4 text-center text-muted-foreground">
          Ask a question about the SEC filings to start this conversation.
        </div>
      ) : (
        <MessageList messages={messages} status={status} />
      )}
      {error && (
        <p role="alert" className="mx-auto w-full max-w-3xl px-4 text-sm text-destructive">
          {error.message || 'Something went wrong. Please try again.'}
        </p>
      )}
      <ChatInput status={status} onSend={(text) => sendMessage({ text })} onStop={stop} />
    </div>
  )
}
