const { chromium } = require('playwright')
;(async () => {
  const b = await chromium.launch()
  const p = await b.newPage({ viewport: { width: 390, height: 844 } })
  p.on('pageerror', (e) => console.log('[pageerror]', e.message))
  await p.goto('http://localhost:5199/_probe_reader.html', { waitUntil: 'networkidle' })
  await p.waitForTimeout(800)

  // 打开设置抽屉（复现夜星操作）
  await p.mouse.click(195, 420)
  await p.waitForTimeout(250)
  await p.evaluate(() => {
    Array.from(document.querySelectorAll('.nrd-foot-tools button')).find((b) => b.textContent.includes('设置'))?.click()
  })
  await p.waitForTimeout(500)

  const info = await p.evaluate(() => {
    const sheet = document.querySelector('.nrd-sheet-set')
    const foot = document.querySelector('.nrd-foot')
    const nrd = document.querySelector('.nrd')
    const done = Array.from(document.querySelectorAll('.nrd-sheet-set .nrd-btn')).find((x) => x.textContent.includes('完成'))
    const g = (el) => {
      if (!el) return null
      const r = el.getBoundingClientRect()
      const cs = getComputedStyle(el)
      return { top: Math.round(r.top), bottom: Math.round(r.bottom), h: Math.round(r.height), z: cs.zIndex, pos: cs.position, display: cs.display, opacity: cs.opacity, overflow: cs.overflow }
    }
    let atDone = null
    if (done) {
      const dr = done.getBoundingClientRect()
      const cx = Math.round(dr.left + dr.width / 2)
      const cy = Math.round(dr.top + dr.height / 2)
      atDone = {
        point: [cx, cy],
        stack: document.elementsFromPoint(cx, cy).slice(0, 5).map((e) => `${e.tagName.toLowerCase()}.${(e.className || '').toString().split(' ').filter(Boolean).slice(0, 3).join('.')}`),
      }
    }
    return {
      innerH: window.innerHeight,
      visualH: window.visualViewport?.height,
      nrd: g(nrd),
      sheet: g(sheet),
      foot: g(foot),
      done: g(done),
      atDone,
    }
  })
  console.log(JSON.stringify(info, null, 2))
  await p.screenshot({ path: '../artifacts/_probe/dbg-set-sheet.png' })
  await b.close()
})()
