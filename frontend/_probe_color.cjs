/**
 * 配色探针（v2.46.312）：本地渲染「记账页 + 关系页」，看颜色是否统一
 *   node _probe_color.cjs
 * 只 mock 接口，不进后端。
 */
const { chromium } = require('playwright')
const BASE = 'http://localhost:5301'
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url')
const JWT = [
  b64u({ alg: 'HS256', typ: 'JWT' }),
  b64u({ sub: '1', exp: Math.floor(Date.now() / 1000) + 86400 * 30 }),
  'sig',
].join('.')

const CATS = {
  expense: [
    { key: '餐饮', icon: '🍜' }, { key: '交通', icon: '🚇' }, { key: '购物', icon: '🛍️' },
    { key: '居家', icon: '🏠' }, { key: '娱乐', icon: '🎮' }, { key: '医疗', icon: '💊' },
    { key: '教育', icon: '📚' }, { key: '人情', icon: '🎁' }, { key: '其他', icon: '🧾' },
    { key: '断链罚金', icon: '⚖️' },
    { key: '水电费', icon: '💡', is_custom: true }, { key: '网上订阅', icon: '📱', is_custom: true },
    { key: '旅游', icon: '✈️', is_custom: true },
  ],
  income: [{ key: '工资', icon: '💼' }, { key: '奖金', icon: '🏅' }],
  hidden_builtin: { expense: [], income: [] },
}

const REL = [
  { id: 1, name: '孟瑾', relation: '丈母娘', intimacy: 4, overdue: false, last_text: '还没记过' },
  { id: 2, name: '罗香宝', relation: '母亲', intimacy: 5, overdue: true, last_text: '还没记过' },
  { id: 3, name: '郭丽莎', relation: '老婆', intimacy: 5, overdue: false, last_text: '还没记过' },
]

;(async () => {
  const b = await chromium.launch()
  const ctx = await b.newContext({ viewport: { width: 1180, height: 760 }, deviceScaleFactor: 2 })
  await ctx.route(/localhost:5301\/api\//, (r) => {
    const u = r.request().url()
    const j = (d) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: d }) })
    if (/\/api\/finance\/categories/.test(u)) return j(CATS)
    if (/\/api\/finance\/summary/.test(u)) return j({ income: 0, expense: 0, balance: 0, categories: [], trends: [], days: [] })
    if (/\/api\/finance\/funds/.test(u)) return j({ list: [], funds: [] })
    if (/\/api\/finance\/transactions/.test(u)) return j({ list: [], total: 0 })
    if (/\/api\/finance\/member-breakdown/.test(u)) return j({ list: [] })
    if (/\/api\/relations\/dashboard/.test(u)) return j({ birthdays: [{ id: 1, name: '陈金鑫', days: 5, label: '5 天后生日 · 农历' }], overdue: [], overdue_total: 0, blind: { id: 2, name: '罗香宝', topics: '' } })
    if (/\/api\/relations/.test(u)) return j({ items: REL, total: REL.length })
    return j({ list: [], total: 0 })
  })
  await ctx.addInitScript((t) => localStorage.setItem('token', t), JWT)
  const p = await ctx.newPage()
  p.on('pageerror', (e) => console.log('[pageerror]', e.message.slice(0, 120)))

  for (const [path, name] of [['/finance', 'finance'], ['/relations', 'relations']]) {
    await p.goto(`${BASE}${path}`, { waitUntil: 'domcontentloaded', timeout: 60000 })
    await p.waitForTimeout(2200)
    if (name === 'finance') {
      await p.evaluate(() => {
        const el = Array.from(document.querySelectorAll('button')).find((x) => /记一笔/.test(x.textContent || ''))
        el && el.click()
      })
      await p.waitForTimeout(900)
      await p.evaluate(() => {
        const el = document.querySelector('.fin-cats')
        el && el.scrollIntoView({ block: 'center' })
      })
      await p.waitForTimeout(400)
    }
    const info = await p.evaluate(() => {
      const pick = (sel) => {
        const el = document.querySelector(sel)
        if (!el) return null
        const c = getComputedStyle(el)
        return { bg: c.backgroundColor, color: c.color, border: c.borderTopColor }
      }
      return {
        cue: pick('.rl-cue'),
        cueText: pick('.rl-cue-row b'),
        catActive: pick('.fin-cat.active'),
        catIdle: pick('.fin-cat:not(.active)'),
        fundActive: pick('.fin-fund.active'),
        primaryBtn: pick('.fin-btn.primary'),
        rawIcon: !!document.querySelector('.ledger-icon.is-raw'),
      }
    })
    console.log(`[${name}]`, JSON.stringify(info))
    await p.screenshot({ path: `artifacts/_probe/color_${name}.png` })
  }
  await b.close()
})()
