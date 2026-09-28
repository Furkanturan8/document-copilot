import { Outlet } from 'react-router-dom'

import { ThreadSidebar } from '@/components/chat/ThreadSidebar'
import { ThreadsProvider } from '@/components/chat/ThreadsProvider'

export function ChatLayout() {
  return (
    <ThreadsProvider>
      <div className="flex h-svh">
        <ThreadSidebar />
        <main className="flex min-w-0 flex-1 flex-col">
          <Outlet />
        </main>
      </div>
    </ThreadsProvider>
  )
}
