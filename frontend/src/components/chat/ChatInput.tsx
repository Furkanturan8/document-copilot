import type { ChatStatus } from 'ai'
import { ArrowUp, Square } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { PromptInput, PromptInputAction, PromptInputActions, PromptInputTextarea } from '@/components/ui/prompt-input'

type ChatInputProps = {
  status: ChatStatus
  onSend: (text: string) => void
  onStop: () => void
}

export function ChatInput({ status, onSend, onStop }: ChatInputProps) {
  const [text, setText] = useState('')
  const isBusy = status === 'submitted' || status === 'streaming'

  function submit() {
    const trimmed = text.trim()
    if (!trimmed || isBusy) return
    onSend(trimmed)
    setText('')
  }

  return (
    <div className="px-4 pb-4">
      <div className="mx-auto w-full max-w-3xl">
        <PromptInput value={text} onValueChange={setText} isLoading={isBusy} onSubmit={submit} className="rounded-2xl">
          <PromptInputTextarea placeholder="Ask about the filings…" aria-label="Message" autoFocus />
          <PromptInputActions className="justify-end pt-1">
            {isBusy ? (
              <PromptInputAction tooltip="Stop generating">
                <Button size="icon" className="rounded-full" aria-label="Stop generating" onClick={onStop}>
                  <Square className="fill-current" />
                </Button>
              </PromptInputAction>
            ) : (
              <PromptInputAction tooltip="Send">
                <Button
                  size="icon"
                  className="rounded-full"
                  aria-label="Send message"
                  disabled={!text.trim()}
                  onClick={submit}
                >
                  <ArrowUp />
                </Button>
              </PromptInputAction>
            )}
          </PromptInputActions>
        </PromptInput>
        <p className="mt-2 text-center text-xs text-muted-foreground">
          Answers are grounded in SEC filings. Check the cited passages before relying on them.
        </p>
      </div>
    </div>
  )
}
