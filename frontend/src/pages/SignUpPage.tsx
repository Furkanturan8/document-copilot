import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'

import { AuthForm } from '@/components/auth/AuthForm'
import { useAuth } from '@/components/auth/auth-context'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { supabase } from '@/lib/supabase'

export function SignUpPage() {
  const { session, isLoading } = useAuth()
  const [confirmationSentTo, setConfirmationSentTo] = useState<string | null>(null)

  if (isLoading) return null
  if (session) return <Navigate to="/" replace />

  if (confirmationSentTo) {
    return (
      <main className="flex min-h-svh items-center justify-center p-4">
        <Card className="w-full max-w-sm">
          <CardHeader>
            <CardTitle>Check your email</CardTitle>
            <CardDescription>
              We sent a confirmation link to {confirmationSentTo}. Open it, then{' '}
              <Link to="/login" className="underline underline-offset-4">
                sign in
              </Link>
              .
            </CardDescription>
          </CardHeader>
        </Card>
      </main>
    )
  }

  async function signUp(email: string, password: string) {
    const { data, error } = await supabase.auth.signUp({ email, password })
    if (error) return error.message
    // With email confirmation off, Supabase signs the user in right away and the
    // session redirect above takes over; with it on, there is no session yet.
    if (!data.session) setConfirmationSentTo(email)
  }

  return (
    <AuthForm
      title="Create an account"
      description="Sign up with your work email."
      submitLabel="Sign up"
      passwordAutoComplete="new-password"
      onSubmit={signUp}
      footer={
        <>
          Already have an account?{' '}
          <Link to="/login" className="underline underline-offset-4">
            Sign in
          </Link>
        </>
      }
    />
  )
}
