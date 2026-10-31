/**
 * 双击出牌探针（v2.46.311）
 *   node _probe_dblclick.cjs
 * 本地 dev（5301）+ 假 JWT，走单机模式，不碰后端数据。
 */
const { chromium } = require('playwright')
const BASE = 'http://localhost:5301'
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url')
const JWT = [
  b64u({ alg: 'HS256', typ: 'JWT' }),
  b64u({ sub: '1', exp: Math.floor(Date.now() / 1000) + 86400 * 30 }),
  'sig',
].join('.')

async function dblclickAt(p, x, y, gap = 110) {
  await p.mouse.move(x, y)
  await p.mouse.down()
  await p.mouse.up()
  await p.waitForTimeout(gap)
  await p.mouse.down()
  await p.mouse.up()
}

;(async () => {
  const b = await chromium.launch()
  const ctx = await b.newContext({ viewport: { width: 1280, height: 720 } })
  await ctx.route(/localhost:5301\/api\//, (r) =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: { list: [], total: 0 } }) }),
  )
  await ctx.addInitScript((t) => localStorage.setItem('token', t), JWT)
  const p = await ctx.newPage()
  p.on('pageerror', (e) => console.log('[pageerror]', e.message.slice(0, 140)))

  await p.goto(`${BASE}/tool/games`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForTimeout(2200)

  for (const game of ['掼蛋', '四川麻将']) {
    // 进游戏
    await p.evaluate((g) => {
      const el = Array.from(document.querySelectorAll('.gm-item')).find((x) => x.textContent.includes(g))
      el && el.click()
    }, game)
    await p.waitForTimeout(700)
    // 选单人模式
    const modeOk = await p.evaluate(() => {
      const el = Array.from(document.querySelectorAll('button')).find((x) => /单人/.test(x.textContent))
      if (el) { el.click(); return el.textContent.trim().slice(0, 12) }
      return null
    })
    await p.waitForTimeout(500)
    // 开局
    const startOk = await p.evaluate(() => {
      const el = Array.from(document.querySelectorAll('button')).find((x) => /^(开局|开始|开一局)/.test(x.textContent.trim()))
      if (el) { el.click(); return true }
      return false
    })
    await p.waitForTimeout(3500)
    const before = await p.evaluate(() => ({
      cards: document.querySelectorAll('.gd-hand .gt-card').length,
      tiles: document.querySelectorAll('.mj-hand .gt-tile').length,
    }))
    console.log(`[${game}] 模式=${modeOk} 开局=${startOk} 牌数=${JSON.stringify(before)}`)

    if (!before.cards && !before.tiles) { console.log('  没有牌，跳过'); continue }

    // 找一张自己的手牌（最后一张最稳，不会被叠压）
    const box = await p.evaluate(() => {
      const els = Array.from(document.querySelectorAll('.gd-hand .gt-card, .mj-hand .gt-tile'))
      const el = els[els.length - 1]
      if (!el) return null
      const r = el.getBoundingClientRect()
      return { x: r.x + r.width / 2, y: r.y + r.height / 2, w: r.width }
    })
    if (!box) { console.log('  取不到牌坐标'); continue }

    // 先验证「单击只选中不出牌」
    const box2 = await p.evaluate(() => {
      const els = Array.from(document.querySelectorAll('.gd-hand .gt-card, .mj-hand .gt-tile'))
      const el = els[Math.max(0, els.length - 5)]
      if (!el) return null
      const r = el.getBoundingClientRect()
      return { x: r.x + r.width / 2, y: r.y + r.height / 2 }
    })
    if (box2) {
      await p.mouse.move(box2.x, box2.y)
      await p.mouse.down(); await p.mouse.up()
      await p.waitForTimeout(700)
      const one = await p.evaluate(() => ({
        cards: document.querySelectorAll('.gd-hand .gt-card').length,
        tiles: document.querySelectorAll('.mj-hand .gt-tile').length,
      }))
      const same = one.cards === before.cards && one.tiles === before.tiles
      console.log(`  单击后 牌数=${JSON.stringify(one)} → ${same ? '未误出 ✅' : '误出了 ❌'}`)
    }

    await dblclickAt(p, box.x, box.y)
    await p.waitForTimeout(1200)

    const after = await p.evaluate(() => ({
      cards: document.querySelectorAll('.gd-hand .gt-card').length,
      tiles: document.querySelectorAll('.mj-hand .gt-tile').length,
      status: (document.querySelector('.gt-status, .gt-turnpill, .gd-status') || {}).textContent || '',
    }))
    console.log(`  双击后 牌数=${JSON.stringify(after)} → ${after.cards < before.cards || after.tiles < before.tiles ? '出牌成功 ✅' : '没出牌 ❌'}`)
    await p.screenshot({ path: `artifacts/_probe/dbl_${game === '掼蛋' ? 'guandan' : 'mahjong'}.png` })

    // 退出回大厅
    await p.evaluate(() => {
      const el = Array.from(document.querySelectorAll('button')).find((x) => /返回列表|返回/.test(x.textContent))
      el && el.click()
    })
    await p.waitForTimeout(1200)
  }
  await b.close()
})()
