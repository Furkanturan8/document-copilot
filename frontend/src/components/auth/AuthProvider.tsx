import type { Session } from '@supabase/supabase-js'
import { useEffect, useState, type ReactNode } from 'react'

import { AuthContext } from '@/components/auth/auth-context'
import { supabase } from '@/lib/supabase'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Fires INITIAL_SESSION on subscribe, then on every sign-in, sign-out and token refresh.
    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
      setIsLoading(false)
    })
    return () => data.subscription.unsubscribe()
  }, [])

  return <AuthContext.Provider value={{ session, isLoading }}>{children}</AuthContext.Provider>
}
