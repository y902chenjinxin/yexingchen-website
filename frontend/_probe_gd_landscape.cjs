/**
 * v2.46.91 掼蛋横屏全屏探针（仅开发用）：复刻夜星手机横屏 852×393，
 * 量 viewzoom 画布 vs gt-shell 实高 vs 舞台，定位「底部一大块黑」。
 * 用法：cd frontend && node _probe_gd_landscape.cjs
 */
const { chromium } = require('playwright')

;(async () => {
  const browser = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await browser.newContext({ viewport: { width: 852, height: 393 }, deviceScaleFactor: 2 })
  const page = await ctx.newPage()
  await page.goto('http://127.0.0.1:5199/_probe.html?g=gd', { waitUntil: 'domcontentloaded', timeout: 30000 })
  await page.waitForTimeout(2000)

  const info = await page.evaluate(() => {
    const stage = document.querySelector('.gtv-viewstage.is-fs')
    const zoom = document.querySelector('.gtv-viewzoom.is-fs')
    const shell = document.querySelector('.gt-shell')
    const landscape = document.querySelector('.gt-landscape')
    const hand = document.querySelector('.gd-hand-zone') || document.querySelector('.gd-hand')
    const table = document.querySelector('.gd-table')
    const cs = (el) => (el ? getComputedStyle(el) : null)
    const box = (el) => {
      if (!el) return null
      const r = el.getBoundingClientRect()
      return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) }
    }
    return {
      vw: innerWidth, vh: innerHeight,
      stage: box(stage), stageCS: stage ? { h: cs(stage).height } : null,
      zoomStyle: zoom ? { w: zoom.style.width, h: zoom.style.height, tf: zoom.style.transform } : null,
      zoomBox: box(zoom),
      landscape: box(landscape), landscapeCS: landscape ? { h: cs(landscape).height } : null,
      shell: box(shell), shellOffset: shell ? { w: shell.offsetWidth, h: shell.offsetHeight } : null,
      table: box(table),
      hand: box(hand),
    }
  })
  console.log(JSON.stringify(info, null, 1))
  await page.screenshot({ path: '../artifacts/_probe/gd-landscape.png' })
  await browser.close()
})()
