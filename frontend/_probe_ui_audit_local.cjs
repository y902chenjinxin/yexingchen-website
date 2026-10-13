/**
 * 本地 UI 代码 + 生产 API 巡检（仅开发用）
 * vite 5199 跑本地未发布代码；/api/** 经 route 代理到生产，token 用生产登录获取。
 * 用法：node _probe_ui_audit_local.cjs
 */
const { chromium } = require('playwright')

const BASE = 'http://[::1]:5199'
const PROD = 'https://yexingchen.cn'
const PAGES = [
  ['/login', 'login'],
  ['/workbench', 'workbench'],
  ['/modules', 'modules'],
  ['/profile', 'profile'],
  ['/music', 'music'],
  ['/video', 'video'],
  ['/notes', 'notes'],
  ['/assistant', 'assistant'],
  ['/novel', 'novel'],
  // v2.46.69 九项巡检补充
  ['/notes/new', 'note-editor'],
  ['/tool/countdown', 'countdown'],
  ['/tool/idphoto', 'idphoto'],
  ['/tool/games', 'games'],
]

;(async () => {
  const loginRes = await fetch(PROD + '/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'admin@yexingchen.cn', password: 'admin123' }),
  })
  const token = (await loginRes.json())?.data?.token
  if (!token) { console.log('LOGIN_FAIL'); return }

  const browser = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true })
  // /api/** → 生产（本地后端 JWT 密钥与生产不一致，直接代生产数据）
  await ctx.route((u) => u.pathname.startsWith('/api/'), async (route) => {
    const u = new URL(route.request().url())
    try {
      const resp = await route.fetch({ url: PROD + u.pathname + u.search })
      const body = await resp.body()
      const headers = { ...resp.headers() }
      delete headers['content-encoding']
      delete headers['content-length']
      delete headers['transfer-encoding']
      route.fulfill({ status: resp.status(), headers, body })
    } catch (e) { route.abort() }
  })
  // vite 代理把 /music 文档请求转给本地后端（返回 JSON）——拦截文档请求回 index.html
  await ctx.route((u) => u.pathname === '/music', async (route) => {
    try {
      const resp = await route.fetch({ url: BASE + '/?m=1' })
      const body = await resp.body()
      const h = { ...resp.headers() }
      h['content-type'] = 'text/html'
      await route.fulfill({ status: 200, headers: h, body })
    } catch { await route.abort() }
  })

  const page = await ctx.newPage()
  await page.goto(BASE + '/login?m=1', { waitUntil: 'domcontentloaded', timeout: 40000 })

  for (const [path, name] of PAGES) {
    try {
      if (name === 'login') {
        await page.evaluate(() => localStorage.removeItem('token'))
        await page.goto(BASE + '/login?m=1', { waitUntil: 'domcontentloaded', timeout: 40000 })
        await page.waitForTimeout(2600)
        await page.screenshot({ path: `artifacts/_probe/ui-audit2-${name}.png` })
        console.log('SHOT login (pre-auth)')
        await page.evaluate((t) => localStorage.setItem('token', t), token)
        continue
      }
      await page.goto(BASE + path + '?m=1', { waitUntil: 'domcontentloaded', timeout: 40000 })
      await page.waitForTimeout(3000)
      await page.evaluate(() => window.scrollTo(0, 0))
      await page.waitForTimeout(300)
      await page.screenshot({ path: `artifacts/_probe/ui-audit2-${name}.png` })
      console.log('SHOT ' + name)
    } catch (e) {
      console.log(`SHOT ${name} FAIL ` + e.message.split('\n')[0])
    }
  }
  await browser.close()
  console.log('AUDIT_DONE')
})()
