/**
 * 本地截图脚本（仅开发用）：跑起 vite dev 后，按手机竖屏（360×720，dpr2）截棋牌牌桌。
 * 用法：cd frontend && node _probe_shot.cjs
 */
const { chromium } = require('playwright')

const CASES = [
  { g: 'mp', name: 'monopoly' },
  { g: 'mj', name: 'mahjong' },
  { g: 'gd', name: 'guandan' },
]

;(async () => {
  const browser = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await browser.newContext({
    viewport: { width: 360, height: 720 },
    deviceScaleFactor: 2,
  })
  for (const c of CASES) {
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
    // 麻将开局会先弹「定缺」，先点掉才能看到牌桌
    if (c.g === 'mj') {
      // 定缺不能选手上没有的花色：每次都挑持有最多的一门；打完/结算的页内浮层直接摘掉
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
      await page.waitForTimeout(1500)
      // 自己打几张，把四家的弃牌都喂出来
      for (let i = 0; i < 4; i++) {
        try {
          const tiles = await page.$$('.mj-hand .gt-tile')
          if (tiles.length) await tiles[tiles.length - 1].click()
          await page.waitForTimeout(250)
          const play = await page.$('.mj-actions .gt-btn')
          if (play) await play.click()
        } catch { /* 忽略 */ }
        await page.waitForTimeout(1400)
      }
      await page.evaluate(() => document.querySelectorAll('.gt-over').forEach((e) => e.remove()))
      await page.waitForTimeout(400)
    }
    const info = await page.evaluate(() => {
      const q = (s) => document.querySelector(s)
      const box = (s) => {
        const el = q(s)
        if (!el) return null
        const r = el.getBoundingClientRect()
        return { w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x), y: Math.round(r.y) }
      }
      const cs = (s, p) => { const el = q(s); return el ? getComputedStyle(el).getPropertyValue(p) : null }
      return {
        stage: box('.gtv-viewstage'),
        canvas: box('.gtv-viewzoom'),
        shell: box('.gt-shell'),
        mpBoard: box('.mp-board'),
        mpWrap: box('.mp-boardwrap'),
        mpSide: box('.mp-side'),
        mpCols: cs('.mp', 'grid-template-columns'),
        mpSizeVar: cs('.mp-boardwrap', '--mp-size'),
        wrapClient: (() => { const el = q('.mp-boardwrap'); return el ? { w: el.clientWidth, h: el.clientHeight } : null })(),
        mpCell: box('.mp-cell'),
        boardRows: cs('.mp-board', 'grid-template-rows'),
        boardCols: cs('.mp-board', 'grid-template-columns'),
        boardN: cs('.mp-board', '--n'),
        boardSize: (() => { const el = q('.mp-board'); return el ? { w: el.offsetWidth, h: el.offsetHeight, sh: el.scrollHeight, sw: el.scrollWidth } : null })(),
        firstCells: Array.from(document.querySelectorAll('.mp-cell')).slice(0, 3).map((el) => ({
          t: el.textContent.trim().slice(0, 6),
          gr: getComputedStyle(el).gridRow, gc: getComputedStyle(el).gridColumn,
          w: el.offsetWidth, h: el.offsetHeight,
        })),
        mjTable: box('.mj-table'),
        mjCenter: box('.mj-center'),
        mjHand: box('.mj-hand'),
        mjTile: box('.mj .gt-tile.mini'),
        miniW: cs('.mj', '--mini-w'),
        tilePos: cs('.mj .gt-tile', 'position'),
        tileOverflow: cs('.mj .gt-tile', 'overflow'),
        tileBox: box('.mj-hand .gt-tile'),
        svgBox: (() => {
          const svg = document.querySelector('.mj-hand .gt-tile svg')
          if (!svg) return null
          const r = svg.getBoundingClientRect()
          const cs2 = getComputedStyle(svg)
          return { w: Math.round(r.width), h: Math.round(r.height), pos: cs2.position, inset: cs2.inset, cnt: document.querySelectorAll('.mj svg').length }
        })(),
        gdHand: box('.gd-hand'),
        gdCard: box('.gd .gt-card'),
      }
    })
    console.log('===== ' + c.name + ' =====')
    console.log(JSON.stringify(info))
    if (logs.length) console.log('LOGS: ' + logs.slice(0, 6).join(' | '))
    await page.screenshot({ path: `../artifacts/_probe/${c.name}.png` })
    // 大富翁：中央区 + 右栏各来一张特写，方便看骰子与信息层级
    if (c.g === 'mp') {
      for (const [sel, tag] of [['.mp-center', 'mp-center'], ['.mp-side', 'mp-side'], ['.mp-board', 'mp-board']]) {
        const el = await page.$(sel)
        if (el) await el.screenshot({ path: `../artifacts/_probe/${tag}.png` })
      }
    }
    await page.close()
  }
  await browser.close()
})()
