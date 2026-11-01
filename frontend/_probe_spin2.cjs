const { chromium } = require('playwright')
const BASE = 'http://localhost:5301'
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url')
const JWT = [b64u({ alg: 'HS256', typ: 'JWT' }), b64u({ sub: '1', exp: Math.floor(Date.now() / 1000) + 86400 * 30 }), 'sig'].join('.')
;(async () => {
  const b = await chromium.launch()
  const ctx = await b.newContext({ viewport: { width: 1180, height: 900 }, deviceScaleFactor: 2 })
  await ctx.route(/localhost:5301\/api\//, (r) => {
    const u = r.request().url()
    const j = (d) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: d }) })
    if (/\/api\/auth\/me/.test(u)) return j({ id: 1, username: 'probe', is_super_admin: 1 })
    return j({ list: [], total: 0 })
  })
  await ctx.addInitScript((t) => localStorage.setItem('token', t), JWT)
  const p = await ctx.newPage()
  p.on('pageerror', (e) => console.log('[pageerror]', e.message.slice(0, 120)))
  await p.goto(`${BASE}/tool/spin`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForTimeout(2400)
  for (const theme of ['night', 'day']) {
    await p.evaluate((t) => { document.documentElement.dataset.theme = t }, theme)
    await p.waitForTimeout(500)
    const info = await p.evaluate(() => {
      const w = document.querySelector('.sp-wheel')
      const lab = document.querySelector('.sp-seg-label')
      const hub = document.querySelector('.sp-hub')
      return {
        wheelBg: getComputedStyle(w).backgroundImage.slice(0, 120),
        labelColor: lab ? getComputedStyle(lab).color : '-',
        hubBorder: hub ? getComputedStyle(hub).borderTopColor : '-',
      }
    })
    console.log(`\n[${theme}]`, JSON.stringify(info, null, 1))
    await p.screenshot({ path: `artifacts/_probe/spin2_${theme}.png` })
  }
  await b.close()
})()
