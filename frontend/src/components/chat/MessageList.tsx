import type { ChatStatus } from 'ai'

import { AssistantMessage } from '@/components/chat/AssistantMessage'
import { PipelineStatus } from '@/components/chat/PipelineStatus'
import { ChatContainerContent, ChatContainerRoot } from '@/components/ui/chat-container'
import { ScrollButton } from '@/components/ui/scroll-button'
import { messageText, type UIMessage } from '@/lib/chat'
import type { CitationPayload, PipelineStatus as PipelineStatusState } from '@/lib/citations'

type MessageListProps = {
  messages: UIMessage[]
  status: ChatStatus
  pipelineStatus: PipelineStatusState | null
  selectedCitationIndex: number | null
  onSelectCitation: (citation: CitationPayload) => void
}

export function MessageList({ messages, status, pipelineStatus, selectedCitationIndex, onSelectCitation }: MessageListProps) {
  const lastMessage = messages.at(-1)
  const isAnswerStreaming =
    status === 'streaming' && lastMessage?.role === 'assistant' && messageText(lastMessage).length > 0
  // The agent works for a while before any answer text arrives; show its progress meanwhile.
  const showPipeline = (status === 'submitted' || status === 'streaming') && !isAnswerStreaming

  return (
    <ChatContainerRoot className="relative min-h-0 flex-1">
      <ChatContainerContent className="mx-auto w-full max-w-3xl gap-8 px-4 py-8">
        {messages.map((message) =>
          message.role === 'user' ? (
            <div key={message.id} className="flex justify-end">
              <div className="max-w-[80%] rounded-2xl rounded-br-md bg-secondary px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap">
                {messageText(message)}
              </div>
            </div>
          ) : (
            <AssistantMessage
              key={message.id}
              message={message}
              isStreaming={message === lastMessage && isAnswerStreaming}
              selectedCitationIndex={selectedCitationIndex}
              onSelectCitation={onSelectCitation}
            />
          ),
        )}
        {showPipeline && <PipelineStatus status={pipelineStatus} />}
      </ChatContainerContent>

      <div className="pointer-events-none absolute inset-x-0 bottom-4 flex justify-center">
        <div className="pointer-events-auto">
          <ScrollButton className="shadow-sm" />
        </div>
      </div>
    </ChatContainerRoot>
  )
}
