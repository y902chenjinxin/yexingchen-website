/**
 * v2.46.76 新工具巡检（仅开发用）：手持弹幕 / 自定义抽签 / 密码批量 / 工作台 14 格
 * 本地 vite 5199 跑未发布代码，/api/** 代理到生产取登录态。
 * 用法：node _probe_newtools.cjs
 */
const { chromium } = require('playwright')

const BASE = 'http://[::1]:5199'
const PROD = 'https://yexingchen.cn'
const PAGES = [
  ['/workbench', 'wb-grid'],
  ['/tool/danmu', 'danmu'],
  ['/tool/spin', 'spin'],
  ['/tool/password', 'password'],
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
  await ctx.route((u) => u.pathname.startsWith('/api/'), async (route) => {
    const u = new URL(route.request().url())
    try {
      const resp = await route.fetch({ url: PROD + u.pathname + u.search })
      const body = await resp.body()
      const headers = { ...resp.headers() }
      delete headers['content-encoding']; delete headers['content-length']; delete headers['transfer-encoding']
      route.fulfill({ status: resp.status(), headers, body })
    } catch { route.abort() }
  })
  await ctx.addInitScript((t) => localStorage.setItem('token', t), token)

  const page = await ctx.newPage()
  const errs = []
  page.on('pageerror', (e) => errs.push('pageerror: ' + e.message))
  page.on('console', (m) => { if (m.type() === 'error') errs.push('err: ' + m.text().slice(0, 160)) })

  const out = {}
  for (const [path, key] of PAGES) {
    await page.goto(BASE + path + '?m=1', { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForTimeout(2200)
    await page.screenshot({ path: `../artifacts/_probe/nt-${key}.png` })
    if (key === 'wb-grid') {
      out.gridCount = await page.$$eval('.abb-grid .abb-cell', (els) => els.map((e) => e.querySelector('.abb-cell__lab')?.textContent?.trim()))
    }
    if (key === 'danmu') {
      await page.fill('#dm-text', '丽莎姐姐最棒')
      await page.click('.dm-show-btn')
      await page.waitForTimeout(800)
      out.danmuStage = !!(await page.$('.dm-stage'))
      out.danmuText = await page.$eval('.dm-text', (e) => e.textContent.trim()).catch(() => null)
      await page.screenshot({ path: '../artifacts/_probe/nt-danmu-stage.png' })
      await page.click('.dm-exit')
      out.danmuClosed = !(await page.$('.dm-stage'))
    }
    if (key === 'spin') {
      out.segLabels = await page.$$eval('.sp-seg-label', (els) => els.map((e) => e.textContent.trim()))
      await page.click('.sp-hub')
      await page.waitForTimeout(4800)
      out.spinResult = await page.$eval('.sp-result-text', (e) => e.textContent.trim()).catch(() => null)
      await page.screenshot({ path: '../artifacts/_probe/nt-spin-result.png' })
    }
    if (key === 'password') {
      await page.click('.pw-generate')
      await page.waitForTimeout(400)
      out.batchCount = await page.$$eval('.pw-batch-item', (els) => els.length)
    }
  }
  console.log(JSON.stringify(out, null, 1))
  console.log('ERRS:', errs.length ? errs.slice(0, 6) : 'none')
  await browser.close()
})()
