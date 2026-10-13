/**
 * v2.46.72 掼蛋横屏改版 · 720×360 探针（仅开发用）
 *
 * 验证项：四区布局（左/顶/右/中央留白）、手牌 80% 宽 + 弧形、四座位出牌区、
 * 大按钮在视口内、无横向溢出、选牌自动识别牌型、记录浮层开合。
 * 用法：cd frontend && node _probe_gd2.cjs
 */
const { chromium } = require('playwright')

;(async () => {
  const browser = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await browser.newContext({ viewport: { width: 720, height: 360 }, deviceScaleFactor: 2 })
  const page = await ctx.newPage()
  const logs = []
  page.on('console', (m) => { if (m.type() === 'error') logs.push('err: ' + m.text()) })
  page.on('pageerror', (e) => logs.push('pageerror: ' + e.message))

  await page.goto('http://[::1]:5199/_probe.html?g=gd', { waitUntil: 'domcontentloaded', timeout: 30000 })
  await page.waitForTimeout(1500)
  await page.screenshot({ path: '../artifacts/_probe/gd2-open.png' })

  // 等第一家 AI 出牌（3~3.5s 思考 + 出牌），四座位出牌区应出现 who 胶囊
  let thzSeen = false
  for (let w = 0; w < 20; w++) {
    if (await page.$('.gd-thz .gd-thz-who')) { thzSeen = true; break }
    await page.waitForTimeout(500)
  }

  // 选一张牌：验证自动识别牌型标签
  let patLabel = null
  try {
    await page.$eval('.gd-hand .gt-card', (el) => el.click())
    await page.waitForTimeout(350)
    patLabel = await page.$eval('.gd-pat-label', (el) => el.textContent.replace(/\s+/g, ' ').trim())
  } catch (e) { patLabel = 'ERR ' + String(e).slice(0, 60) }
  await page.screenshot({ path: '../artifacts/_probe/gd2-select.png' })

  // 记录浮层开合
  let histToggle = null
  try {
    await page.$eval('.gd-hist-btn', (el) => el.click())
    await page.waitForTimeout(300)
    const visible = await page.$eval('.gd-history', (el) => getComputedStyle(el).display !== 'none')
    histToggle = { visibleAfterOpen: visible }
  } catch (e) { histToggle = { err: String(e).slice(0, 60) } }

  const info = await page.evaluate(() => {
    const q = (s) => document.querySelector(s)
    const box = (s) => {
      const el = q(s)
      if (!el) return null
      const r = el.getBoundingClientRect()
      return { w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x), y: Math.round(r.y) }
    }
    const handCards = Array.from(document.querySelectorAll('.gd-hand .gt-card'))
    const arcs = handCards.slice(0, 3).map((el) => {
      const c = getComputedStyle(el)
      return { rot: c.rotate, tr: c.translate }
    })
    return {
      vw: window.innerWidth, vh: window.innerHeight,
      scrollW: document.documentElement.scrollWidth,
      table: box('.gd-table'),
      zoneTop: box('.gd-zone-top'),
      zoneLeft: box('.gd-zone-left'),
      zoneRight: box('.gd-zone-right'),
      center: box('.gd-center'),
      thzWho: Array.from(document.querySelectorAll('.gd-thz-who')).map((e) => e.textContent.trim()),
      handZone: box('.gd-hand-zone'),
      hand: box('.gd-hand'),
      handRatio: (() => { const h = q('.gd-hand'); const t = q('.gd-table'); return h && t ? +(h.getBoundingClientRect().width / t.getBoundingClientRect().width).toFixed(2) : null })(),
      handN: handCards.length,
      arcSample: arcs,
      patLabel: box('.gd-pat-label'),
      tools: box('.gd-hand-tools'),
      passBig: box('.gd-pass-big'),
      playBig: box('.gd-play-big'),
      bigInVp: (() => {
        const a = q('.gd-pass-big'); const b = q('.gd-play-big')
        if (!a || !b) return null
        const ra = a.getBoundingClientRect(); const rb = b.getBoundingClientRect()
        return ra.right <= window.innerWidth + 1 && rb.right <= window.innerWidth + 1 && ra.bottom <= window.innerHeight + 1 && rb.bottom <= window.innerHeight + 1
      })(),
      turn: box('.gd-turnbox'),
      histBtn: box('.gd-hist-btn'),
      dividerN: document.querySelectorAll('.gd-hand-divider').length,
      overlapPairs: (() => {
        const rects = {
          左区: q('.gd-zone-left'), 右区: q('.gd-zone-right'), 顶部: q('.gd-zone-top'),
          中央: q('.gd-center'), 手牌: q('.gd-hand-zone'),
        }
        const keys = Object.keys(rects)
        const out = []
        for (let i = 0; i < keys.length; i++) {
          for (let j = i + 1; j < keys.length; j++) {
            const a = rects[keys[i]]; const b = rects[keys[j]]
            if (!a || !b) continue
            const ra = a.getBoundingClientRect(); const rb = b.getBoundingClientRect()
            const w = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left)
            const h = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top)
            if (w > 1 && h > 1) out.push(`${keys[i]}×${keys[j]} ${Math.round(w)}×${Math.round(h)}`)
          }
        }
        return out
      })(),
    }
  })
  console.log(JSON.stringify(info, null, 1))
  console.log('THZ_SEEN: ' + thzSeen, '| PAT_LABEL: ' + patLabel, '| HIST: ' + JSON.stringify(histToggle))

  // 自己出一张单牌 → 等三家 AI 跟牌（各 3~3.5s）→ 四座位出牌区应有 who 胶囊
  let thzAfterPlay = null
  try {
    // 前面选牌验证可能留下了选中态：先重选再单选一张
    const re = await page.$('.gd-hand-tools .gt-btn:last-child')
    if (re) await re.click()
    await page.waitForTimeout(200)
    await page.$eval('.gd-hand .gt-card', (el) => el.click())
    await page.waitForTimeout(250)
    const play = await page.$('.gd-play-big')
    const disabled = await play.isDisabled()
    if (disabled) thzAfterPlay = { err: '出牌按钮 disabled' }
    else {
      await play.click()
      let who = []
      for (let w = 0; w < 30; w++) {
        await page.waitForTimeout(500)
        who = await page.$$eval('.gd-thz-who', (els) => els.map((e) => e.textContent.trim()))
        if (who.length >= 2) break
      }
      thzAfterPlay = { who, n: who.length }
    }
  } catch (e) { thzAfterPlay = { err: String(e).slice(0, 80) } }
  console.log('THZ_AFTER_PLAY: ' + JSON.stringify(thzAfterPlay))
  if (logs.length) console.log('LOGS: ' + logs.slice(0, 6).join(' | '))
  await page.screenshot({ path: '../artifacts/_probe/gd2-final.png' })
  await browser.close()
})()
