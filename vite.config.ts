import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
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
