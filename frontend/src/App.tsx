import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'

import { AuthProvider } from '@/components/auth/AuthProvider'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { HomePage } from '@/pages/HomePage'
import { LoginPage } from '@/pages/LoginPage'
import { SignUpPage } from '@/pages/SignUpPage'

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/signup', element: <SignUpPage /> },
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
