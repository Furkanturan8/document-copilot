import { Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { useThreads } from '@/components/chat/threads-context'
import { Button } from '@/components/ui/button'

export function ChatEmptyPage() {
  const { createThread } = useThreads()
  const navigate = useNavigate()

  async function startNewChat() {
    const thread = await createThread()
    navigate(`/chats/${thread.id}`)
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-4 text-center">
      <h1 className="text-xl font-semibold">Document Copilot</h1>
      <p className="max-w-md text-muted-foreground">
        Ask questions about the SEC filings in the corpus. Every answer will cite the passages it comes from.
      </p>
      <Button onClick={startNewChat}>
        <Plus /> New chat
      </Button>
    </div>
  )
}
