/**
 * v2.46.44 专用探针：麻将大量弃牌极限场景（仅开发用）。
 * 打 ~46 轮把四家弃牌喂满，量四方弃牌盒 + 截图，验证：
 *  ① 左右弃牌始终纵向码列（不再横摊）
 *  ② 上下弃牌行高封顶（不再撑桌）
 * 用法：cd frontend && node _probe_mj44.cjs
 */
const { chromium } = require('playwright')

;(async () => {
  const browser = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await browser.newContext({ viewport: { width: 720, height: 360 }, deviceScaleFactor: 2 })
  const page = await ctx.newPage()
  const logs = []
  page.on('pageerror', (e) => logs.push('pageerror: ' + e.message))
  await page.goto('http://[::1]:5199/_probe.html?g=mj', { waitUntil: 'domcontentloaded', timeout: 30000 })
  await page.waitForTimeout(2200)
  await page.evaluate(() => document.querySelectorAll('.gt-over').forEach((e) => e.remove()))

  const rounds = 60
  let captured = false
  for (let i = 0; i < rounds && !captured; i++) {
    let ready = false
    for (let w = 0; w < 25; w++) {
      // 有碰/杠/胡响应窗先点「过」（不然手牌永远不出 pickable，整局卡死）
      const passed = await page.evaluate(() => {
        const b = document.querySelector('.mj-actions .gt-btn.ghost')
        if (b && b.textContent.trim() === '过') { b.click(); return true }
        return false
      })
      if (passed) { await page.waitForTimeout(300); continue }
      if (await page.$('.mj-hand .gt-tile.pickable')) { ready = true; break }
      await page.waitForTimeout(400)
    }
    if (!ready) break
    try {
      const tiles = await page.$$('.mj-hand .gt-tile.pickable')
      await tiles[Math.floor(Math.random() * tiles.length)].click()
      await page.waitForTimeout(300)
      const play = await page.$('.mj-actions .gt-btn')
      if (play) await play.click()
    } catch { /* 忽略 */ }
    await page.waitForTimeout(500)
    // 若出现结算/胡牌浮层就关掉并开下一局继续喂
    await page.evaluate(() => {
      document.querySelectorAll('.mj-hushow').forEach((e) => e.click())
      // 「再来一局」是第一个非 ghost 按钮；绝不能点 ghost（返回列表会离开牌桌）
      document.querySelectorAll('.gt-over-card .gt-btn:not(.ghost)').forEach((e) => e.click())
    })
    await page.waitForTimeout(400)
    await page.evaluate(() => document.querySelectorAll('.gt-over').forEach((e) => e.remove()))
    // 弃牌攒够就当场抓拍（等整局结束再量只会量到新局的空桌）
    const total = await page.evaluate(() =>
      ['.mj-dis-up', '.mj-dis-down', '.mj-dis-left', '.mj-dis-right']
        .reduce((s, sel) => s + document.querySelectorAll(sel + ' > .gt-tile').length, 0))
    if (total >= 40) captured = true
  }
  await page.waitForTimeout(1200)

  const info = await page.evaluate(() => {
    const box = (sel) => {
      const el = document.querySelector(sel)
      if (!el) return null
      const r = el.getBoundingClientRect()
      return { w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x), y: Math.round(r.y) }
    }
    const n = (sel) => document.querySelectorAll(sel + ' > .gt-tile').length
    // 横摊检测：左右弃牌格若出现「列数 == 牌数」即摊平（每列一张）
    const strip = (sel) => {
      const el = document.querySelector(sel)
      if (!el) return null
      const kids = Array.from(el.querySelectorAll(':scope > .gt-tile'))
      const xs = new Set(kids.map((k) => Math.round(k.getBoundingClientRect().x)))
      return { tiles: kids.length, distinctCols: xs.size }
    }
    return {
      vars: (() => {
        const el = document.querySelector('.gt-shell.mj')
        if (!el) return null
        const c = getComputedStyle(el)
        return { gtH: c.getPropertyValue('--gt-h').trim(), disW: c.getPropertyValue('--dis-w').trim(), disH: c.getPropertyValue('--dis-h').trim(), miniW: c.getPropertyValue('--mini-w').trim() }
      })(),
      firstTiles: Object.fromEntries(['.mj-dis-up', '.mj-dis-down', '.mj-dis-left', '.mj-dis-right'].map((sel) => {
        const t = document.querySelector(sel + ' > .gt-tile')
        if (!t) return [sel, null]
        const r = t.getBoundingClientRect()
        return [sel, { w: Math.round(r.width), h: Math.round(r.height) }]
      })),
      table: box('.mj-table'),
      center: box('.mj-center'),
      disUp: { ...box('.mj-dis-up'), n: n('.mj-dis-up') },
      disDown: { ...box('.mj-dis-down'), n: n('.mj-dis-down') },
      disLeft: { ...box('.mj-dis-left'), n: n('.mj-dis-left'), strip: strip('.mj-dis-left') },
      disRight: { ...box('.mj-dis-right'), n: n('.mj-dis-right'), strip: strip('.mj-dis-right') },
      shell: box('.gt-shell.mj'),
    }
  })
  console.log(JSON.stringify(info, null, 1))
  if (logs.length) console.log('LOGS:', logs.slice(0, 5).join(' | '))
  await page.screenshot({ path: '../artifacts/_probe/mj44-full.png' })
  const c = await page.$('.mj-center')
  if (c) await c.screenshot({ path: '../artifacts/_probe/mj44-center.png' })
  await browser.close()
})()
