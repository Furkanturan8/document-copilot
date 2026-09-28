import type { ChatStatus } from 'ai'
import { SendHorizontal, Square } from 'lucide-react'
import { useState, type FormEvent, type KeyboardEvent } from 'react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

type ChatInputProps = {
  status: ChatStatus
  onSend: (text: string) => void
  onStop: () => void
}

export function ChatInput({ status, onSend, onStop }: ChatInputProps) {
  const [text, setText] = useState('')
  const isBusy = status === 'submitted' || status === 'streaming'

  function submit(event?: FormEvent) {
    event?.preventDefault()
    const trimmed = text.trim()
    if (!trimmed || isBusy) return
    onSend(trimmed)
    setText('')
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends, Shift+Enter adds a line; skip while an IME composition is active.
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) submit(event)
  }

  return (
    <form onSubmit={submit} className="mx-auto flex w-full max-w-3xl items-end gap-2 p-4">
      <Textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about the filings…"
        aria-label="Message"
        rows={2}
        className="max-h-48 resize-none"
        autoFocus
      />
      {isBusy ? (
        <Button type="button" variant="outline" size="icon" aria-label="Stop generating" onClick={onStop}>
          <Square />
        </Button>
      ) : (
        <Button type="submit" size="icon" aria-label="Send message" disabled={!text.trim()}>
          <SendHorizontal />
        </Button>
      )}
    </form>
  )
}
