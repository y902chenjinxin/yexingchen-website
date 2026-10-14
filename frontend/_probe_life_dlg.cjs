/**
 * v2.46.79 体重弹窗巡检（仅开发用）：验证 teleport 到 body 的 el-dialog
 * 在移动端（html.m-app）下主按钮/表面/输入控件的宣纸令牌兜底是否生效。
 * 本地 vite 5199 跑未发布代码，/api/** 代理到生产取登录态。
 * 用法：node _probe_life_dlg.cjs
 */
const { chromium } = require('playwright')

const BASE = 'http://127.0.0.1:5199'
const PROD = 'https://yexingchen.cn'

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

  const out = {}
  await page.goto(BASE + '/life/weight?m=1', { waitUntil: 'domcontentloaded', timeout: 30000 })
  await page.waitForTimeout(2500)
  out.mAppClass = await page.evaluate(() => document.documentElement.classList.contains('m-app'))

  await page.click('.life-tb .el-button--primary')
  await page.waitForTimeout(900)
  out.dialogOpen = !!(await page.$('.el-overlay .el-dialog'))
  out.btn = await page.$eval('.el-overlay .el-dialog .el-button--primary', (e) => {
    const cs = getComputedStyle(e)
    return { text: e.textContent.trim(), bg: cs.backgroundColor, fg: cs.color, weight: cs.fontWeight }
  }).catch(() => null)
  out.cancelBtn = await page.$eval('.el-overlay .el-dialog .el-button:not(.el-button--primary)', (e) => {
    const cs = getComputedStyle(e)
    return { text: e.textContent.trim(), bg: cs.backgroundColor, fg: cs.color }
  }).catch(() => null)
  out.dialogBg = await page.$eval('.el-overlay .el-dialog', (e) => getComputedStyle(e).backgroundColor).catch(() => null)
  await page.screenshot({ path: '../artifacts/_probe/life-weight-dlg.png' })

  // 打开「家人」下拉，看 popper 表面兜底
  await page.click('.el-overlay .el-dialog .el-select__wrapper')
  await page.waitForTimeout(600)
  out.popperBg = await page.$eval('.el-popper.el-select__popper, .el-popper', (e) => getComputedStyle(e).backgroundColor).catch(() => null)
  await page.screenshot({ path: '../artifacts/_probe/life-weight-select.png' })

  console.log(JSON.stringify(out, null, 1))
  console.log('ERRS:', errs.length ? errs.slice(0, 4) : 'none')
  await browser.close()
})()
