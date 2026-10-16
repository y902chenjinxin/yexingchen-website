/**
 * 麻将布局探针：量化「桌面空地」浪费。用法：cd frontend && node _probe_mj_layout.cjs
 * 加载 /_probe.html?g=mj（合成数据），在手机横屏分辨率下截图并量各区域盒子。
 */
const { chromium } = require('playwright')

;(async () => {
  const W = 780, H = 390
  const browser = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 })
  const page = await ctx.newPage()
  const logs = []
  page.on('console', (m) => { if (m.type() === 'error') logs.push('err: ' + m.text()) })
  page.on('pageerror', (e) => logs.push('pageerror: ' + e.message))

  await page.goto(`http://127.0.0.1:5199/_probe.html?g=mj&size=big`, { waitUntil: 'domcontentloaded', timeout: 30000 })
  await page.waitForTimeout(1500)

  const info = await page.evaluate(() => {
    const box = (el) => { const r = el.getBoundingClientRect(); return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) } }
    const q = (s) => document.querySelector(s)
    const qa = (s) => Array.from(document.querySelectorAll(s))
    const mj = q('.mj'), table = q('.mj-table'), center = q('.mj-center')
    const seats = qa('.mj-seat').map((s) => ({ cls: [...s.classList].find((c) => c.startsWith('mj-seat-')) || s.className, ...box(s) }))
    const dis = qa('.mj-dis').map((s) => ({ cls: [...s.classList].filter((c) => c.startsWith('mj-dis-'))[0], ...box(s) }))
    const hand = q('.mj-hand')
    return {
      vw: innerWidth, vh: innerHeight,
      mj: mj ? box(mj) : null,
      table: table ? box(table) : null,
      center: center ? box(center) : null,
      centerMaxW: center ? getComputedStyle(center).maxWidth : null,
      centerPad: center ? getComputedStyle(center).padding : null,
      seats, dis,
      hand: hand ? box(hand) : null,
    }
  })
  // 计算各丢弃区真实占用的牌盒（用 .gt-tile.mini 数量与单牌大小估占用）
  console.log(JSON.stringify(info, null, 1))
  await page.screenshot({ path: '../artifacts/_probe/mj-landscape.png' })
  if (logs.length) console.log('LOGS: ' + logs.slice(0, 6).join(' | '))
  await browser.close()
})()
