/**
 * 本地书架探针（v2.46.308）
 * 目的：不出网、不碰后端，用 mock 数据把 /novel 书架页在 390×844 触摸环境下渲染出来，
 *       验证「无框 / 三列 / 不分页 / 搜索 + 三个图标」是否符合番茄式预期。
 * 用法：先 `npx vite --port 5299`，再 `node _probe_shelf.cjs`
 */
const { chromium } = require('playwright')
const path = require('path')
const BASE = 'http://localhost:5301'
/* 假 JWT：前端守卫只看 payload.exp，不看签名 */
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url')
const FAKE_JWT = [
  b64u({ alg: 'HS256', typ: 'JWT' }),
  b64u({ sub: '1', exp: Math.floor(Date.now() / 1000) + 86400 * 30 }),
  'sig',
].join('.')

const BOOKS = [
  { id: 1, title: '诸神愚戏', author: '未知作者', chapter_count: 1463, progress_percent: 0, is_favorite: 0 },
  { id: 2, title: '阳神', author: '梦入神机', chapter_count: 783, progress_percent: 0.12, is_favorite: 1 },
  { id: 3, title: '无限恐怖', author: 'zhttty', chapter_count: 769, progress_percent: 0.46, is_favorite: 0 },
  { id: 4, title: '万妖之祖', author: '未知作者', chapter_count: 1281, progress_percent: 0, is_favorite: 0 },
  { id: 5, title: '圣王', author: '梦入神机', chapter_count: 1704, progress_percent: 0.8, is_favorite: 0 },
  { id: 6, title: '神秘复苏', author: '佛前献花', chapter_count: 1636, progress_percent: 0.03, is_favorite: 0 },
  { id: 7, title: '全职高手', author: '蝴蝶蓝', chapter_count: 1728, progress_percent: 0.27, is_favorite: 0 },
  { id: 8, title: '雪中悍刀行', author: '烽火戏诸侯', chapter_count: 1024, progress_percent: 0, is_favorite: 0 },
  { id: 9, title: '斗罗大陆', author: '唐家三少', chapter_count: 336, progress_percent: 1, is_favorite: 0 },
]

;(async () => {
  const b = await chromium.launch()
  const ctx = await b.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
  })
  const p = await ctx.newPage()
  p.on('pageerror', (e) => console.log('[pageerror]', e.message.slice(0, 200)))

  await ctx.route(/localhost:5301\/api\//, async (route) => {
    const url = route.request().url()
    const json = (data) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data }) })
    if (/\/api\/novels\?/.test(url) || /\/api\/novels$/.test(url)) return json({ list: BOOKS, total: BOOKS.length })
    if (/\/api\/auth\/me/.test(url)) return json({ id: 1, username: 'probe', role: 'admin', is_super_admin: 1, menus: [] })
    return json({ list: [], total: 0 })
  })

  await ctx.addInitScript((tok) => {
    localStorage.setItem('token', tok)
    localStorage.setItem('user', JSON.stringify({ id: 1, username: 'probe', role: 'admin' }))
  }, FAKE_JWT)
  p.on('console', (m) => { if (m.type() === 'error') console.log('[console]', m.text().slice(0, 200)) })
  p.on('framenavigated', (f) => { if (f === p.mainFrame()) console.log('[nav]', f.url()) })
  await p.goto(`${BASE}/novel`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForSelector('.ns-card', { timeout: 15000 }).catch(() => console.log('[warn] 没有 .ns-card'))
  console.log('[url]', p.url(), '[html]', (await p.content()).length)
  await p.waitForTimeout(1200)

  const info = await p.evaluate(() => {
    const pane = document.querySelector('.manage-pane')
    const cs = pane ? getComputedStyle(pane) : null
    const shelf = document.querySelector('.novel-shelf')
    const cards = document.querySelectorAll('.ns-card')
    const cs2 = shelf ? getComputedStyle(shelf) : null
    return {
      paneBorder: cs && `${cs.borderTopWidth} ${cs.borderTopColor}`,
      paneBg: cs && cs.backgroundColor,
      panePad: cs && cs.padding,
      paneRadius: cs && cs.borderRadius,
      cols: cs2 && cs2.gridTemplateColumns,
      cards: cards.length,
      pager: !!document.querySelector('.pager-wrap'),
      vw: window.innerWidth,
      card0: cards[0] ? cards[0].getBoundingClientRect().width.toFixed(1) : 0,
    }
  })
  console.log('[shelf]', JSON.stringify(info))

  const out = path.join(__dirname, 'artifacts', '_probe', 'shelf_390.png')
  await p.screenshot({ path: out })
  console.log('shot ->', out)

  // 管理态（选择模式）
  await p.click('.nv-ic-btn[aria-label="管理书架"]')
  await p.waitForTimeout(400)
  await p.click('.ns-card:nth-child(2)')
  await p.click('.ns-card:nth-child(5)')
  await p.waitForTimeout(300)
  const out2 = path.join(__dirname, 'artifacts', '_probe', 'shelf_390_sel.png')
  await p.screenshot({ path: out2 })
  console.log('shot ->', out2)

  await b.close()
})()
