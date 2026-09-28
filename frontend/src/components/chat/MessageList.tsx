import type { ChatStatus } from 'ai'
import { useEffect, useRef } from 'react'

import { messageText, type UIMessage } from '@/lib/chat'
import { cn } from '@/lib/utils'

type MessageListProps = {
  messages: UIMessage[]
  status: ChatStatus
}

export function MessageList({ messages, status }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, status])

  return (
    <div className="flex-1 overflow-y-auto">
      <ol className="mx-auto flex max-w-3xl flex-col gap-4 p-4">
        {messages.map((message) => (
          <li
            key={message.id}
            className={cn(
              'max-w-[85%] rounded-lg px-4 py-2 whitespace-pre-wrap',
              message.role === 'user' ? 'self-end bg-primary text-primary-foreground' : 'self-start bg-muted',
            )}
          >
            {messageText(message)}
          </li>
        ))}
        {status === 'submitted' && (
          <li className="self-start rounded-lg bg-muted px-4 py-2 text-muted-foreground" aria-live="polite">
            <span className="animate-pulse">Thinking…</span>
          </li>
        )}
      </ol>
      <div ref={endRef} />
    </div>
  )
}
