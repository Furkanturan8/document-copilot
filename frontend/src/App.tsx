import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'

import { AuthProvider } from '@/components/auth/AuthProvider'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { ChatLayout } from '@/components/chat/ChatLayout'
import { ChatEmptyPage } from '@/pages/chat/ChatEmptyPage'
import { ChatThreadPage } from '@/pages/chat/ChatThreadPage'
import { LoginPage } from '@/pages/LoginPage'
import { RequestAccessPage } from '@/pages/RequestAccessPage'

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/request-access', element: <RequestAccessPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: '/chats',
        element: <ChatLayout />,
        children: [
          { index: true, element: <ChatEmptyPage /> },
          { path: ':threadId', element: <ChatThreadPage /> },
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to="/chats" replace /> },
])

export default function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  )
}
