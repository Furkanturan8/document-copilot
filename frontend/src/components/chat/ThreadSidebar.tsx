import { Loader2, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { Logo } from '@/components/Logo'
import { UserMenu } from '@/components/chat/UserMenu'
import { useThreads } from '@/components/chat/threads-context'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSkeleton,
  useSidebar,
} from '@/components/ui/sidebar'
import type { ThreadSummary } from '@/lib/chat'
import { groupByRecency } from '@/lib/format'

export function ThreadSidebar() {
  const { threads, isLoading, error, createThread, deleteThread } = useThreads()
  const navigate = useNavigate()
  const { threadId } = useParams()
  const { isMobile, setOpenMobile } = useSidebar()
  const [isCreating, setIsCreating] = useState(false)
  const [threadToDelete, setThreadToDelete] = useState<ThreadSummary | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  function closeOnMobile() {
    if (isMobile) setOpenMobile(false)
  }

  async function startNewChat() {
    setIsCreating(true)
    try {
      const thread = await createThread()
      navigate(`/chats/${thread.id}`)
      closeOnMobile()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not start a new chat.')
    } finally {
      setIsCreating(false)
    }
  }

  async function confirmDelete() {
    if (!threadToDelete) return
    setIsDeleting(true)
    try {
      await deleteThread(threadToDelete.id)
      toast.success('Conversation deleted')
      if (threadToDelete.id === threadId) navigate('/chats', { replace: true })
      setThreadToDelete(null)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not delete the conversation.')
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <>
      <Sidebar>
        <SidebarHeader className="gap-3 p-3">
          <Logo className="p-1" />
          <Button
            variant="outline"
            className="w-full justify-start border-dashed bg-transparent text-muted-foreground shadow-none hover:text-foreground"
            disabled={isCreating}
            onClick={() => void startNewChat()}
          >
            {isCreating ? <Loader2 className="animate-spin" /> : <Plus />}
            New chat
          </Button>
        </SidebarHeader>

        <SidebarContent>
          {isLoading && (
            <SidebarGroup>
              <SidebarMenu>
                {Array.from({ length: 5 }, (_, index) => (
                  <SidebarMenuItem key={index}>
                    <SidebarMenuSkeleton />
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroup>
          )}
          {!isLoading && error && (
            <p role="alert" className="px-4 py-2 text-sm text-destructive">
              {error}
            </p>
          )}
          {!isLoading && !error && threads.length === 0 && (
            <p className="px-4 py-2 text-sm text-muted-foreground">No conversations yet.</p>
          )}

          {groupByRecency(threads, (thread) => thread.updatedAt).map((group) => (
            <SidebarGroup key={group.label}>
              <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {group.items.map((thread) => (
                    <SidebarMenuItem key={thread.id}>
                      <SidebarMenuButton asChild isActive={thread.id === threadId}>
                        <Link to={`/chats/${thread.id}`} onClick={closeOnMobile}>
                          <span className="truncate">{thread.title}</span>
                        </Link>
                      </SidebarMenuButton>
                      <SidebarMenuAction
                        showOnHover
                        aria-label={`Delete ${thread.title}`}
                        className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                        onClick={() => setThreadToDelete(thread)}
                      >
                        <Trash2 />
                      </SidebarMenuAction>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          ))}
        </SidebarContent>

        <SidebarFooter>
          <UserMenu />
        </SidebarFooter>
      </Sidebar>

      <AlertDialog open={threadToDelete !== null} onOpenChange={(open) => !open && !isDeleting && setThreadToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogMedia className="bg-destructive/10 text-destructive">
              <Trash2 />
            </AlertDialogMedia>
            <AlertDialogTitle>Delete this conversation?</AlertDialogTitle>
            <AlertDialogDescription>
              “{threadToDelete?.title}” and its message history will be deleted permanently. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={isDeleting}
              onClick={(event) => {
                // Keep the dialog open until the delete finishes.
                event.preventDefault()
                void confirmDelete()
              }}
            >
              {isDeleting ? 'Deleting…' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
