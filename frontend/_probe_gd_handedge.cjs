const { chromium } = require('playwright')
;(async () => {
  const browser = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await browser.newContext({ viewport: { width: 393, height: 852 }, deviceScaleFactor: 2 })
  const page = await ctx.newPage()
  await page.goto('http://127.0.0.1:5199/_probe.html?g=gd', { waitUntil: 'domcontentloaded', timeout: 30000 })
  await page.waitForTimeout(1200)
  const info = await page.evaluate(() => {
    const box = (el) => { const r = el.getBoundingClientRect(); return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) } }
    const q = (s) => document.querySelector(s)
    const hand = q('.gd-hand'), zone = q('.gd-hand-zone')
    // 手牌每张卡的右缘最大值（扇形弧顶）
    const cards = Array.from(document.querySelectorAll('.gd-hand .gt-card')).map((c) => box(c))
    const maxRight = cards.length ? Math.max(...cards.map((c) => c.x + c.w)) : null
    return { zone: zone ? box(zone) : null, hand: hand ? box(hand) : null, cardCount: cards.length, maxCardRight: maxRight }
  })
  console.log(JSON.stringify(info))
  await browser.close()
})()
