/**
 * 翻页时钟全屏横屏探针（v2.46.118）：
 *   ① 852×393 横屏 + ?m=1 → .fc-stage 出现（z-index 1600）、全屏钟 is-full 卡几何不溢出、
 *      字号随 vh/vw 公式放大（卡高 ~min(46vh,21vw)）、冒号呼吸动画存在；
 *   ② 转竖屏 390×844 → 舞台消失、lg 工具页钟仍在；
 *   ③ 横屏点 × → 舞台消失（manualExit）；再转竖屏+横屏 → 舞台重现（manualExit 已重置）。
 * 用法：dev server 5198 起来后 cd frontend && node _probe_fs.cjs
 */
const { chromium } = require('playwright')

;(async () => {
  const browser = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 })
  const page = await ctx.newPage()
  await page.goto('http://localhost:5198/_probe_fs.html?m=1', {
    waitUntil: 'domcontentloaded', timeout: 30000,
  })
  await page.waitForTimeout(1200)

  const snap = () => page.evaluate(() => {
    const stage = document.querySelector('.fc-stage')
    const card = document.querySelector('.mfc.is-full .mfc-card')
    const r = card ? card.getBoundingClientRect() : null
    const clock = document.querySelector('.mfc.is-full')
    const cr = clock ? clock.getBoundingClientRect() : null
    const colonDot = document.querySelector('.mfc.is-full .mfc-colon i')
    return {
      stageOn: !!stage,
      stageZ: stage ? getComputedStyle(stage).zIndex : null,
      cardW: r ? Math.round(r.width) : null,
      cardH: r ? Math.round(r.height) : null,
      fs: r ? Math.round(parseFloat(getComputedStyle(card.querySelector('span')).fontSize)) : null,
      clockL: cr ? Math.round(cr.left) : null,
      clockR: cr ? Math.round(cr.right) : null,
      clockT: cr ? Math.round(cr.top) : null,
      clockB: cr ? Math.round(cr.bottom) : null,
      blink: colonDot ? getComputedStyle(colonDot).animationName : null,      lgStill: !!document.querySelector('.mfc.is-lg'),
      vw: innerWidth, vh: innerHeight,
    }
  })

  const out = {}

  // ① 横屏 852×393
  await page.setViewportSize({ width: 852, height: 393 })
  await page.waitForTimeout(700)
  out.landscape = await snap()

  // ② 转竖屏
  await page.setViewportSize({ width: 390, height: 844 })
  await page.waitForTimeout(700)
  out.portrait = await snap()

  // ③ 横屏 → 点 × → 竖屏 → 再横屏
  await page.setViewportSize({ width: 852, height: 393 })
  await page.waitForTimeout(600)
  const exitBtn = await page.$('.fc-exit')
  out.exitBtnVisible = !!exitBtn
  if (exitBtn) await exitBtn.click()
  await page.waitForTimeout(500)
  out.afterExit = (await snap()).stageOn
  await page.setViewportSize({ width: 390, height: 844 })
  await page.waitForTimeout(500)
  await page.setViewportSize({ width: 852, height: 393 })
  await page.waitForTimeout(600)
  out.reEnter = (await snap()).stageOn

  // 断言
  const L = out.landscape
  const checks = [
    ['横屏出舞台', L.stageOn === true],
    ['舞台 z-index 1600', L.stageZ === '1600'],
    ['钟横向居中不溢出', L.clockL >= 0 && L.clockR <= 852],
    ['钟纵向不溢出', L.clockT >= 0 && L.clockB <= 393],
    ['卡高≈min(46vh,21vw)', Math.abs(L.cardH - Math.min(0.46 * 393, 0.21 * 852)) < 3],
    ['大字号(fs≥55px)', L.fs >= 55],
    ['冒号呼吸动画生效', (L.blink || '').startsWith('mfc-blink')],
    ['竖屏收舞台', out.portrait.stageOn === false],
    ['竖屏保留 lg 工具页钟', out.portrait.lgStill === true],
    ['× 可见可点', out.exitBtnVisible === true],
    ['点 × 后收舞台', out.afterExit === false],
    ['竖→横重现（manualExit 重置）', out.reEnter === true],
  ]
  console.log('landscape:', JSON.stringify(out.landscape))
  console.log('portrait :', JSON.stringify(out.portrait))
  let pass = 0, fail = 0
  for (const [name, ok] of checks) {
    console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}`)
    ok ? pass++ : fail++
  }
  console.log(`\n${pass} PASS / ${fail} FAIL`)
  await browser.close()
  process.exit(fail ? 1 : 0)
})().catch((e) => { console.error(e); process.exit(1) })
