/** 弹幕 / 转盘工具：暗夜玻璃改版验收（v2.46.314）
 *  直接改 <html data-theme> 切换主题（所有配色规则都是属性选择器，立即生效），
 *  量关键元素的计算色并截图。不需要后端（本地 mock）。 */
const { chromium } = require('playwright')
const BASE = process.env.PROBE_BASE || 'http://localhost:5301'
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url')
const JWT = [b64u({ alg: 'HS256', typ: 'JWT' }), b64u({ sub: '1', exp: Math.floor(Date.now() / 1000) + 86400 * 30 }), 'sig'].join('.')

const PAGES = [
  {
    path: '/tool/danmu',
    name: 'danmu',
    sels: ['.dm-color-block', '.dm-dir', '.dm-dir.on', '.dm-input', '.dm-label', '.dm-swatch.on'],
  },
  {
    path: '/tool/spin',
    name: 'spin',
    sels: ['.sp-label', '.sp-input', '.sp-btn.primary', '.sp-btn.ghost', '.sp-cfg-card'],
    before: async (p) => {
      await p.evaluate(() => document.querySelector('.sp-icon-btn')?.click())
      await p.waitForTimeout(600)
    },
  },
]

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

  for (const pg of PAGES) {
    await p.goto(`${BASE}${pg.path}`, { waitUntil: 'domcontentloaded', timeout: 60000 })
    await p.waitForTimeout(2200)
    if (pg.before) await pg.before(p)
    for (const theme of ['night', 'day']) {
      await p.evaluate((t) => { document.documentElement.dataset.theme = t }, theme)
      await p.waitForTimeout(450)
      const out = await p.evaluate((sels) => {
        const pick = (s) => {
          const el = document.querySelector(s)
          if (!el) return `${s}: (none)`
          const c = getComputedStyle(el)
          const lum = (str) => {
            const m = String(str).match(/[\d.]+/g)
            if (!m) return -1
            const [r, g, b, a] = m.map(Number)
            if (a !== undefined && a < 0.06) return -1
            return Math.round((0.299 * r + 0.587 * g + 0.114 * b))
          }
          return `${s}: bgLum=${lum(c.backgroundColor)} img=${c.backgroundImage.includes('gradient') ? 'grad' : '-'} color=${c.color} colorLum=${lum(c.color)}`
        }
        return { theme: document.documentElement.dataset.theme, rows: sels.map(pick) }
      }, pg.sels)
      console.log(`\n[${pg.name}] theme=${out.theme}`)
      out.rows.forEach((r) => console.log('   ', r))
      await p.screenshot({ path: `artifacts/_probe/dm_${pg.name}_${theme}.png` })
    }
  }
  await b.close()
})()
