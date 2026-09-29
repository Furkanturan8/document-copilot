import { Loader2 } from 'lucide-react'
import { useState, type FormEvent, type ReactNode } from 'react'

import { AuthLayout } from '@/components/auth/AuthLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

type AuthFormProps = {
  title: string
  description: string
  submitLabel: string
  footer: ReactNode
  // Returns an error message to show, or nothing on success.
  onSubmit: (email: string, password: string) => Promise<string | void>
}

export function AuthForm({ title, description, submitLabel, footer, onSubmit }: AuthFormProps) {
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setError(null)
    setIsSubmitting(true)
    const message = await onSubmit(String(form.get('email')).trim(), String(form.get('password')))
    setIsSubmitting(false)
    if (message) setError(message)
  }

  return (
    <AuthLayout title={title} description={description}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" name="email" type="email" autoComplete="email" placeholder="you@company.com" required />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="password">Password</Label>
          <Input id="password" name="password" type="password" autoComplete="current-password" required />
        </div>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <Button type="submit" className="mt-2 w-full" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="animate-spin" />}
          {isSubmitting ? 'Please wait…' : submitLabel}
        </Button>
      </form>
      <p className="mt-4 text-center text-sm text-muted-foreground">{footer}</p>
    </AuthLayout>
  )
}
