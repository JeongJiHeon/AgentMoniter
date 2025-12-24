import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api/llm': {
        target: 'https://api.platform.a15t.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/llm/, '/v1'),
        secure: false,
      },
    },
  },
})
