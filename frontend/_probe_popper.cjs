/** 暗色主题下 Element Plus 弹层（下拉/选择器）底色检查
 *  用法：node _probe_popper.cjs  → 打印各弹层计算色 + 截图 */
const { chromium } = require('playwright')
const BASE = process.env.PROBE_BASE || 'http://localhost:5301'
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url')
const JWT = [b64u({ alg: 'HS256', typ: 'JWT' }), b64u({ sub: '1', exp: Math.floor(Date.now() / 1000) + 86400 * 30 }), 'sig'].join('.')

const CASES = [
  {
    path: '/finance',
    name: 'finance-cat',
    open: async (p) => {
      await p.evaluate(() => {
        const el = Array.from(document.querySelectorAll('button, .fin-btn')).find((x) => /分类|管理/.test(x.textContent || ''))
        el && el.click()
      })
      await p.waitForTimeout(900)
      // 点第一个图标下拉
      await p.evaluate(() => {
        const el = document.querySelector('.fin-cd-icon, .fin-cd-add .el-select')
        el && el.click()
      })
      await p.waitForTimeout(700)
    },
    sels: ['.el-dialog', '.el-select-dropdown', '.el-popper'],
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
  for (const c of CASES) {
    await p.goto(`${BASE}${c.path}`, { waitUntil: 'domcontentloaded', timeout: 60000 })
    await p.waitForTimeout(2200)
    await p.evaluate(() => { document.documentElement.dataset.theme = 'night' })
    await p.waitForTimeout(400)
    await c.open(p)
    const out = await p.evaluate((sels) => sels.map((s) => {
      const el = document.querySelector(s)
      if (!el) return `${s}: (none)`
      const cs = getComputedStyle(el)
      const r = el.getBoundingClientRect()
      return `${s}: ${Math.round(r.width)}x${Math.round(r.height)} bg=${cs.backgroundColor} color=${cs.color} cls=${el.className.toString().slice(0, 60)}`
    }), c.sels)
    console.log(`\n[${c.name}]`)
    out.forEach((x) => console.log('   ', x))
    await p.screenshot({ path: `artifacts/_probe/popper_${c.name}.png` })
  }
  await b.close()
})()
