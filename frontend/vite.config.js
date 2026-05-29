import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'https://yexingchen.cn',
        changeOrigin: true,
        secure: false
      },
      '/uploads': {
        target: 'https://yexingchen.cn',
        changeOrigin: true,
        secure: false
      },
      '/music': {
        target: 'https://yexingchen.cn',
        changeOrigin: true,
        secure: false
      }
    }
  }
})