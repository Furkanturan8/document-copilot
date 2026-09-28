import { Link } from 'react-router-dom'

import { Card, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'

// Public sign-up is disabled in Supabase; accounts are created by an admin in the dashboard.
export function RequestAccessPage() {
  return (
    <main className="flex min-h-svh items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Request access</CardTitle>
          <CardDescription>
            Document Copilot accounts are created by your administrator. Contact them with your work email to get
            access, then sign in with the credentials they give you.
          </CardDescription>
        </CardHeader>
        <CardFooter>
          <p className="text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link to="/login" className="underline underline-offset-4">
              Sign in
            </Link>
          </p>
        </CardFooter>
      </Card>
    </main>
  )
}
