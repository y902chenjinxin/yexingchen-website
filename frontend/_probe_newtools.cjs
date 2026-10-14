/**
 * v2.46.76 新工具巡检（仅开发用）：手持弹幕 / 自定义抽签 / 密码批量 / 工作台 14 格
 * 本地 vite 5199 跑未发布代码，/api/** 代理到生产取登录态。
 * 用法：node _probe_newtools.cjs
 */
const { chromium } = require('playwright')

const BASE = 'http://127.0.0.1:5199'
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
      // v2.46.80：200 字符上限 + 计数器
      out.danmuMax = await page.$eval('#dm-text', (e) => e.maxLength)
      await page.fill('#dm-text', 'x'.repeat(150))
      out.danmuCount = await page.$eval('.dm-count', (e) => e.textContent.trim())
      out.danmuLen = await page.$eval('#dm-text', (e) => e.value.length)
      // v2.46.80：手动输入 rgb → 前景实时变 #e9c877，输入框归一化
      const fgBox = (await page.$$('.dm-color-text'))[0]
      await fgBox.fill('rgb(233,200,119)')
      await page.waitForTimeout(250)
      out.danmuRgbInput = await fgBox.inputValue()
      out.danmuRgbFg = await page.$eval('.dm-color-cur', (e) => getComputedStyle(e).backgroundColor)
      // 非法值：标红但不改当前色；失焦回滚
      await fgBox.fill('not-a-color')
      out.danmuBad = await page.$eval('.dm-color-text', (e) => e.classList.contains('bad'))
      await page.evaluate(() => { document.activeElement?.blur() })
      out.danmuRollback = await fgBox.inputValue()
      // 配色板：点第二颗前景预设 + 第一颗背景预设
      await page.$$eval('.dm-color-block', (blocks) => blocks[0]?.querySelectorAll('.dm-swatch')[1]?.click())
      await page.$$eval('.dm-color-block', (blocks) => blocks[1]?.querySelectorAll('.dm-swatch')[0]?.click())
      out.danmuFg = await page.$eval('.dm-color-text', (e) => e.value)
      // 横屏模式 + 竖屏视口 → rotate90 兜底
      await page.click('.dm-dir:has-text("横屏")')
      await page.click('.dm-show-btn')
      await page.waitForTimeout(800)
      out.danmuStage = !!(await page.$('.dm-stage'))
      out.danmuText = await page.$eval('.dm-text', (e) => e.textContent.trim()).catch(() => null)
      out.danmuRot = await page.$eval('.dm-stage', (e) => {
        const cs = getComputedStyle(e)
        return { rot: e.classList.contains('is-rot'), w: e.style.width, h: e.style.height, tf: e.style.transform }
      }).catch(() => null)
      await page.screenshot({ path: '../artifacts/_probe/nt-danmu-rot.png' })
      await page.click('.dm-exit')
      out.danmuClosed = !(await page.$('.dm-stage'))
      // 真横屏视口 → 不旋转，铺满
      await page.setViewportSize({ width: 844, height: 390 })
      await page.click('.dm-show-btn')
      await page.waitForTimeout(600)
      out.danmuLand = await page.$eval('.dm-stage', (e) => {
        const r = e.getBoundingClientRect()
        return { rot: e.classList.contains('is-rot'), w: Math.round(r.width), h: Math.round(r.height) }
      }).catch(() => null)
      await page.screenshot({ path: '../artifacts/_probe/nt-danmu-land.png' })
      await page.click('.dm-exit')
      await page.setViewportSize({ width: 390, height: 844 })
    }
    if (key === 'spin') {
      out.spinPalette = await page.$eval('.sp-wheel', (e) => getComputedStyle(e).backgroundImage.slice(0, 90))
      out.segLabels = await page.$$eval('.sp-seg-label', (els) => els.map((e) => e.textContent.trim()))
      // v2.46.80：标签段中心居中断言——标签中心相对盘心的切向偏移应 ≈0（旧实现从径向线向右展开，偏右）
      out.segCenter = await page.evaluate(() => {
        const wheel = document.querySelector('.sp-wheel')
        const wr = wheel.getBoundingClientRect()
        const cx = wr.left + wr.width / 2, cy = wr.top + wr.height / 2
        const labels = [...wheel.querySelectorAll('.sp-seg-label')]
        const n = labels.length
        const worst = { off: 0, dist: 0 }
        labels.forEach((el, i) => {
          const r = el.getBoundingClientRect()
          const lx = r.left + r.width / 2 - cx, ly = r.top + r.height / 2 - cy
          const rad = (((i + 0.5) * 360) / n * Math.PI) / 180
          const rx = Math.sin(rad), ry = -Math.cos(rad)   // 径向（12 点起顺时针）
          const tx = Math.cos(rad), ty = Math.sin(rad)    // 切向
          worst.dist = Math.max(worst.dist, Math.abs(lx * rx + ly * ry - 86))
          worst.off = Math.max(worst.off, Math.abs(lx * tx + ly * ty))
        })
        return worst
      })
      await page.click('.sp-hub')
      await page.waitForTimeout(4800)
      out.spinResult = await page.$eval('.sp-result-text', (e) => e.textContent.trim()).catch(() => null)
      await page.screenshot({ path: '../artifacts/_probe/nt-spin-result.png' })
      // 多签组：新建 → 回主面卡片 2 张 → 切回首张 → 刷新后仍在（持久化）
      await page.click('.sp-cfg-add')
      await page.fill('#sp-name', '今晚谁做饭')
      await page.click('.sp-btn.primary')
      await page.waitForTimeout(300)
      out.spinCards = await page.$$eval('.sp-cfg-card', (els) => els.map((e) => e.querySelector('.sp-cfg-card-name')?.textContent?.trim()))
      await page.$$eval('.sp-cfg-card', (els) => els[0]?.click())
      out.spinActiveAfterSwitch = await page.$eval('.sp-cfg-card.on .sp-cfg-card-name', (e) => e.textContent.trim()).catch(() => null)
      await page.reload({ waitUntil: 'domcontentloaded' })
      await page.waitForTimeout(1500)
      out.spinCardsAfterReload = await page.$$eval('.sp-cfg-card', (els) => els.map((e) => e.querySelector('.sp-cfg-card-name')?.textContent?.trim()))
      await page.screenshot({ path: '../artifacts/_probe/nt-spin-strip.png' })
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
