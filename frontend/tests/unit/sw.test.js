import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

const SW_PATH = path.resolve(__dirname, '..', '..', 'public', 'sw.js')
const SRC = fs.readFileSync(SW_PATH, 'utf-8')

describe('Service Worker (sw.js)', () => {
  it('exists and is non-empty', () => {
    expect(SRC.length).toBeGreaterThan(200)
  })

  it('skips /api/ paths', () => {
    expect(SRC).toContain("url.pathname.startsWith('/api/')")
  })

  it('skips requests with Authorization header', () => {
    expect(SRC.toLowerCase()).toContain('authorization')
    // 必须显式读取 request header 中的 authorization
    expect(SRC).toMatch(/headers\.get\(['"]authorization['"]\)/i)
  })

  it('only caches static asset paths', () => {
    expect(SRC).toContain("'/assets/'")
    expect(SRC).toContain("'/index.html'")
    expect(SRC).toContain("'/manifest.webmanifest'")
    expect(SRC).toContain("'/icons/'")
  })

  it('skips cross-origin requests', () => {
    expect(SRC).toContain('self.location.origin')
  })

  it('only caches GET requests', () => {
    expect(SRC).toContain("req.method !== 'GET'")
  })

  it('POST/PUT/DELETE/HEAD/OPTIONS all fall through (no event.respondWith for non-GET)', () => {
    // 非 GET 一律放行：实现里 if (req.method !== 'GET') return → 不调用 event.respondWith
    expect(SRC).toContain("req.method !== 'GET'")
    // 找到 GET 检查的位置到 fetch 处理器结尾之间不应有 caches.open
    const guardIdx = SRC.indexOf("req.method !== 'GET'")
    expect(guardIdx).toBeGreaterThan(0)
    // guard 应在 caches.open(STATIC_CACHE) 之前出现
    const cachesIdx = SRC.indexOf('caches.open(STATIC_CACHE)')
    expect(cachesIdx).toBeGreaterThan(0)
    expect(guardIdx).toBeLessThan(cachesIdx)
  })

  it('only caches same-origin 200 basic responses', () => {
    expect(SRC).toContain('response.status === 200')
    expect(SRC).toContain("response.type === 'basic'")
  })

  it('uses cache versioning and cleans old caches on activate', () => {
    expect(SRC).toContain('skipWaiting')
    expect(SRC).toContain('clients.claim')
    expect(SRC).toContain('caches.delete')
  })
})