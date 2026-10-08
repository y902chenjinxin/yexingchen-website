/**
 * 牌面检视截图：node _probe_tiles.cjs（需要 vite dev 在 5199 跑着）
 * 输出 ../artifacts/_probe/tiles-big.png 与 tiles-mini.png
 */
const { chromium } = require('playwright')

const SHOTS = [
  { name: "tiles-big", url: "/_probe.html?g=tiles&size=big", w: 600, h: 400 },
  { name: 'tiles-mini', url: '/_probe.html?g=tiles&size=mini', w: 640, h: 340 },
]

;(async () => {
  const browser = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await browser.newContext({ viewport: { width: 640, height: 340 }, deviceScaleFactor: 2 })
  for (const s of SHOTS) {
    const page = await ctx.newPage()
    await page.setViewportSize({ width: s.w, height: s.h })
    await page.goto(`http://[::1]:5199${s.url}`, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForTimeout(1400)
    await page.screenshot({ path: `../artifacts/_probe/${s.name}.png`, fullPage: true })
    console.log('shot: ' + s.name)
    await page.close()
  }
  await browser.close()
})()
