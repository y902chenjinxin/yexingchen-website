/** 桌面 1280×720 探针（v2.46.44 弃牌布局验证） */
const { chromium } = require('playwright')
;(async () => {
  const b = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await b.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1.5 })
  const p = await ctx.newPage()
  await p.goto('http://[::1]:5199/_probe.html?g=mj', { waitUntil: 'domcontentloaded' })
  await p.waitForTimeout(2500)
  await p.evaluate(() => document.querySelectorAll('.gt-over').forEach((e) => e.remove()))
  for (let i = 0; i < 14; i++) {
    for (let w = 0; w < 20; w++) {
      const passed = await p.evaluate(() => {
        const btn = document.querySelector('.mj-actions .gt-btn.ghost')
        if (btn && btn.textContent.trim() === '过') { btn.click(); return true }
        return false
      })
      if (passed) { await p.waitForTimeout(300); continue }
      if (await p.$('.mj-hand .gt-tile.pickable')) break
      await p.waitForTimeout(400)
    }
    try {
      const tiles = await p.$$('.mj-hand .gt-tile.pickable')
      if (!tiles.length) break
      await tiles[Math.floor(Math.random() * tiles.length)].click()
      await p.waitForTimeout(250)
      const play = await p.$('.mj-actions .gt-btn')
      if (play) await play.click()
    } catch { /* 忽略 */ }
    await p.waitForTimeout(400)
    await p.evaluate(() => {
      document.querySelectorAll('.mj-hushow').forEach((e) => e.click())
      document.querySelectorAll('.gt-over-card .gt-btn:not(.ghost)').forEach((e) => e.click())
    })
  }
  await p.waitForTimeout(1200)
  const info = await p.evaluate(() => {
    const box = (s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return { w: Math.round(r.width), h: Math.round(r.height) } }
    return {
      center: box('.mj-center'),
      disUp: box('.mj-dis-up'), disDown: box('.mj-dis-down'),
      disLeft: box('.mj-dis-left'), disRight: box('.mj-dis-right'),
      nLeft: document.querySelectorAll('.mj-dis-left > .gt-tile').length,
      nUp: document.querySelectorAll('.mj-dis-up > .gt-tile').length,
      shell: box('.gt-shell.mj'),
    }
  })
  console.log(JSON.stringify(info))
  await p.screenshot({ path: '../artifacts/_probe/mj44-desktop.png' })
  await b.close()
})()
