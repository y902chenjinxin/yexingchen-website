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
  // 不进全屏缩放链路（= 手机自带浏览器桌面版布局）—— 夜星截到的「底部被遮挡」就是这一形态
  { g: 'mp', nofs: 1, name: 'wide-monopoly-nofs' },
  // 复刻夜星那张截图：桌面版 viewport 1280 × 592（手机横屏 + 桌面版视口），双栏布局
  { g: 'mp', nofs: 1, vp: [1280, 592], name: 'wide-monopoly-nofs-1280' },
  { g: 'mj', name: 'wide-mahjong' },
  { g: 'gd', name: 'wide-guandan' },
  // 在线视角：我坐 1 / 3 号位时，牌桌该按我的方位转（本地单机永远坐 0 号位，看不出旋转）
  { g: 'gd', seat: 1, name: 'wide-guandan-seat1' },
  { g: 'gd', seat: 3, name: 'wide-guandan-seat3' },
  // 牌面检视台：三门 × 1~9（用来肉眼核对条子的排列与配色）
  { g: 'tiles', name: 'wide-tiles', vp: [640, 420] },
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
    if (c.vp) await page.setViewportSize({ width: c.vp[0], height: c.vp[1] })
    try {
      await page.goto(`http://[::1]:5199/_probe.html?g=${c.g}${c.seat === undefined ? '' : '&seat=' + c.seat}${c.nofs ? '&nofs=1' : ''}`, { waitUntil: 'domcontentloaded', timeout: 30000 })
    } catch (e) {
      console.log('===== ' + c.name + ' 打开失败 =====\n' + e.message)
      await page.close()
      continue
    }
    await page.waitForTimeout(2200)
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
      await page.waitForTimeout(1200)
      // 自己打几张，把四家的弃牌都喂出来。注意 AI 现在要 2~3s 才出一张，
      // 所以必须**等轮到自己**（手牌带 .pickable）再点，不能盲点。
      const rounds = Number(new URLSearchParams(await page.url().split('?')[1] || '').get('rounds') || 8)
      for (let i = 0; i < rounds; i++) {
        let ready = false
        for (let w = 0; w < 25; w++) {
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
        await page.waitForTimeout(600)
      }
      await page.evaluate(() => document.querySelectorAll('.gt-over').forEach((e) => e.remove()))
      await page.waitForTimeout(400)
    }

    let gather = null
    let mjSwipe = null
    if (c.g === 'mj') {
      // 上滑出牌手势：等轮到自己 → 在首张手牌上按住向上拖 54px 再松开，
      // 看「自己的弃牌区（.mj-dis-down）」有没有多出一张。
      let ready = false
      for (let w = 0; w < 30; w++) {
        if (await page.$('.mj-hand .gt-tile.pickable')) { ready = true; break }
        await page.waitForTimeout(400)
      }
      if (!ready) mjSwipe = { err: '30 次轮询内没轮到自己' }
      else {
        try {
          const before = await page.$$eval('.mj-dis-down .gt-tile', (e) => e.length)
          const pt = await page.$eval('.mj-hand .gt-tile.pickable', (el) => {
            const r = el.getBoundingClientRect()
            return { x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height * 0.72) }
          })
          await page.mouse.move(pt.x, pt.y)
          await page.mouse.down()
          await page.mouse.move(pt.x, pt.y - 24, { steps: 4 })
          await page.waitForTimeout(60)
          const lifted = await page.$$eval('.mj-hand .gt-tile.is-lift', (e) => e.length)
          await page.mouse.move(pt.x, pt.y - 54, { steps: 4 })
          await page.mouse.up()
          await page.waitForTimeout(600)
          const after = await page.$$eval('.mj-dis-down .gt-tile', (e) => e.length)
          mjSwipe = { before, after, lifted, played: after > before }
        } catch (e) { mjSwipe = { err: String(e).slice(0, 90) } }
      }
    }
    if (c.g === 'gd') {
      // 点「同花顺」验证：①是否把这一组汇总到手牌**最左**；②顺序是否从小到大
      gather = []
      for (const label of ['同花顺', '顺子']) {
        const btns = await page.$$('.gd-actions .gt-btn')
        let hit = null
        for (const b of btns) {
          const t = (await b.innerText()).replace(/\s+/g, '')
          if (t.startsWith(label)) hit = b
        }
        if (!hit) { gather.push({ label, missing: true }); continue }
        const disabled = await hit.isDisabled()
        if (disabled) { gather.push({ label, disabled: true }); continue }
        await hit.click()
        await page.waitForTimeout(350)
        const snap = await page.evaluate(() => {
          const cards = Array.from(document.querySelectorAll('.gd-hand .gt-card'))
          const txt = (el) => el.textContent.replace(/\s+/g, '').slice(0, 3)
          return {
            selCount: cards.filter((el) => el.classList.contains('is-sel')).length,
            headSelected: cards.slice(0, 5).every((el) => el.classList.contains('is-sel')),
            head: cards.slice(0, 6).map(txt),
            tailHead: cards.slice(5, 8).map(txt),
          }
        })
        gather.push({ label, ...snap })
        await page.screenshot({ path: `../artifacts/_probe/${c.name}-${label}.png` })
        // 取消选中，回到原顺序，好让下一个按钮从干净状态开始
        const re = await page.$$('.gd-actions .gt-btn')
        for (const b of re) {
          const t = (await b.innerText()).replace(/\s+/g, '')
          if (t.startsWith('重选')) await b.click()
        }
        await page.waitForTimeout(250)
      }
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
        rotTransform: (() => { const el = q('#probe-rot'); return el ? getComputedStyle(el).transform : null })(),
        winH: window.innerHeight,
        winW: window.innerWidth,
        mpBoard: box('.mp-board'),
        mpWrap: box('.mp-boardwrap'),
        mpCellVars: (() => {
          const el = q('.mp-board')
          if (!el) return null
          const c = getComputedStyle(el)
          return {
            cw: c.getPropertyValue('--mp-cw').trim(),
            ch: c.getPropertyValue('--mp-ch').trim(),
            cell: c.getPropertyValue('--mp-cell').trim(),
          }
        })(),
        mpNameSize: (() => { const el = q('.mp-cname'); return el ? getComputedStyle(el).fontSize : null })(),
        mpTokSize: (() => { const el = q('.mp-tok'); if (!el) return null; const r = el.getBoundingClientRect(); return { w: Math.round(r.width), h: Math.round(r.height) } })(),
        // 「底部被遮挡」的硬证据：外壳 / 右栏 / 操作区的下沿有没有超出视口
        mpShellBox: box('.gt-shell.mp'),
        mpSideBottom: (() => { const el = q('.mp-side'); return el ? Math.round(el.getBoundingClientRect().bottom) : null })(),
        mpSideScroll: (() => { const el = q('.mp-side'); return el ? { sh: el.scrollHeight, ch: el.clientHeight } : null })(),
        mpOpsBottom: (() => { const el = q('.mp-ops'); return el ? Math.round(el.getBoundingClientRect().bottom) : null })(),
        mpCenter: box('.mp-center'),
        mpCenterKids: kids('.mp-center'),
        mpDice: box('.mp-dice'),
        diceItems: kids('.mp-dice'),
        dicePips: (() => {
          const svg = q('.mp-dice svg')
          if (!svg) return null
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
        // 底部各段占高 —— 弃牌区能长多高完全由这里决定
        mjBottom: box('.mj-bottom'),
        mjHandbar: box('.mj-handbar'),
        mjHand: box('.mj-hand'),
        mjActions: box('.mj-actions'),
        mjSeatTop: box('.mj-seat-top'),
        mjSeatCard: box('.mj-seat-top .gt-seat'),
        mjShell: box('.gt-shell.mj'),
        mjPadding: (() => { const el = document.querySelector('.gt-shell.mj'); if (!el) return null; const c = getComputedStyle(el); return `${c.paddingTop}/${c.paddingBottom} gap=${c.rowGap}` })(),
        mjTablePadding: (() => { const el = document.querySelector('.mj-table'); if (!el) return null; const c = getComputedStyle(el); return `${c.paddingTop}/${c.paddingBottom} gap=${c.rowGap}` })(),
        // 四方弃牌各自落在哪 —— 判断「牌有没有放在自己那边」的依据
        mjDis: ['.mj-dis-up', '.mj-dis-left', '.mj-dis-right', '.mj-dis-down'].map((sel) => {
          const el = document.querySelector(sel)
          if (!el) return { sel, missing: true }
          const r = el.getBoundingClientRect()
          const k = el.querySelector('.gt-tile')
          const kr = k ? k.getBoundingClientRect() : null
          return {
            sel,
            box: { w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x), y: Math.round(r.y) },
            n: el.children.length,
            cols: getComputedStyle(el).gridTemplateColumns,
            st: getComputedStyle(el).gridArea,
            tile: kr ? { w: Math.round(kr.width), h: Math.round(kr.height), x: Math.round(kr.x), y: Math.round(kr.y) } : null,
          }
        }),
        mjSeatBoxes: ['.mj-seat-top', '.mj-seat-left', '.mj-seat-right', '.mj-seat-bottom'].map((sel) => ({
          sel, ...(box(sel) || { missing: true }),
        })),
        // 缺门置灰（四川麻将定缺）：手牌里属于缺门的牌应带 .is-miss 且被去饱和
        mjMiss: (() => {
          const els = Array.from(document.querySelectorAll('.mj-hand .gt-tile.is-miss'))
          const one = els[0]
          return {
            n: els.length,
            filter: one ? getComputedStyle(one).filter : null,
            badge: one ? getComputedStyle(one, '::after').content : null,
            handTotal: document.querySelectorAll('.mj-hand .gt-tile').length,
          }
        })(),
        mjHint: (() => { const el = q('.mj-hint'); return el ? el.textContent.replace(/\s+/g, ' ').trim() : null })(),

        /* ---------- 掼蛋 ---------- */
        gdTable: box('.gd-table'),
        gdMain: box('.gd-main'),
        gdCenter: box('.gd-center'),
        gdCards: box('.gd-center-cards'),
        gdRowTop: box('.gd-row-top'),
        gdTurn: box('.gd-turnbox'),
        gdTurnText: (() => { const el = q('.gd-turnbox'); return el ? el.textContent.replace(/\s+/g, ' ').trim() : null })(),
        gdHistory: box('.gd-history'),
        gdHistoryPos: (() => { const el = q('.gd-history'); return el ? getComputedStyle(el).position : null })(),
        gdSeats: ['.gd-row-top .gt-seat', '.gd-row-mid .gt-seat', '.gd-row-mid .gt-seat:last-of-type'].map((sel) => box(sel)),
        // 「视角跟不跟着我的座位转」的文本证据：三家各显示谁
        gdSeatNames: ['.gd-row-top .gt-seat .gt-seat-name', '.gd-row-mid .gt-seat .gt-seat-name', '.gd-row-mid .gt-seat:last-of-type .gt-seat-name']
          .map((sel) => { const el = q(sel); return el ? el.textContent.trim() : null }),
        gdHandTag: (() => { const el = q('.gd-hand-tag'); return el ? el.textContent.trim() : null })(),
        gdTimer: (() => { const el = q('.gd-timer'); return el ? el.textContent.replace(/\s+/g, ' ').trim() : null })(),
        // 操作按钮是否在手牌**上方**（夜星第 5 条）
        gdActionsAboveHand: (() => {
          const a = q('.gd-actions'); const h = q('.gd-hand')
          if (!a || !h) return null
          return { actionsY: Math.round(a.getBoundingClientRect().y), handY: Math.round(h.getBoundingClientRect().y), above: a.getBoundingClientRect().y < h.getBoundingClientRect().y }
        })(),
        gdBottom: box('.gd-bottom'),
        gdHand: box('.gd-hand'),
        gdHandKids: (() => { const el = q('.gd-hand'); return el ? el.children.length : null })(),
        gdCard: box('.gd .gt-card'),
        gdActions: box('.gd-actions'),
        // 重叠检测：「挤一块」的硬证据 —— 任何一对相交都算问题
        gdOverlaps: (() => {
          const rects = {
            '出牌记录': q('.gd-history'),
            '左家': q('.gd-row-mid .gt-seat'),
            '右家': q('.gd-row-mid .gt-seat:last-of-type'),
            '中央区': q('.gd-center'),
            '轮到谁': q('.gd-turnbox'),
            '对家': q('.gd-row-top .gt-seat'),
            '出的牌': q('.gd-center-cards'),
          }
          const keys = Object.keys(rects)
          const out = []
          for (let i = 0; i < keys.length; i++) {
            for (let j = i + 1; j < keys.length; j++) {
              const a = rects[keys[i]]; const b = rects[keys[j]]
              if (!a || !b) continue
              const ra = a.getBoundingClientRect(); const rb = b.getBoundingClientRect()
              const w = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left)
              const h = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top)
              if (w > 1 && h > 1) out.push(`${keys[i]}×${keys[j]} ${Math.round(w)}×${Math.round(h)}`)
            }
          }
          return out
        })(),
      }
    })
    console.log('===== ' + c.name + ' =====')
    console.log(JSON.stringify(info, null, 1))
    if (gather) console.log('GATHER: ' + JSON.stringify(gather))
    if (mjSwipe) console.log('MJ_SWIPE: ' + JSON.stringify(mjSwipe))
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
