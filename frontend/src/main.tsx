import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Imported first so missing env vars fail at boot, not on the first API call.
import '@/lib/env'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
