import { LogOut, Plus, Trash2 } from 'lucide-react'
import { NavLink, useNavigate, useParams } from 'react-router-dom'

import { useAuth } from '@/components/auth/auth-context'
import { useThreads } from '@/components/chat/threads-context'
import { Button } from '@/components/ui/button'
import { supabase } from '@/lib/supabase'
import { cn } from '@/lib/utils'

export function ThreadSidebar() {
  const { session } = useAuth()
  const { threads, isLoading, error, createThread, deleteThread } = useThreads()
  const navigate = useNavigate()
  const { threadId } = useParams()

  async function startNewChat() {
    const thread = await createThread()
    navigate(`/chats/${thread.id}`)
  }

  async function removeThread(id: string, title: string) {
    if (!window.confirm(`Delete "${title}"? This cannot be undone.`)) return
    await deleteThread(id)
    if (id === threadId) navigate('/chats', { replace: true })
  }

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r bg-muted/30">
      <div className="p-3">
        <Button className="w-full" onClick={startNewChat}>
          <Plus /> New chat
        </Button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2" aria-label="Conversations">
        {isLoading && <p className="px-2 py-1 text-sm text-muted-foreground">Loading conversations…</p>}
        {error && (
          <p role="alert" className="px-2 py-1 text-sm text-destructive">
            {error}
          </p>
        )}
        {!isLoading && !error && threads.length === 0 && (
          <p className="px-2 py-1 text-sm text-muted-foreground">No conversations yet.</p>
        )}
        <ul className="flex flex-col gap-0.5">
          {threads.map((thread) => (
            <li key={thread.id} className="group relative">
              <NavLink
                to={`/chats/${thread.id}`}
                className={({ isActive }) =>
                  cn(
                    'block truncate rounded-md py-2 pr-9 pl-2 text-sm hover:bg-muted',
                    isActive && 'bg-muted font-medium',
                  )
                }
              >
                {thread.title}
              </NavLink>
              <Button
                variant="ghost"
                size="icon-sm"
                className="absolute top-1/2 right-1 -translate-y-1/2 opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
                aria-label={`Delete ${thread.title}`}
                onClick={() => removeThread(thread.id, thread.title)}
              >
                <Trash2 />
              </Button>
            </li>
          ))}
        </ul>
      </nav>

      <div className="flex items-center gap-2 border-t p-3">
        <span className="flex-1 truncate text-sm text-muted-foreground">{session?.user.email}</span>
        <Button variant="ghost" size="icon-sm" aria-label="Sign out" onClick={() => supabase.auth.signOut()}>
          <LogOut />
        </Button>
      </div>
    </aside>
  )
}
