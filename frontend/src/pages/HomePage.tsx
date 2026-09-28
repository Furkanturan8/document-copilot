import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { api, type CurrentUser } from '@/lib/api'
import { ApiError } from '@/lib/http'
import { supabase } from '@/lib/supabase'

// Placeholder until the chat list lands in Phase 3; proves the bearer token reaches the backend.
export function HomePage() {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .getCurrentUser()
      .then(setUser)
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : String(err)))
  }, [])

  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-4 p-4">
      {user && (
        <p>
          Backend verified you as <strong>{user.email}</strong>
        </p>
      )}
      {error && (
        <p role="alert" className="text-destructive">
          {error}
        </p>
      )}
      {!user && !error && <p className="text-muted-foreground">Checking session with the backend…</p>}
      <Button variant="outline" onClick={() => supabase.auth.signOut()}>
        Sign out
      </Button>
    </main>
  )
}
