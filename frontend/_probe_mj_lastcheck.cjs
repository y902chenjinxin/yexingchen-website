const { chromium } = require('playwright')
;(async () => {
  const browser = await chromium.launch({ args: ['--no-proxy-server'] })
  const page = await (await browser.newContext({ viewport: { width: 780, height: 390 } })).newPage()
  await page.goto('http://127.0.0.1:5199/_probe.html?g=mj&seat=0&dis=9', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(1500)
  const r = await page.evaluate(() => {
    const els = Array.from(document.querySelectorAll('.mj-dis .gt-tile.is-last'))
    return els.map((el) => {
      const pile = el.closest('[class*=mj-dis-]').className
      const cs = getComputedStyle(el)
      const r = el.getBoundingClientRect()
      return { pile, outline: cs.outline, outlineOffset: cs.outlineOffset, filter: cs.filter.slice(0, 60), x: Math.round(r.x), y: Math.round(r.y) }
    })
  })
  console.log(JSON.stringify(r, null, 1))
  await browser.close()
})()
