const { chromium } = require('playwright')
const BASE = 'http://localhost:5301'
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url')
const JWT = [b64u({ alg: 'HS256', typ: 'JWT' }), b64u({ sub: '1', exp: Math.floor(Date.now() / 1000) + 86400 * 30 }), 'sig'].join('.')
;(async () => {
  const b = await chromium.launch()
  const ctx = await b.newContext({ viewport: { width: 1180, height: 900 } })
  await ctx.route(/localhost:5301\/api\//, (r) => {
    const u = r.request().url()
    const j = (d) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: d }) })
    if (/\/api\/auth\/me/.test(u)) return j({ id: 1, username: 'probe', is_super_admin: 1 })
    return j({ list: [], total: 0 })
  })
  await ctx.addInitScript((t) => localStorage.setItem('token', t), JWT)
  const p = await ctx.newPage()
  await p.goto(`${BASE}/tool/spin`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForTimeout(2400)
  await p.evaluate(() => { document.documentElement.dataset.theme = 'night' })
  await p.waitForTimeout(400)
  const scan = async (tag) => {
    const out = await p.evaluate(() => {
      const lum = (s) => { const m = String(s).match(/[\d.]+/g); if (!m) return -1; const [r,g,bl,a] = m.map(Number); if (a !== undefined && a < 0.5) return -1; return Math.round(0.299*r+0.587*g+0.114*bl) }
      const res = []
      document.querySelectorAll('.sp-play *, .sp-edit *').forEach((el) => {
        const c = getComputedStyle(el)
        const L = lum(c.backgroundColor)
        const r = el.getBoundingClientRect()
        if (L > 190 && r.width * r.height > 1200) res.push(`${el.tagName.toLowerCase()}.${(el.className||'').toString().split(' ')[0]} ${Math.round(r.width)}x${Math.round(r.height)} lum=${L} bg=${c.backgroundColor}`)
      })
      return res
    })
    console.log(`[${tag}] 亮块 ${out.length} 处`); out.forEach((x) => console.log('   ', x))
  }
  await scan('play')
  await p.evaluate(() => document.querySelector('.sp-icon-btn')?.click())
  await p.waitForTimeout(700)
  await scan('edit')
  await b.close()
})()
