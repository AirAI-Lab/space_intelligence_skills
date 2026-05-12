import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  base: '/',
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/styles/mixins.scss" as *;\n`
      }
    }
  },
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        // Docker 环境使用 backend:8080，本地开发使用 localhost:8081
        target: process.env.DOCKER_ENV === 'true' ? 'http://backend:8080' : 'http://localhost:8081',
        changeOrigin: true
      },
      '/ws': {
        target: process.env.DOCKER_ENV === 'true' ? 'ws://backend:8080' : 'ws://localhost:8081',
        ws: true
      }
    }
  }
})
