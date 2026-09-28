import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '@/components/auth/auth-context'

export function ProtectedRoute() {
  const { session, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) return null
  if (!session) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}
