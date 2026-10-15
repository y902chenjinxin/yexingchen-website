/**
 * v2.46.90 掼蛋竖屏 rotate90 探针（仅开发用）
 * 验证项：四家出牌区是否呈菱形散开（不叠成一条）、席位头像尺寸是否稳定。
 * 用法：cd frontend && node _probe_gd_portrait.cjs
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
  let who = []
  for (let w = 0; w < 80; w++) {
    who = await page.$$eval('.gd-thz-who', (els) => els.map((e) => e.textContent.trim())).catch(() => [])
    if (who.length >= 4) break
    await page.waitForTimeout(500)
  }

  const info = await page.evaluate(() => {
    const box = (el) => {
      const r = el.getBoundingClientRect()
      return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) }
    }
    const q = (s) => document.querySelector(s)
    const thz = Array.from(document.querySelectorAll('.gd-thz')).map((el) => ({
      cls: el.className.replace('gd-thz ', ''),
      who: el.querySelector('.gd-thz-who')?.textContent.trim() || null,
      box: box(el),
    }))
    const seats = Array.from(document.querySelectorAll('.gd-table > .gd-zone .gt-seat, .gd-table > button ~ .gt-seat')).map((el) => ({
      cls: el.className,
      box: box(el),
      av: el.querySelector('.gt-seat-av') ? box(el.querySelector('.gt-seat-av')) : null,
      badge: !!el.querySelector('.gt-seat-badge'),
    }))
    return {
      vw: innerWidth, vh: innerHeight,
      isLow: !!q('.gd-center.is-low'),
      table: q('.gd-table') ? box(q('.gd-table')) : null,
      center: q('.gd-center') ? box(q('.gd-center')) : null,
      thz, seats,
      whoText: Array.from(document.querySelectorAll('.gd-thz-who')).map((e) => e.textContent.trim()),
    }
  })
  console.log(JSON.stringify(info, null, 1))
  console.log('WHO: ' + JSON.stringify(who))
  if (logs.length) console.log('LOGS: ' + logs.slice(0, 6).join(' | '))
  await page.screenshot({ path: '../artifacts/_probe/gd-portrait-baseline.png' })
  await browser.close()
})()
