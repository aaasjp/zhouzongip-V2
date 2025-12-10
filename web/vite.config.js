import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0', // 允许任何服务器访问
    port: 8002,
    proxy: {
      '/vector_db_service': {
        target: 'http://localhost:8003',
        changeOrigin: true
      },
      '/chat_service': {
        target: 'http://localhost:8003',
        changeOrigin: true
      }
    }
  }
})

