import { useChat } from '@ai-sdk/react'
import { useEffect, useRef, useState } from 'react'

import { ChatError } from '@/components/chat/ChatError'
import { ChatInput } from '@/components/chat/ChatInput'
import { MessageList } from '@/components/chat/MessageList'
import { SourcePassageSheet } from '@/components/chat/SourcePassageSheet'
import { useThreads } from '@/components/chat/threads-context'
import { createChatTransport, type UIMessage } from '@/lib/chat'
import { isPipelineStatus, type CitationPayload, type PipelineStatus } from '@/lib/citations'

type ChatViewProps = {
  threadId: string
  initialMessages: UIMessage[]
  // A question picked on the empty page, sent once this thread opens.
  initialPrompt?: string
}

export function ChatView({ threadId, initialMessages, initialPrompt }: ChatViewProps) {
  const { refreshThreads } = useThreads()
  const [transport] = useState(createChatTransport)
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null)
  const [selectedCitation, setSelectedCitation] = useState<CitationPayload | null>(null)
  const { messages, sendMessage, status, error, stop } = useChat({
    id: threadId,
    messages: initialMessages,
    transport,
    // Transient `data-status` parts only reach this callback; they are never added to the message.
    onData: (part) => {
      if (part.type === 'data-status' && isPipelineStatus(part.data)) setPipelineStatus(part.data)
    },
    // The backend renames the thread after its first turn and bumps updatedAt; resync the sidebar.
    onFinish: () => {
      setPipelineStatus(null)
      void refreshThreads()
    },
  })

  function send(text: string) {
    setPipelineStatus(null)
    setSelectedCitation(null)
    void sendMessage({ text })
  }

  // A ref, not state: StrictMode runs effects twice and the prompt must be sent only once.
  const sentInitialPrompt = useRef(false)
  useEffect(() => {
    if (!initialPrompt || sentInitialPrompt.current) return
    sentInitialPrompt.current = true
    send(initialPrompt)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- runs once per mounted thread
  }, [initialPrompt])

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {messages.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-1 p-4 text-center">
          <h2 className="font-semibold">Ask about the SEC filings</h2>
          <p className="text-sm text-muted-foreground">Every answer cites the filing passages it comes from.</p>
        </div>
      ) : (
        <MessageList
          messages={messages}
          status={status}
          pipelineStatus={pipelineStatus}
          selectedCitationIndex={selectedCitation?.citationIndex ?? null}
          onSelectCitation={setSelectedCitation}
        />
      )}
      {error && (
        <div className="mx-auto w-full max-w-3xl px-4 pb-3">
          <ChatError error={error} />
        </div>
      )}
      <ChatInput status={status} onSend={send} onStop={stop} />
      <SourcePassageSheet citation={selectedCitation} onClose={() => setSelectedCitation(null)} />
    </div>
  )
}
