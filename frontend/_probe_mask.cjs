const { chromium } = require('playwright')
const BASE = 'http://localhost:5301/_probe_reader.html'
;(async () => {
  const b = await chromium.launch()
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 })
  const p = await ctx.newPage()
  p.on('pageerror', (e) => console.log('[pageerror]', e.message.slice(0, 160)))
  await p.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForSelector('.nrd', { timeout: 20000 })
  await p.waitForTimeout(900)
  // 点中部唤出顶栏/底栏
  await p.mouse.click(195, 420)
  await p.waitForTimeout(500)
  const btns = await p.evaluate(() => Array.from(document.querySelectorAll('.nrd-foot-tools button')).map((x) => x.textContent.trim()))
  console.log('foot tools:', btns.join(' | '))
  // 打开目录
  await p.evaluate(() => {
    const b = Array.from(document.querySelectorAll('.nrd-foot-tools button')).find((x) => x.textContent.trim() === '目录')
    b && b.click()
  })
  await p.waitForTimeout(700)
  const geo = await p.evaluate(() => {
    const s = document.querySelector('.nrd-scrim-panel')
    const sh = document.querySelector('.nrd-sheet')
    const cs = s && getComputedStyle(s)
    return {
      scrim: cs ? `${cs.backgroundColor} z${cs.zIndex} ${s.getBoundingClientRect().height.toFixed(0)}px` : 'none',
      sheet: sh ? `${sh.getBoundingClientRect().height.toFixed(0)}px` : 'none',
    }
  })
  console.log('panel:', JSON.stringify(geo))
  await p.screenshot({ path: 'artifacts/_probe/mask_toc.png' })
  console.log('shot -> artifacts/_probe/mask_toc.png')
  await b.close()
})()
