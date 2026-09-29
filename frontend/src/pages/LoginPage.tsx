import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'

import { AuthForm } from '@/components/auth/AuthForm'
import { useAuth } from '@/components/auth/auth-context'
import { supabase } from '@/lib/supabase'

export function LoginPage() {
  const { session, isLoading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const redirectTo = (location.state as { from?: string } | null)?.from ?? '/chats'

  if (isLoading) return null
  if (session) return <Navigate to={redirectTo} replace />

  async function signIn(email: string, password: string) {
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) return error.message
    navigate(redirectTo, { replace: true })
  }

  return (
    <AuthForm
      title="Sign in"
      description="Use your work email to access Document Copilot."
      submitLabel="Sign in"
      onSubmit={signIn}
      footer={
        <>
          No account yet?{' '}
          <Link to="/request-access" className="font-medium text-foreground underline-offset-4 hover:underline">
            Request access
          </Link>
        </>
      }
    />
  )
}
