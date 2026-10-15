/**
 * v2.46.90 探针3：外部驱动对局（轮到我方→不要/提示出牌），页面内 120ms 采样席位尺寸
 * 用法：cd frontend && node _probe_gd_avatar3.cjs
 */
const { chromium } = require('playwright')

;(async () => {
  const browser = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await browser.newContext({ viewport: { width: 393, height: 852 }, deviceScaleFactor: 2 })
  const page = await ctx.newPage()
  await page.goto('http://127.0.0.1:5199/_probe.html?g=gd', { waitUntil: 'domcontentloaded', timeout: 30000 })
  await page.waitForTimeout(1000)

  // 页面内：持续采样席位，变化时推入 window.__evts
  await page.evaluate(() => {
    window.__evts = []
    const snap = () => Array.from(document.querySelectorAll('.gt-seat')).map((el) => {
      const r = el.getBoundingClientRect()
      const av = el.querySelector('.gt-seat-av')
      const ar = av ? av.getBoundingClientRect() : null
      const cs = av ? getComputedStyle(av) : null
      return {
        cls: el.className.replace(/gt-seat\s?/g, '').trim(),
        w: Math.round(r.width), h: Math.round(r.height),
        avW: ar ? Math.round(ar.width) : 0, avH: ar ? Math.round(ar.height) : 0,
        font: cs ? cs.fontSize : '',
      }
    })
    window.__prev = JSON.stringify(snap())
    window.__t0 = Date.now()
    window.__iv = setInterval(() => {
      const s = JSON.stringify(snap())
      if (s !== window.__prev) { window.__evts.push({ t: Date.now() - window.__t0, s }); window.__prev = s }
    }, 120)
  })

  const t0 = Date.now()
  let played = 0
  while (Date.now() - t0 < 45000) {
    const passOk = await page.$eval('.gd-pass-big', (b) => !b.disabled).catch(() => false)
    const playBtn = await page.$('.gd-play-big')
    const playOk = await page.$eval('.gd-play-big', (b) => !b.disabled).catch(() => false)
    if (passOk) { await page.$eval('.gd-pass-big', (b) => b.click()); played++ }
    else if (playOk) { await page.$eval('.gd-play-big', (b) => b.click()); played++ }
    else {
      await page.$eval('.gd-hand .gt-card', (el) => el.click()).catch(() => {})
      await page.waitForTimeout(320)
      const ok = await page.$eval('.gd-play-big', (b) => !b.disabled).catch(() => false)
      if (ok) { await page.$eval('.gd-play-big', (b) => b.click()); played++ }
    }
    await page.waitForTimeout(340)
  }

  const evts = await page.evaluate(() => { clearInterval(window.__iv); return window.__evts })
  const seen = new Set()
  for (const e of evts) {
    const arr = JSON.parse(e.s)
    const key = arr.map((c) => c.cls + '|' + c.avW + 'x' + c.avH + '@' + c.font + '|seat ' + c.w + 'x' + c.h).join(' ;; ')
    if (!seen.has(key)) { seen.add(key); console.log(e.t + 'ms ' + key) }
  }
  console.log('EVENTS: ' + evts.length + ' UNIQUE: ' + seen.size + ' MY_ACTIONS: ' + played)
  const dbg = await page.evaluate(() => ({
    pass: (() => { const b = document.querySelector('.gd-pass-big'); return b ? { disabled: b.disabled, vis: !!b.offsetParent } : null })(),
    play: (() => { const b = document.querySelector('.gd-play-big'); return b ? { disabled: b.disabled, vis: !!b.offsetParent } : null })(),
    turn: document.querySelector('.gd-turnbox')?.textContent.replace(/\s+/g, ' ').trim(),
    thz: document.querySelectorAll('.gd-thz-who').length,
    handN: document.querySelectorAll('.gd-hand .gt-card').length,
  }))
  console.log('DBG: ' + JSON.stringify(dbg))
  await page.screenshot({ path: '../artifacts/_probe/gd-avatar3-end.png' })
  await browser.close()
})()
