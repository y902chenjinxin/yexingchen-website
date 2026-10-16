/**
 * 麻将弃牌区探针（v2.46.97）：?dis=N 注入每家 N 张弃牌，横屏 780×390 截图 +
 * 量化每家弃牌的行/列结构（腾讯式 6 张一行/列的整齐度核验）。用法：
 *   cd frontend && node _probe_mj_discard.cjs 12
 */
const { chromium } = require('playwright')

;(async () => {
  const disN = Number(process.argv[2] || 9)
  const W = 780, H = 390
  const browser = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 })
  const page = await ctx.newPage()
  const logs = []
  page.on('pageerror', (e) => logs.push('pageerror: ' + e.message))

  await page.goto(`http://127.0.0.1:5199/_probe.html?g=mj&seat=0&dis=${disN}`, { waitUntil: 'domcontentloaded', timeout: 30000 })
  await page.waitForTimeout(1800)

  const info = await page.evaluate(() => {
    const box = (el) => { const r = el.getBoundingClientRect(); return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) } }
    const qa = (s) => Array.from(document.querySelectorAll(s))
    const center = document.querySelector('.mj-center')
    const piles = qa('.mj-dis').map((p) => {
      const cls = [...p.classList].find((c) => c.startsWith('mj-dis-'))
      const tiles = qa('.gt-tile', p).length ? Array.from(p.querySelectorAll(':scope > .gt-tile')) : Array.from(p.children)
      const boxes = tiles.map((t) => box(t))
      // 按 y 聚行（上/下家）、按 x 聚列（左右家），看每行/列张数
      const groups = []
      const keyOf = (b) => Math.round((cls === 'mj-dis-left' || cls === 'mj-dis-right' ? b.x : b.y) / 12)
      for (const b of boxes) {
        const k = keyOf(b)
        let g = groups.find((x) => x.k === k)
        if (!g) { g = { k, n: 0 }; groups.push(g) }
        g.n++
      }
      groups.sort((a, b) => a.k - b.k)
      return { cls, pile: box(p), tiles: tiles.length, rowsOrCols: groups.map((g) => g.n) }
    })
    return { vw: innerWidth, vh: innerHeight, center: center ? box(center) : null, piles }
  })
  console.log(JSON.stringify(info, null, 1))
  await page.screenshot({ path: '../artifacts/_probe/mj-discard.png' })
  if (logs.length) console.log('LOGS: ' + logs.slice(0, 6).join(' | '))
  await browser.close()
})()
