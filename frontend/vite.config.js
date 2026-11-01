import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: process.env.GITHUB_ACTIONS === 'true' ? '/Agentic-AI-HUB/' : '/',
  build: { assetsDir: 'agentic-ai-hub-assets' },
  plugins: [react()],
  server: { port: 5173 },
})