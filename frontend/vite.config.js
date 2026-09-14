
import { execSync } from 'node:child_process'
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'

/**
 * SW 版本号自动注入：build 时把 sw.js 里的 __SW_VERSION__ 替换为
 *   - git short hash（如果在 git 仓库内）
 *   - 否则 build timestamp (YYYYMMDD-HHMMSS)
 * 避免人工改 VERSION 导致缓存不刷。
 */
function injectSwVersion() {
  let version = 'unknown'
  try {
    version = execSync('git rev-parse --short HEAD', { stdio: ['ignore', 'pipe', 'ignore'] })
      .toString().trim()
  } catch {
    const d = new Date()
    const pad = n => String(n).padStart(2, '0')
    version = `build-${d.getFullYear()}${pad(d.getMonth()+1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`
  }
  return {
    name: 'inject-sw-version',
    apply: 'build',
    closeBundle() {
      const swPath = resolve(__dirname, 'dist', 'sw.js')
      if (!existsSync(swPath)) return
      const content = readFileSync(swPath, 'utf8')
      if (!content.includes('__SW_VERSION__')) return
      const newContent = content.replace('__SW_VERSION__', version)
      writeFileSync(swPath, newContent)
      console.log('[sw-version] injected:', version)
    },
  }
}

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue(), injectSwVersion()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false
      },
      '/uploads': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false
      },
      '/music': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false
      }
    }
  }
})