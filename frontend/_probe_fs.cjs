/**
 * 翻页时钟全屏探针（v2.46.119：点击入口自动横屏展示，竖屏 rotate90 兜底）：
 *   ① 390×844 竖屏 + ?m=1 → 挂载即舞台出现（不用手动横屏）、is-rot 平面 rotate(90deg)、
 *      时钟卡视觉水平长度 ≈ min(46vw,21vh)≈177、整体 AABB 在视口内；
 *   ② 物理横屏 852×393 → is-rot 移除、正常横排（卡高≈min(46vh,21vw)≈179）；
 *   ③ 点 × → 舞台收、lg 工具页钟 + 「全屏时钟」重进按钮出现；
 *   ④ 点「全屏时钟」→ 舞台重现。
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
    const plane = document.querySelector('.fc-plane')
    const card = document.querySelector('.mfc.is-full .mfc-card')
    const clock = document.querySelector('.mfc.is-full')
    const r = card ? card.getBoundingClientRect() : null
    const cr = clock ? clock.getBoundingClientRect() : null
    return {
      stageOn: !!stage,
      isRot: !!(stage && stage.classList.contains('is-rot')),
      planeTransform: plane ? getComputedStyle(plane).transform : null,
      cardVisW: r ? Math.round(r.width) : null,   // 竖屏旋转后=平面内卡高；横屏=卡宽
      cardVisH: r ? Math.round(r.height) : null,  // 横屏不旋转时=平面内卡高
      clockIn: cr ? (cr.left >= 0 && cr.right <= innerWidth && cr.top >= 0 && cr.bottom <= innerHeight) : null,
      fsBtn: !!document.querySelector('.fc-enter'),
      lgStill: !!document.querySelector('.mfc.is-lg'),
      vw: innerWidth, vh: innerHeight,
    }
  })

  const out = {}

  // ① 竖屏挂载即全屏 + 旋转平面
  out.portrait = await snap()

  // ② 物理横屏
  await page.setViewportSize({ width: 852, height: 393 })
  await page.waitForTimeout(700)
  out.landscape = await snap()

  // ③ 点 × → 回工具页
  const exitBtn = await page.$('.fc-exit')
  out.exitBtnVisible = !!exitBtn
  if (exitBtn) await exitBtn.click()
  await page.waitForTimeout(500)
  out.afterExit = await snap()

  // ④ 点「全屏时钟」重进（竖屏）
  await page.setViewportSize({ width: 390, height: 844 })
  await page.waitForTimeout(500)
  const enterBtn = await page.$('.fc-enter')
  out.enterBtnVisible = !!enterBtn
  if (enterBtn) await enterBtn.click()
  await page.waitForTimeout(600)
  out.reEnter = (await snap()).stageOn

  const P = out.portrait, L = out.landscape
  const expRotH = Math.round(Math.min(0.46 * 390, 0.21 * 844))   // 177
  const expLsH = Math.round(Math.min(0.46 * 393, 0.21 * 852))    // 179
  const checks = [
    ['竖屏挂载即全屏（不手动转屏）', P.stageOn === true],
    ['竖屏 is-rot 平面旋转 90°', P.isRot === true && (P.planeTransform || '').includes('matrix')],
    [`竖屏卡视觉水平长≈${expRotH}`, Math.abs(P.cardVisW - expRotH) <= 2],
    ['竖屏时钟整体在视口内', P.clockIn === true],
    ['横屏去旋转正常横排', L.stageOn === true && L.isRot === false],
    [`横屏卡高≈${expLsH}`, Math.abs(L.cardVisH - expLsH) <= 2],
    ['横屏时钟整体在视口内', L.clockIn === true],
    ['× 可见可点', out.exitBtnVisible === true],
    ['× 后回工具页（lg+重进按钮）', out.afterExit.stageOn === false && out.afterExit.lgStill === true && out.afterExit.fsBtn === true],
    ['「全屏时钟」按钮可重进', out.enterBtnVisible === true && out.reEnter === true],
  ]
  console.log('portrait :', JSON.stringify(out.portrait))
  console.log('landscape:', JSON.stringify(out.landscape))
  console.log('afterExit:', JSON.stringify(out.afterExit))
  let pass = 0, fail = 0
  for (const [name, ok] of checks) {
    console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}`)
    ok ? pass++ : fail++
  }
  console.log(`\n${pass} PASS / ${fail} FAIL`)
  await browser.close()
  process.exit(fail ? 1 : 0)
})().catch((e) => { console.error(e); process.exit(1) })
