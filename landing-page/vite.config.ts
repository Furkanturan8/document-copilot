import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Relative base so the build works under the GitHub Pages project path (/document-copilot/).
export default defineConfig({
  base: './',
  plugins: [react()],
})
