/** 播放条「展开全屏」入口验收（v2.46.317）：桌面 + 手机各看一次 */
const { chromium } = require('playwright')
const BASE = process.env.PROBE_BASE || 'http://localhost:5303'
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url')
const JWT = [b64u({ alg: 'HS256', typ: 'JWT' }), b64u({ sub: '1', exp: Math.floor(Date.now() / 1000) + 86400 * 30 }), 'sig'].join('.')
const T = { id: 1, title: '夜航西飞', artist: '陈鸿宇', duration: 245 }
function wav() { const r = 8000, s = r * 3, b = Buffer.alloc(44 + s); b.write('RIFF', 0); b.writeUInt32LE(36 + s, 4); b.write('WAVE', 8); b.write('fmt ', 12); b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(1, 22); b.writeUInt32LE(r, 24); b.writeUInt32LE(r, 28); b.writeUInt16LE(1, 32); b.writeUInt16LE(8, 34); b.write('data', 36); b.writeUInt32LE(s, 40); b.fill(128, 44); return b }
;(async () => {
  const b = await chromium.launch()
  for (const vp of [{ name: 'desktop', width: 1440, height: 900, isMobile: false }, { name: 'mobile', width: 390, height: 844, isMobile: true }]) {
    const ctx = await b.newContext({ viewport: { width: vp.width, height: vp.height }, isMobile: vp.isMobile, hasTouch: vp.isMobile, deviceScaleFactor: 2 })
    await ctx.route((u) => u.pathname.startsWith('/api/'), (r) => {
      const u = r.request().url()
      const j = (d) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: d }) })
      if (/stream/.test(u)) return r.fulfill({ status: 200, contentType: 'audio/wav', body: wav() })
      if (/\/api\/auth\/me/.test(u)) return j({ id: 1, username: 'probe', is_super_admin: 1 })
      if (/\/api\/music\/playback/.test(u)) return j({ track: T, position: 40 })
      if (/\/api\/music/.test(u)) return j({ list: [T], total: 1 })
      return j({ list: [], total: 0 })
    })
    await ctx.addInitScript((t) => { localStorage.setItem('token', t); localStorage.setItem('np_minimized', '0') }, JWT)
    const p = await ctx.newPage()
    p.on('pageerror', (e) => { if (!/slice/.test(e.message)) console.log('[pageerror]', e.message.slice(0, 120)) })
    /* 直接从 /tool 起（不是工作台）：mock 下工作台卡片渲染会抛错，把 app 的 patch 队列搞坏，
       后续路由跳转全都进不去 —— 那是探针的问题，不是入口的问题。 */
    await p.goto(`${BASE}/tool`, { waitUntil: 'domcontentloaded', timeout: 60000 })
    await p.waitForTimeout(3600)
    const info = await p.evaluate(() => {
      const e = document.querySelector('.np-expand')
      const bar = document.querySelector('.npbar')
      const r = e && e.getBoundingClientRect()
      return { hasBtn: !!e, rect: r && [Math.round(r.width), Math.round(r.height), Math.round(r.right), Math.round(r.top)], barW: bar && Math.round(bar.getBoundingClientRect().width), title: e && e.title, vw: window.innerWidth, vh: window.innerHeight }
    })
    console.log(`[${vp.name}] 展开按钮:`, JSON.stringify(info))
    await p.screenshot({ path: `artifacts/_probe/bar_${vp.name}.png` })
    /* 手机浏览器上本站 viewport 被写成 width=1280（main.js），Playwright 按 390 判可见性会超时；
       用 JS 触发 click，验证的是同一个 handler。 */
    await p.evaluate(() => document.querySelector('.np-expand').click())
    await p.waitForTimeout(1800)
    console.log(`[${vp.name}] 点击后 url=${p.url()} fp=${await p.evaluate(() => !!document.querySelector('.fp'))}`)
    await ctx.close()
  }
  await b.close()
})()
