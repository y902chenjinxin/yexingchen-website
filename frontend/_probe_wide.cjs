/**
 * 本地截图脚本 · 横向视口版（仅开发用）
 *
 * 竖屏版（_probe_shot.cjs）看到的是 rotate(90deg) 之后的画面，读坐标要脑内转 90°；
 * 这里换成 720×360 横向视口 —— orientation 变成 landscape，媒体查询不生效，
 * 于是 #probe-rot 不旋转，屏幕坐标 == CSS 坐标，定位布局问题一眼可见。
 *
 * 用法：cd frontend && node _probe_wide.cjs [g]
 */
const { chromium } = require('playwright')

const CASES = [
  { g: 'mp', name: 'wide-monopoly' },
  { g: 'mj', name: 'wide-mahjong' },
  { g: 'gd', name: 'wide-guandan' },
]
const only = process.argv[2]
const list = only ? CASES.filter((c) => c.g === only) : CASES

;(async () => {
  const browser = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await browser.newContext({
    viewport: { width: 720, height: 360 },
    deviceScaleFactor: 2,
  })
  for (const c of list) {
    const page = await ctx.newPage()
    const logs = []
    page.on('console', (m) => { if (m.type() === 'error') logs.push('err: ' + m.text()) })
    page.on('pageerror', (e) => logs.push('pageerror: ' + e.message))
    try {
      await page.goto(`http://[::1]:5199/_probe.html?g=${c.g}`, { waitUntil: 'domcontentloaded', timeout: 30000 })
    } catch (e) {
      console.log('===== ' + c.name + ' 打开失败 =====\n' + e.message)
      await page.close()
      continue
    }
    await page.waitForTimeout(2200)
    if (c.g === 'mj') {
      for (let i = 0; i < 6; i++) {
        const btns = await page.$$('.gt-over-card .gt-btn')
        if (!btns.length) break
        let best = 0
        let bestN = -1
        for (let k = 0; k < btns.length; k++) {
          const t = await btns[k].innerText()
          const m = t.match(/(\d+)\s*张/)
          const n = m ? Number(m[1]) : 0
          if (n > bestN) { bestN = n; best = k }
        }
        await btns[best].click()
        await page.waitForTimeout(500)
      }
      await page.evaluate(() => document.querySelectorAll('.gt-over').forEach((e) => e.remove()))
      await page.waitForTimeout(1200)
    }

    const info = await page.evaluate(() => {
      const q = (s) => document.querySelector(s)
      const box = (s) => {
        const el = q(s)
        if (!el) return null
        const r = el.getBoundingClientRect()
        return { w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x), y: Math.round(r.y) }
      }
      const kids = (s) => {
        const el = q(s)
        if (!el) return null
        return Array.from(el.children).map((k) => {
          const r = k.getBoundingClientRect()
          return {
            cls: (k.className && k.className.baseVal !== undefined ? k.className.baseVal : k.className) || k.tagName,
            w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x), y: Math.round(r.y),
            txt: (k.textContent || '').trim().slice(0, 14),
          }
        })
      }
      return {
        rotTransform: getComputedStyle(q('#probe-rot')).transform,
        mpBoard: box('.mp-board'),
        mpWrap: box('.mp-boardwrap'),
        mpCenter: box('.mp-center'),
        mpCenterKids: kids('.mp-center'),
        mpDice: box('.mp-dice'),
        diceItems: kids('.mp-dice'),
        dicePips: (() => {
          const svg = q('.mp-dice svg')
          if (!svg) return null
          const cs = getComputedStyle(svg)
          const r = svg.getBoundingClientRect()
          const parents = []
          let el = svg
          while (el && parents.length < 6) {
            parents.push((el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className) || el.tagName)
            el = el.parentElement
          }
          return {
            nCircle: svg.querySelectorAll('circle').length,
            w: Math.round(r.width), h: Math.round(r.height),
            viewBox: svg.getAttribute('viewBox'),
            chain: parents.join(' < '),
          }
        })(),
        mdySize: (() => { const el = q('.mp-dice'); return el ? getComputedStyle(el).getPropertyValue('--mdy-size') : null })(),
        mdyVarOnMdy: (() => { const el = q('.mdy'); return el ? getComputedStyle(el).getPropertyValue('--mdy-size') : null })(),
        mdyBox: (() => { const el = q('.mdy'); if (!el) return null; const r = el.getBoundingClientRect(); return { w: Math.round(r.width), h: Math.round(r.height), bg: getComputedStyle(el.querySelector('.mdy-body')).backgroundImage.slice(0, 40) } })(),
        mpSide: box('.mp-side'),
        mpSideKids: kids('.mp-side'),
        mpCols: (() => { const el = q('.mp'); return el ? getComputedStyle(el).gridTemplateColumns : null })(),
        mpScroll: (() => { const el = q('.mp-center'); return el ? { sh: el.scrollHeight, ch: el.clientHeight, sw: el.scrollWidth, cw: el.clientWidth } : null })(),
        mjTable: box('.mj-table'),
        mjCenter: box('.mj-center'),
        mjTableKids: kids('.mj-table'),
      }
    })
    console.log('===== ' + c.name + ' =====')
    console.log(JSON.stringify(info, null, 1))
    if (logs.length) console.log('LOGS: ' + logs.slice(0, 6).join(' | '))
    await page.screenshot({ path: `../artifacts/_probe/${c.name}.png` })
    for (const [sel, tag] of [['.mp-center', 'w-mp-center'], ['.mp-side', 'w-mp-side'], ['.mp-dice', 'w-mp-dice'], ['.mj-center', 'w-mj-center']]) {
      const el = await page.$(sel)
      if (el) await el.screenshot({ path: `../artifacts/_probe/${tag}.png` })
    }
    await page.close()
  }
  await browser.close()
})()
