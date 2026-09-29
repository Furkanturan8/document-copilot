import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { LogoMark } from '@/components/Logo'
import { useThreads } from '@/components/chat/threads-context'
import { PromptSuggestion } from '@/components/ui/prompt-suggestion'
import { EXAMPLE_QUESTIONS } from '@/lib/suggestions'

export function ChatEmptyPage() {
  const { createThread } = useThreads()
  const navigate = useNavigate()
  const [isStarting, setIsStarting] = useState(false)

  async function startWith(question: string) {
    setIsStarting(true)
    try {
      const thread = await createThread()
      navigate(`/chats/${thread.id}`, { state: { initialPrompt: question } })
    } finally {
      setIsStarting(false)
    }
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-8 overflow-y-auto p-6">
      <div className="flex flex-col items-center gap-4 text-center">
        <LogoMark className="size-12 rounded-xl" />
        <div className="flex flex-col gap-1.5">
          <h1 className="text-2xl font-semibold tracking-tight">How can I help with your filings?</h1>
          <p className="max-w-md text-sm text-muted-foreground">
            Ask about the 10-K filings of Apple, Amazon, Alphabet, Microsoft and NVIDIA (2021–2025). Every answer
            cites the passages it comes from.
          </p>
        </div>
      </div>

      <div className="grid w-full max-w-2xl gap-2 sm:grid-cols-2">
        {EXAMPLE_QUESTIONS.map((question) => (
          <PromptSuggestion
            key={question}
            className="h-auto justify-start rounded-xl px-4 py-3 text-left text-sm font-normal whitespace-normal"
            disabled={isStarting}
            onClick={() => void startWith(question)}
          >
            {question}
          </PromptSuggestion>
        ))}
      </div>
    </div>
  )
}
