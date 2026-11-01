const { chromium } = require('playwright')
const BASE = 'http://localhost:5301'
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url')
const JWT = [b64u({ alg: 'HS256', typ: 'JWT' }), b64u({ sub: '1', exp: Math.floor(Date.now() / 1000) + 86400 * 30 }), 'sig'].join('.')
;(async () => {
  const b = await chromium.launch()
  const ctx = await b.newContext({ viewport: { width: 1280, height: 820 }, deviceScaleFactor: 1 })
  await ctx.route(/localhost:5301\/api\//, (r) => {
    const u = r.request().url()
    const j = (d) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: d }) })
    if (/\/api\/auth\/me/.test(u)) return j({ id: 1, username: 'probe', is_super_admin: 1 })
    return j({ list: [], total: 0 })
  })
  await ctx.addInitScript((t) => localStorage.setItem('token', t), JWT)
  const p = await ctx.newPage()
  p.on('pageerror', (e) => console.log('[pageerror]', e.message.slice(0, 120)))

  for (const path of ['/profile', '/workbench', '/finance']) {
    await p.goto(`${BASE}${path}`, { waitUntil: 'domcontentloaded', timeout: 60000 })
    await p.waitForTimeout(2000)
    const hasSeg = await p.evaluate(() => !!document.querySelector('.theme-seg'))
    if (!hasSeg) { console.log(`[${path}] 无 .theme-seg`); continue }
    await p.evaluate(() => {
      window.__lt = []
      window.__po = new PerformanceObserver((l) => l.getEntries().forEach((e) => window.__lt.push(e.duration)))
      window.__po.observe({ entryTypes: ['longtask'] })
    })
    const t0 = Date.now()
    await p.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('.theme-seg button, .theme-seg *')).find((x) => (x.textContent || '').trim() === '白天')
      if (btn) btn.click()
    })
    await p.waitForFunction(() => document.documentElement.dataset.theme === 'day', { timeout: 8000 }).catch(() => {})
    const applyMs = Date.now() - t0
    // 等两帧 + 过渡结束
    await p.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))))
    const frameMs = Date.now() - t0
    await p.waitForTimeout(500)
    const stat = await p.evaluate(() => {
      const lt = window.__lt || []
      window.__po && window.__po.disconnect()
      return { longMax: Math.round(Math.max(0, ...lt)), longTotal: Math.round(lt.reduce((a, c) => a + c, 0)), theme: document.documentElement.dataset.theme, hasFlip: document.documentElement.classList.contains('theme-flip') }
    })
    console.log(`[${path}] 属性生效 ${applyMs}ms · 首帧 ${frameMs}ms`, JSON.stringify(stat))
    await p.screenshot({ path: `artifacts/_probe/theme_${path.replace(/\//g, '')}.png` })
    // 切回夜间
    await p.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('.theme-seg button, .theme-seg *')).find((x) => (x.textContent || '').trim() === '夜间')
      if (btn) btn.click()
    })
    await p.waitForTimeout(600)
  }
  await b.close()
})()
