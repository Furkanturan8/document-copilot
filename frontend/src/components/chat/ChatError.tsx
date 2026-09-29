import { AlertTriangle } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { classifyChatError } from '@/lib/chat-errors'

export function ChatError({ error }: { error: Error }) {
  const { title, message, showLoginLink } = classifyChatError(error)

  return (
    <Alert variant="destructive">
      <AlertTriangle />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        {message}
        {showLoginLink && (
          <Link to="/login" className="font-medium text-foreground underline underline-offset-4">
            Sign in again
          </Link>
        )}
      </AlertDescription>
    </Alert>
  )
}
