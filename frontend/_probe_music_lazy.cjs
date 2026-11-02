/**
 * 音乐页「滚动自动加载」验收（v2.46.319）
 * 手机视口 390×844，mock 120 首，验证：首屏 40 → 滚到底 80 → 再滚 120，全程不点按钮。
 */
const { chromium } = require('playwright')
const BASE = process.env.PROBE_BASE || 'http://localhost:5321'
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url')
const JWT = [
  b64u({ alg: 'HS256', typ: 'JWT' }),
  b64u({ sub: '1', exp: Math.floor(Date.now() / 1000) + 86400 * 30 }),
  'sig',
].join('.')

const TOTAL = 120
const TRACKS = Array.from({ length: TOTAL }, (_, i) => ({
  id: i + 1,
  title: `测试曲目 ${String(i + 1).padStart(3, '0')}`,
  artist: '测试歌手',
  category: '流行',
  duration: 200 + i,
  file_size: 4000000 + i * 1000,
  file_url: `/music/test-${i + 1}.mp3`,
  created_at: '2026-11-01 10:00:00',
}))

;(async () => {
  const b = await chromium.launch()
  const ctx = await b.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
    deviceScaleFactor: 2,
  })
  await ctx.route((u) => u.pathname === '/music', async (route) => {
    const resp = await route.fetch({ url: `${BASE}/` })
    await route.fulfill({ response: resp })
  })
  await ctx.route((u) => u.pathname.startsWith('/api/'), (r) => {
    const u = r.request().url()
    const j = (d) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: d }) })
    if (/\/api\/auth\/me/.test(u)) return j({ id: 1, username: 'probe', is_super_admin: 1, menus: [] })
    if (/\/api\/music/.test(u)) return j({ list: TRACKS, total: TOTAL })
    return j({ list: [], total: 0 })
  })
  // 本站「移动端」只认 APK UA 或 localStorage 强制位（?m=1 写的就是这个键）
  await ctx.addInitScript((t) => {
    localStorage.setItem('token', t)
    localStorage.setItem('xuanhuang_force_mobile', '1')
  }, JWT)

  const p = await ctx.newPage()
  p.on('pageerror', (e) => { if (!/slice/.test(e.message)) console.log('[pageerror]', e.message.slice(0, 140)) })

  await p.goto(`${BASE}/music`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForTimeout(2800)

  const rows = () => p.evaluate(() => document.querySelectorAll('.el-table__row').length)
  const sentinel = () => p.evaluate(() => {
    const el = document.querySelector('.mu-more')
    return el ? { text: (el.innerText || '').replace(/\s+/g, ' ').trim(), top: Math.round(el.getBoundingClientRect().top) } : null
  })
  const scrollToBottom = async () => {
    await p.evaluate(() => {
      // 页面可能是 window 滚动，也可能是内部容器：两个都推到底
      window.scrollTo(0, document.documentElement.scrollHeight)
      const cands = Array.from(document.querySelectorAll('div, main, section'))
        .filter((el) => el.scrollHeight > el.clientHeight + 40 && getComputedStyle(el).overflowY !== 'visible')
      cands.forEach((el) => { el.scrollTop = el.scrollHeight })
    })
    await p.waitForTimeout(700)
  }

  console.log('URL:', p.url())
  console.log('首屏行数:', await rows(), '| 哨兵:', JSON.stringify(await sentinel()))
  await p.screenshot({ path: 'artifacts/_probe/music_lazy_1.png' })

  await scrollToBottom()
  console.log('滚到底 → 行数:', await rows(), '| 哨兵:', JSON.stringify(await sentinel()))

  await scrollToBottom()
  console.log('再滚到底 → 行数:', await rows(), '| 哨兵:', JSON.stringify(await sentinel()))

  // 第 3 次：应已到 120 上限，不再增加
  await scrollToBottom()
  console.log('第三次 → 行数:', await rows(), '| 哨兵:', JSON.stringify(await sentinel()))
  await p.screenshot({ path: 'artifacts/_probe/music_lazy_2.png' })

  await b.close()
})()
