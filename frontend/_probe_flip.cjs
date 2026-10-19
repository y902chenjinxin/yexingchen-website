/**
 * 翻页时钟探针（v2.46.116）：验证四层翻牌结构与时序（夜星反馈：上半延后更新+卡顿）。
 * 时序断言（每张卡）：
 *   翻转开始瞬间：静态上半 = 新值（不再等 620ms）、翻转上半 = 旧值（倒下去的是旧卡片）
 *   约 300ms：静态下半切新（与翻入的翻转下半同值无缝）
 *   约 600ms：翻转层移除
 * 另量几何（溢出/尺寸）+ 截翻转中一帧。
 * 用法：cd frontend && node _probe_flip.cjs
 */
const { chromium } = require('playwright')

const VW = Number(process.env.VW || 390)

;(async () => {
  const browser = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await browser.newContext({ viewport: { width: VW, height: 844 }, deviceScaleFactor: 2 })
  const page = await ctx.newPage()
  await page.goto('http://localhost:5198/_probe_flip.html', {
    waitUntil: 'domcontentloaded', timeout: 30000,
  })
  await page.waitForTimeout(1500)

  const geo = await page.evaluate(() => {
    const mfcLg = document.querySelector('.mfc.is-lg')
    const card = document.querySelector('.mfc.is-lg .mfc-card')
    const r = card.getBoundingClientRect()
    return {
      vw: innerWidth, vh: innerHeight,
      lgW: Math.round(mfcLg.getBoundingClientRect().width),
      cardW: Math.round(r.width), cardH: Math.round(r.height),
      overflowX: mfcLg.getBoundingClientRect().right > innerWidth,
      cardCount: document.querySelectorAll('.mfc-card').length,
    }
  })
  console.log('geometry:', JSON.stringify(geo))

  // 采样 2.8s：40ms 粒度，覆盖至少 2 次秒位翻转
  const samples = await page.evaluate(() => new Promise((res) => {
    const log = []
    const t0 = performance.now()
    const id = setInterval(() => {
      const now = performance.now() - t0
      log.push({
        t: Math.round(now),
        cards: [...document.querySelectorAll('.mfc.is-lg .mfc-card')].map((c) => ({
          flip: c.classList.contains('is-flip'),
          up: c.querySelector('.mfc-up:not(.mfc-flip-up) span')?.textContent ?? null,
          dn: c.querySelector('.mfc-down:not(.mfc-flip-down) span')?.textContent ?? null,
          fu: c.querySelector('.mfc-flip-up span')?.textContent ?? null,
          fd: c.querySelector('.mfc-flip-down span')?.textContent ?? null,
        })),
      })
      if (now > 2800) { clearInterval(id); res(log) }
    }, 40)
  }))

  // 每张卡找翻转窗口并断言
  let pass = 0, fail = 0
  if (process.env.DUMP) {
    for (const i of [4, 5]) {
      const seq = samples.map((s) => ({ t: s.t, c: s.cards[i] })).filter((x) => x.c)
      console.log(`--- dump card${i} ---`)
      for (const x of seq) {
        console.log(`t=${String(x.t).padStart(4)} flip=${x.c.flip ? 'Y' : '.'} up=${x.c.up} dn=${x.c.dn} fu=${x.c.fu} fd=${x.c.fd}`)
      }
    }
  }
  for (let i = 0; i < 6; i++) {
    const seq = samples.map((s) => ({ t: s.t, c: s.cards[i] })).filter((x) => x.c)
    // 收集所有连续翻转窗口，取最长的一段（避开采样起点错过翻转前段的偶然）
    const wins = []
    let j = seq.findIndex((x) => x.c.flip)
    while (j >= 0 && j < seq.length) {
      if (!seq[j].c.flip) { j++; continue }
      const w = []
      while (j < seq.length && seq[j].c.flip) { w.push(seq[j]); j++ }
      wins.push(w)
    }
    if (!wins.length) { console.log(`card${i}: no flip observed (skipped)`); continue }
    const win = wins.reduce((a, b) => (b.length > a.length ? b : a), [])
    const first = win[0], mid = win[Math.floor(win.length / 2)], last = win[win.length - 1]
    const dur = last.t - first.t
    const newV = first.c.up, oldV = first.c.fu
    const checks = [
      ['static-up=new at t0 (上半不延后)', first.c.up === newV && first.c.up !== oldV],
      ['flip-up=old at t0 (倒下的是旧卡片)', first.c.fu === oldV],
      ['static-down=old at t0', first.c.dn === oldV],
      ['static-down=new by flip end (300ms切新生效)', last.c.dn === newV],
      ['static-down switched within window', win.some((x) => x.c.dn === newV) && win.some((x) => x.c.dn === oldV)],
      ['flip-down=new while flipping', win.some((x) => x.c.fd === newV)],
      ['flip layer removed ~600ms', dur >= 480 && dur <= 900],
    ]
    const ok = checks.every(([, v]) => v)
    ok ? pass++ : fail++
    console.log(`card${i}: ${ok ? 'PASS' : 'FAIL'} (dur=${dur}ms, old=${oldV}→new=${newV})`)
    for (const [name, v] of checks) if (!v) console.log(`   ✗ ${name}`)
  }
  console.log(`--- result: ${pass} pass, ${fail} fail ---`)

  await browser.close()
  process.exit(fail > 0 ? 1 : 0)
})()
