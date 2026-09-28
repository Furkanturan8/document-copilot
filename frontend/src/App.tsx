import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'

import { AuthProvider } from '@/components/auth/AuthProvider'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { HomePage } from '@/pages/HomePage'
import { LoginPage } from '@/pages/LoginPage'
import { RequestAccessPage } from '@/pages/RequestAccessPage'

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/request-access', element: <RequestAccessPage /> },
  {
    element: <ProtectedRoute />,
    children: [{ path: '/', element: <HomePage /> }],
  },
  { path: '*', element: <Navigate to="/" replace /> },
])

export default function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  )
}
