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
  await p.goto(`${BASE}/tool/spin`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForTimeout(2400)
  for (const theme of ['night']) {
    await p.evaluate((t) => { document.documentElement.dataset.theme = t }, theme)
    await p.waitForTimeout(400)
    console.log(theme, await p.evaluate(() => ({
      cards: document.querySelectorAll('.sp-cfg-card').length,
      hub: (() => { const e = document.querySelector('.sp-hub'); return e ? getComputedStyle(e).borderColor + ' | ' + getComputedStyle(e).backgroundImage.slice(0, 40) : 'none' })(),
      wheel: (() => { const e = document.querySelector('.sp-wheel'); return e ? getComputedStyle(e).boxShadow.slice(0, 80) : 'none' })(),
    })))
    await p.screenshot({ path: 'artifacts/_probe/spin_play_night.png' })
  }
  // 对照：棋类大厅（夜星说「像棋牌那里就挺好」，用它做基准）
  await p.goto(`${BASE}/tool/games`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForTimeout(2400)
  await p.evaluate(() => { document.documentElement.dataset.theme = 'night' })
  await p.waitForTimeout(400)
  await p.screenshot({ path: 'artifacts/_probe/ref_games_night.png' })
  await b.close()
})()
