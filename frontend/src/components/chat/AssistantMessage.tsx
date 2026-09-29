import { Check, Copy } from 'lucide-react'
import { useState } from 'react'

import { AssistantMarkdown } from '@/components/chat/AssistantMarkdown'
import { CitationChip } from '@/components/chat/CitationChip'
import { Button } from '@/components/ui/button'
import { messageText, type UIMessage } from '@/lib/chat'
import { citationsFromMessage, type CitationPayload } from '@/lib/citations'

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <Button
      variant="ghost"
      size="icon-sm"
      className="text-muted-foreground"
      aria-label="Copy answer"
      onClick={() => void copy()}
    >
      {copied ? <Check /> : <Copy />}
    </Button>
  )
}

type AssistantMessageProps = {
  message: UIMessage
  isStreaming: boolean
  selectedCitationIndex: number | null
  onSelectCitation: (citation: CitationPayload) => void
}

export function AssistantMessage({ message, isStreaming, selectedCitationIndex, onSelectCitation }: AssistantMessageProps) {
  const text = messageText(message)
  const citations = citationsFromMessage(message)
  if (!text) return null

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <AssistantMarkdown
        text={text}
        citations={citations}
        selectedCitationIndex={selectedCitationIndex}
        onSelectCitation={onSelectCitation}
      />

      {isStreaming && <span className="h-4 w-2 animate-pulse rounded-sm bg-foreground" />}

      {!isStreaming && citations.length === 0 && (
        <p className="w-fit rounded-lg border border-dashed bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
          No filing passages are cited in this answer.
        </p>
      )}

      {citations.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {citations.map((citation) => (
            <CitationChip
              key={citation.citationIndex}
              citation={citation}
              selected={selectedCitationIndex === citation.citationIndex}
              onSelect={onSelectCitation}
            />
          ))}
        </div>
      )}

      {!isStreaming && (
        <div className="-ml-2 flex items-center">
          <CopyButton text={text} />
        </div>
      )}
    </div>
  )
}
