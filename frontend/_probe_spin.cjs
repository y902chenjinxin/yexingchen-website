/**
 * 现网抽签转盘实测：登录 → /tool/spin → 拖拽转盘 → 等它停 → 校验落点。
 *
 * 校验口径（这是这套物理的核心承诺）：
 *   停稳后「指针角度」必须正好落在某个扇区的中线上（±0.6°），
 *   且结果文字 == 指针所属扇区的标签。
 *
 * 跑法：node _probe_spin.cjs
 */
const { chromium } = require('playwright')
const path = require('path')

const OUT = path.resolve(__dirname, '../artifacts/_probe')
const BASE = process.env.PROBE_BASE || 'https://yexingchen.cn'
const fs = require('fs')

function creds() {
  const env = fs.readFileSync('D:/software/codex/codex_work/.secrets/local.env', 'utf8')
  const seg = env.split('#项目网站信息').pop()
  return { acc: /账号：\s*(\S+)/.exec(seg)[1], pw: /密码：\s*(\S+)/.exec(seg)[1] }
}

const state = () => {
  const w = document.querySelector('.sp-wheel')
  if (!w) return { ok: false, why: 'no .sp-wheel' }
  const t = getComputedStyle(w).transform
  let deg = 0
  if (t && t !== 'none') {
    const m = t.match(/matrix\(([^)]+)\)/)
    if (m) {
      const [a, b] = m[1].split(',').map(Number)
      deg = (Math.atan2(b, a) * 180) / Math.PI
    }
  }
  const cfgRaw = localStorage.getItem('xuanhuang-spin-v1') || '{}'
  let cfg = {}
  try { cfg = JSON.parse(cfgRaw) } catch { /* 忽略 */ }
  const cur = (cfg.configs || []).find((c) => c.id === cfg.activeId) || (cfg.configs || [])[0] || {}
  const opts = cur.options || []
  const total = opts.reduce((s, o) => s + Math.max(1, o.weight || 1), 0) || 1
  let acc = 0
  const mids = opts.map((o) => {
    const span = (Math.max(1, o.weight || 1) / total) * 360
    const mid = acc + span / 2
    acc += span
    return { mid, span, label: o.label }
  })
  const mod = (v, m) => ((v % m) + m) % m
  const a = mod(-deg, 360)
  let hit = null
  let cum = 0
  for (const s of mids) {
    if (a < cum + s.span) { hit = s; break }
    cum += s.span
  }
  return {
    ok: true,
    rot: Math.round(deg * 100) / 100,
    pointer: Math.round(a * 100) / 100,
    spinning: w.classList.contains('spinning'),
    fast: w.classList.contains('is-fast'),
    result: (document.querySelector('.sp-result-text') || {}).textContent || '',
    hint: (document.querySelector('.sp-result-hint') || {}).textContent || '',
    hitLabel: hit ? hit.label : '',
    offsetFromMid: hit ? Math.round((a - hit.mid) * 100) / 100 : null,
    wheelRect: (() => { const r = w.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height } })(),
  }
}

;(async () => {
  const { acc, pw } = creds()
  const browser = await chromium.launch({ headless: true })
  const ctx = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
    deviceScaleFactor: 3,
  })
  const page = await ctx.newPage()
  const errs = []
  page.on('pageerror', (e) => errs.push(String(e)))
  page.on('console', (m) => { if (m.type() === 'error') errs.push('console: ' + m.text()) })

  // 登录
  const r = await page.request.post(BASE + '/api/auth/login', { data: { email: acc, password: pw } })
  const j = await r.json()
  const token = j?.data?.token
  if (!token) throw new Error('登录失败: ' + JSON.stringify(j).slice(0, 200))
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
  await page.evaluate((t) => localStorage.setItem('token', t), token)

  await page.goto(BASE + '/tool/spin', { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('.sp-wheel', { timeout: 25000 })
  await page.waitForTimeout(1200)

  console.log('初始：', JSON.stringify(await page.evaluate(state)))

  // ---- 测试 1：轻点（不滑）应只出提示、不转 ----
  const box = await page.evaluate(() => {
    const w = document.querySelector('.sp-wheel')
    const r = w.getBoundingClientRect()
    return { cx: r.x + r.width / 2, cy: r.y + r.height / 2, r: r.width / 2 }
  })
  await page.mouse.move(box.cx + box.r * 0.6, box.cy)
  await page.mouse.down()
  await page.mouse.up()
  await page.waitForTimeout(400)
  const tap = await page.evaluate(state)
  console.log('轻点后：', JSON.stringify({ rot: tap.rot, hint: tap.hint, spinning: tap.spinning }))

  // ---- 测试 2：绕圆心快速划一段（模拟手指转盘）----
  const R = box.r * 0.72
  const pt = (deg) => {
    const rad = (deg * Math.PI) / 180
    return { x: box.cx + Math.sin(rad) * R, y: box.cy - Math.cos(rad) * R }
  }
  const start = pt(-30)
  await page.mouse.move(start.x, start.y)
  await page.mouse.down()
  for (let d = -30; d <= 150; d += 8) {
    const p = pt(d)
    await page.mouse.move(p.x, p.y)
    await page.waitForTimeout(12)
  }
  await page.mouse.up()
  const atRelease = await page.evaluate(state)
  console.log('松手：', JSON.stringify({ rot: atRelease.rot, spinning: atRelease.spinning, fast: atRelease.fast }))

  // 等停稳（v2.46.331 起是"变速自行车"，最长 30s，这里给 34s 余量）
  const t0 = Date.now()
  let settled = atRelease
  while (Date.now() - t0 < 34000) {
    settled = await page.evaluate(state)
    if (!settled.spinning) break
    await page.waitForTimeout(150)
  }
  await page.waitForTimeout(400)
  const fin = await page.evaluate(state)
  console.log('停稳：', JSON.stringify({
    ms: Date.now() - t0, rot: fin.rot, pointer: fin.pointer, offsetFromMid: fin.offsetFromMid,
    hit: fin.hitLabel, result: fin.result, spinning: fin.spinning,
  }))

  await page.screenshot({ path: path.join(OUT, 'spin-probe.png') })

  // ---- 断言 ----
  const problems = []
  if (fin.spinning) problems.push('34 秒还没停')
  if (fin.ms > 30500) problems.push('超过 30 秒上限：' + fin.ms + 'ms')
  if (fin.offsetFromMid == null || Math.abs(fin.offsetFromMid) > 0.8) problems.push('落点没对准中线：' + fin.offsetFromMid)
  if (!fin.result) problems.push('没有展示结果')
  if (fin.result !== fin.hitLabel) problems.push(`结果(${fin.result}) ≠ 指针所指(${fin.hitLabel})`)
  if (fin.rot === atRelease.rot) problems.push('松手后没有惯性转动')
  if (errs.length) problems.push('页面报错：' + errs.slice(0, 3).join(' | '))
  console.log(problems.length ? '❌ ' + problems.join('\n❌ ') : '✅ 全部通过')

  await browser.close()
  process.exit(problems.length ? 1 : 0)
})().catch((e) => { console.error('探针失败：', e.message); process.exit(2) })
