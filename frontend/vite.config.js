import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/chat': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
      '/sessions': 'http://127.0.0.1:8000',
    }
  }
})
