/**
 * v2.46.93 掼蛋竖屏 rotate90 探针：实测「挪左/挪右按钮」与四家出牌区屏幕坐标，
 * 验证我方出牌(thz-0)是否落在两按钮正中间、且不与对家(thz-2)重叠。仅开发用。
 * 用法：cd frontend && node _probe_gd_mid.cjs
 */
const { chromium } = require('playwright')

;(async () => {
  const browser = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await browser.newContext({ viewport: { width: 393, height: 852 }, deviceScaleFactor: 2 })
  const page = await ctx.newPage()
  const logs = []
  page.on('console', (m) => { if (m.type() === 'error') logs.push('err: ' + m.text()) })
  page.on('pageerror', (e) => logs.push('pageerror: ' + e.message))

  await page.goto('http://127.0.0.1:5199/_probe.html?g=gd', { waitUntil: 'domcontentloaded', timeout: 30000 })
  await page.waitForTimeout(1200)

  // 我方先出一张单牌，触发 AI 跟牌；等到四家都有 who 胶囊（或超时 40s）
  try {
    await page.$eval('.gd-hand .gt-card', (el) => el.click())
    await page.waitForTimeout(300)
    const play = await page.$('.gd-play-big')
    if (play && !(await play.isDisabled())) await play.click()
  } catch (e) { console.log('PLAY_ERR: ' + String(e).slice(0, 80)) }
  // 我方先出一张单牌，触发 AI 跟牌
  try {
    await page.$eval('.gd-hand .gt-card', (el) => el.click())
    await page.waitForTimeout(300)
    const play = await page.$('.gd-play-big')
    if (play && !(await play.isDisabled())) await play.click()
  } catch (e) { console.log('PLAY_ERR: ' + String(e).slice(0, 80)) }

  // 轮询采样：等到「我方 thz-0 与对家 thz-2 同时有内容」的瞬间再量（AI 会跟牌/清桌，需抓拍）
  const grab = () => page.evaluate(() => {
    const box = (el) => { const r = el.getBoundingClientRect(); return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) } }
    const q = (s) => document.querySelector(s)
    const t0 = q('.gd-thz-0'), t2 = q('.gd-thz-2')
    const b0 = t0 ? box(t0) : null, b2 = t2 ? box(t2) : null
    return { b0, b2, has0: !!(b0 && b0.w > 0), has2: !!(b2 && b2.w > 0) }
  })
  let sample = null
  for (let i = 0; i < 100; i++) {
    sample = await grab()
    if (sample.has0 && sample.has2) break
    await page.waitForTimeout(250)
  }

  const info = await page.evaluate(() => {
    const box = (el) => {
      const r = el.getBoundingClientRect()
      return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) }
    }
    const q = (s) => document.querySelector(s)
    const qa = (s) => Array.from(document.querySelectorAll(s))
    const btns = qa('.gd-hand-tools .gt-btn').map((b) => ({ t: b.textContent.trim(), ...box(b) }))
    const center = q('.gd-center'), tools = q('.gd-hand-tools'), hand = q('.gd-hand-zone') || q('.gd-hand')
    // 两枚钉按钮（挪左/挪右）的中点
    const pins = btns.filter((b) => b.t === '挪左' || b.t === '挪右')
    const mid = pins.length === 2 ? {
      x: Math.round(pins[0].x + pins[0].w / 2 + pins[1].x + pins[1].w / 2) / 2,
      y: Math.round((pins[0].y + pins[0].h / 2 + pins[1].y + pins[1].h / 2) / 2),
    } : null
    return {
      vw: innerWidth, vh: innerHeight,
      isLow: !!q('.gd-center.is-low'),
      center: center ? box(center) : null,
      tools: tools ? box(tools) : null,
      hand: hand ? box(hand) : null,
      btns, pinsMid: mid,
    }
  })
  // 采样到的 thz 盒子在 Node 侧合并（page.evaluate 里拿不到 Node 变量）
  info.thz0 = sample ? sample.b0 : null
  info.thz2 = sample ? sample.b2 : null
  info.thz0center = info.thz0 ? { x: Math.round(info.thz0.x + info.thz0.w / 2), y: Math.round(info.thz0.y + info.thz0.h / 2) } : null
  info.thz2center = info.thz2 ? { x: Math.round(info.thz2.x + info.thz2.w / 2), y: Math.round(info.thz2.y + info.thz2.h / 2) } : null
  // 重叠判定（屏幕坐标下两矩形是否相交）
  if (info.thz0 && info.thz2) {
    const a = info.thz0, b = info.thz2
    info.overlap = !(a.x + a.w <= b.x || b.x + b.w <= a.x || a.y + a.h <= b.y || b.y + b.h <= a.y)
  }
  console.log(JSON.stringify(info, null, 1))
  if (logs.length) console.log('LOGS: ' + logs.slice(0, 6).join(' | '))
  await page.screenshot({ path: '../artifacts/_probe/gd-portrait-mid.png' })
  await browser.close()
})()
