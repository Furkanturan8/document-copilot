import { Outlet, useParams } from 'react-router-dom'

import { ThreadSidebar } from '@/components/chat/ThreadSidebar'
import { ThreadsProvider } from '@/components/chat/ThreadsProvider'
import { useThreads } from '@/components/chat/threads-context'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'

function ChatHeader() {
  const { threadId } = useParams()
  const { threads } = useThreads()
  const title = threads.find((thread) => thread.id === threadId)?.title

  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b px-3">
      <SidebarTrigger className="text-muted-foreground" />
      <span className="truncate text-sm font-medium">{title ?? 'Document Copilot'}</span>
    </header>
  )
}

export function ChatLayout() {
  return (
    <ThreadsProvider>
      <SidebarProvider>
        <ThreadSidebar />
        <SidebarInset className="h-svh min-h-0">
          <ChatHeader />
          <div className="flex min-h-0 flex-1 flex-col">
            <Outlet />
          </div>
        </SidebarInset>
      </SidebarProvider>
    </ThreadsProvider>
  )
}
