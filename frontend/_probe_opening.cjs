/** 开局仪式截图（仅开发用）：抓码牌/掷骰/流牌三个阶段 */
const { chromium } = require('playwright')
;(async () => {
  const browser = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await browser.newContext({ viewport: { width: 720, height: 360 }, deviceScaleFactor: 2 })
  const page = await ctx.newPage()
  const errs = []
  page.on('pageerror', (e) => errs.push(e.message))
  await page.goto('http://[::1]:5199/_probe.html?g=mj', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(2600)
  await page.screenshot({ path: '../artifacts/_probe/wide-mahjong-opening.png' })
  await page.waitForTimeout(2500)
  await page.screenshot({ path: '../artifacts/_probe/wide-mahjong-opening2.png' })
  await page.waitForTimeout(3200)
  await page.screenshot({ path: '../artifacts/_probe/wide-mahjong-opening3.png' })
  console.log('ERRS:', JSON.stringify(errs))
  await browser.close()
})()
