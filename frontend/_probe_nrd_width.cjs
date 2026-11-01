/** 阅读器桌面端列宽验收（v2.46.318）：1440 / 1024 / 390 三档量正文宽度与分页 */
const { chromium } = require('playwright')
const BASE = process.env.PROBE_BASE || 'http://localhost:5311'

;(async () => {
  const b = await chromium.launch()
  for (const vp of [
    { name: 'pc1440', width: 1440, height: 900 },
    { name: 'pc1024', width: 1024, height: 800 },
    { name: 'phone390', width: 390, height: 844, isMobile: true },
  ]) {
    const ctx = await b.newContext({
      viewport: { width: vp.width, height: vp.height },
      deviceScaleFactor: 2,
      isMobile: !!vp.isMobile,
      hasTouch: !!vp.isMobile,
    })
    const p = await ctx.newPage()
    p.on('pageerror', (e) => console.log('[pageerror]', e.message.slice(0, 120)))
    await p.goto(`${BASE}/_probe_reader.html`, { waitUntil: 'domcontentloaded', timeout: 60000 })
    await p.waitForSelector('.nrd', { timeout: 20000 }).catch(() => {})
    await p.waitForTimeout(2200)

    const m = await p.evaluate(() => {
      const cols = document.querySelector('.nrd-txt-cols')
      const para = document.querySelector('.nrd-p')
      const txt = document.querySelector('.nrd-txt')
      if (!cols) return { none: true }
      const cs = getComputedStyle(cols)
      const r = cols.getBoundingClientRect()
      const pr = para ? para.getBoundingClientRect() : null
      const cw = cols.clientWidth
      const padL = parseFloat(cs.paddingLeft)
      const padR = parseFloat(cs.paddingRight)
      return {
        viewport: innerWidth,
        colsWidth: Math.round(r.width),
        padL: Math.round(padL),
        padR: Math.round(padR),
        textWidth: Math.round(cw - padL - padR),
        paraWidth: pr ? Math.round(pr.width) : null,
        fontSize: cs.fontSize,
        lineHeight: cs.lineHeight,
        paged: document.querySelector('.nrd-txt')?.classList.contains('is-paged'),
        scrollW: Math.round(cols.scrollWidth),
        txtClientW: txt ? Math.round(txt.clientWidth) : null,
      }
    })
    // 翻页一页：看是否错位（第一页应显示完整一行文字，不横向溢出）
    const pageAfter = await p.evaluate(async () => {
      const next = document.querySelector('.nrd-foot-next, [aria-label="下一页"], .nrd-next')
      if (!next) return 'no-next-btn'
      next.click()
      await new Promise((r) => setTimeout(r, 500))
      const cols = document.querySelector('.nrd-txt-cols')
      return { transform: getComputedStyle(cols).transform }
    })
    console.log(`\n[${vp.name}]`, JSON.stringify(m))
    console.log(`        翻页后:`, JSON.stringify(pageAfter))
    await p.screenshot({ path: `artifacts/_probe/nrd_${vp.name}.png` })
    await ctx.close()
  }
  await b.close()
})()
