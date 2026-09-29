import { Link } from 'react-router-dom'

import { AuthLayout } from '@/components/auth/AuthLayout'

// Public sign-up is disabled in Supabase; accounts are created by an admin in the dashboard.
export function RequestAccessPage() {
  return (
    <AuthLayout
      title="Request access"
      description="Document Copilot accounts are created by your administrator. Contact them with your work email to get access, then sign in with the credentials they give you."
    >
      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-foreground underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  )
}
