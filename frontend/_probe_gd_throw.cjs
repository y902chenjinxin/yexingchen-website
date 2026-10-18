/**
 * 掼蛋出牌区几何探针（v2.46.114）：量「我方出牌（gd-thz-0）」与手牌/工具条的
 * 几何关系，复现「出牌较多压牌」。852×393 复刻夜星手机横屏。
 * 用法：cd frontend && node _probe_gd_throw.cjs [张数]
 */
const { chromium } = require('playwright')

const N = Number(process.argv[2] || 6)

;(async () => {
  const browser = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await browser.newContext({ viewport: { width: 852, height: 393 }, deviceScaleFactor: 2 })
  const page = await ctx.newPage()
  await page.goto(`http://127.0.0.1:5199/_probe.html?g=gd&seat=0&thrown=${N}&tseat=0`, {
    waitUntil: 'domcontentloaded', timeout: 30000,
  })
  await page.waitForTimeout(2500)

  const info = await page.evaluate(() => {
    const box = (sel) => {
      const el = document.querySelector(sel)
      if (!el) return null
      const r = el.getBoundingClientRect()
      return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), bottom: Math.round(r.bottom), right: Math.round(r.right) }
    }
    const thz = document.querySelector('.gd-thz-0')
    const who = document.querySelector('.gd-thz-0 .gd-thz-who')
    const cards = document.querySelector('.gd-thz-0 .gd-thz-cards')
    const firstCard = document.querySelector('.gd-thz-0 .gt-card')
    const center = document.querySelector('.gd-center')
    const low = center ? center.classList.contains('is-low') : null
    const mq = window.matchMedia('(orientation: landscape) and (max-height: 480px)').matches
    return {
      vw: innerWidth, vh: innerHeight, mqLandscape: mq, lowTable: low,
      center: box('.gd-center'),
      thz0: box('.gd-thz-0'),
      whoPill: box('.gd-thz-0 .gd-thz-who'),
      cardsRow: box('.gd-thz-0 .gd-thz-cards'),
      firstCard: firstCard ? { w: Math.round(firstCard.getBoundingClientRect().width), h: Math.round(firstCard.getBoundingClientRect().height) } : null,
      bar: box('.gd-bottom-bar'),
      tools: box('.gd-hand-tools'),
      toolsMarginTop: document.querySelector('.gd-hand-tools') ? getComputedStyle(document.querySelector('.gd-hand-tools')).marginTop : null,
      hand: box('.gd-hand'),
      handZone: box('.gd-hand-zone'),
      bottom: box('.gd-bottom'),
    }
  })
  console.log(JSON.stringify(info, null, 1))

  // 重叠判定
  const ov = (a, b) => (a && b && a.x < b.right && b.x < a.right && a.y < b.bottom && b.y < a.bottom)
  const t = info.thz0, h = info.hand, tools = info.tools
  console.log('--- overlap checks ---')
  console.log('throw vs hand   :', ov(t, h) ? 'OVERLAP ❌' : 'ok')
  console.log('throw vs tools  :', ov(t, tools) ? 'OVERLAP ❌' : 'ok')
  if (t && h) console.log('gap throw→hand  :', h.y - t.bottom, 'px')
  if (t && tools) console.log('gap tools→throw :', t.y - tools.bottom, 'px')

  await page.screenshot({ path: `../artifacts/_probe/gd-throw-${N}.png` })
  await browser.close()
})()
