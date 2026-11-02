/**
 * 现网探针：音乐造物主（v2.46.334）
 *
 * 覆盖：登录 → 上传一首示例曲 → 大厅 → 选曲 → 演奏页 → 点开始 → 音符下落/键盘/采样加载
 *
 * 跑法：node _probe_piano.cjs
 */
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const OUT = path.resolve(__dirname, '../artifacts/_probe')
const BASE = process.env.PROBE_BASE || 'https://yexingchen.cn'

function creds() {
  const env = fs.readFileSync('D:/software/codex/codex_work/.secrets/local.env', 'utf8')
  const seg = env.split('#项目网站信息').pop()
  return { acc: /账号：\s*(\S+)/.exec(seg)[1], pw: /密码：\s*(\S+)/.exec(seg)[1] }
}

/** 小星星（C 大调，用本站键位表：C4=K D4=L E4=Q F4=W G4=E A4=R） */
function twinkle() {
  const seq = 'KKEERRE WWQQL LK EEWWQQL EEWWQQL KKEERRE WWQQL LK'
    .replace(/ /g, '')
    .split('')
  const notes = seq.map((key, i) => ({ time: +(i * 0.5).toFixed(3), key, pitch: '', dur: 0.45 }))
  return { title: '小星星（示例）', artist: '公版', bpm: 120, notes, source: 'seed' }
}

;(async () => {
  const { acc, pw } = creds()
  const browser = await chromium.launch({ headless: true })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })
  const page = await ctx.newPage()
  const errs = []
  const audioRes = []
  page.on('pageerror', (e) => errs.push(String(e)))
  page.on('console', (m) => { if (m.type() === 'error') errs.push('console: ' + m.text()) })
  page.on('response', (r) => {
    if (r.url().includes('/sounds/piano/')) audioRes.push(`${r.status()} ${r.url().split('/').pop()}`)
  })

  const login = await page.request.post(BASE + '/api/auth/login', { data: { email: acc, password: pw } })
  const token = (await login.json())?.data?.token
  if (!token) throw new Error('登录失败')

  // 准备一首示例曲（已存在就复用）
  const list0 = await page.request.get(BASE + '/api/songs', { headers: { Authorization: `Bearer ${token}` } })
  const items0 = (await list0.json())?.data?.items || []
  let demo = items0.find((s) => s.title.startsWith('小星星'))
  if (!demo) {
    const r = await page.request.post(BASE + '/api/songs', {
      headers: { Authorization: `Bearer ${token}` },
      data: twinkle(),
    })
    demo = (await r.json())?.data
  }
  console.log('曲库：', items0.length, '首；示例曲 id =', demo?.id, demo?.title)

  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
  await page.evaluate((t) => localStorage.setItem('token', t), token)

  // ---- 大厅 ----
  await page.goto(BASE + '/tool/piano', { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('.pl', { timeout: 20000 })
  await page.waitForTimeout(800)
  const hall = await page.evaluate(() => ({
    tip: !!document.querySelector('.pl-tip'),
    inst: !!document.querySelector('.pl-inst'),
    keys: document.querySelectorAll('.pl-inst-key').length,
  }))
  console.log('大厅：', JSON.stringify(hall))
  await page.screenshot({ path: path.join(OUT, 'piano-hall.png') })

  // ---- 选曲 ----
  await page.click('.pl-inst')
  await page.waitForTimeout(600)
  const songs = await page.evaluate(() => ({
    items: document.querySelectorAll('.pl-item').length,
    first: (document.querySelector('.pl-item-main b') || {}).textContent || '',
  }))
  console.log('选曲：', JSON.stringify(songs))
  await page.screenshot({ path: path.join(OUT, 'piano-songs.png') })

  // ---- 演奏 ----
  await page.click('.pl-item-play')
  // 等到「开始演奏」按钮出现（loading / ready 两种覆盖层都叫 .pp-ov-box，会被抢先匹配）
  await page.waitForSelector('.pp-btn.primary', { timeout: 30000 })
  await page.waitForTimeout(400)
  const ready = await page.evaluate(() => ({
    lead: (document.querySelector('.pp-ov-lead') || {}).textContent || '',
    notes: document.querySelectorAll('.pp-note').length,
    white: document.querySelectorAll('.pk-key--white').length,
    black: document.querySelectorAll('.pk-key--black').length,
  }))
  console.log('准备页：', JSON.stringify(ready))
  await page.screenshot({ path: path.join(OUT, 'piano-ready.png') })

  await page.click('.pp-btn.primary')
  // ⚠️ 等「遮罩消失」而不是等 .pp-count 消失：倒计时之前 .pp-count 本来就不存在，
  //    等它消失会在 t=0 立刻返回，量到的自然是"还没开始动"。
  await page.waitForFunction(() => !document.querySelector('.pp-overlay'), null, { timeout: 20000 })
  await page.waitForTimeout(700)
  const playing = await page.evaluate(() => ({
    phase: !!document.querySelector('.pp-count'),
    transform: getComputedStyle(document.querySelector('.pp-roll')).transform,
    noteTop: document.querySelector('.pp-note') ? document.querySelector('.pp-note').getBoundingClientRect().top : -1,
  }))
  await page.waitForTimeout(1500)
  const after = await page.evaluate(() => ({
    transform: getComputedStyle(document.querySelector('.pp-roll')).transform,
    noteTop: document.querySelector('.pp-note') ? document.querySelector('.pp-note').getBoundingClientRect().top : -1,
  }))

  // 按键：K 应该发声且键亮
  await page.keyboard.down('k')
  await page.waitForTimeout(120)
  const keyOn = await page.evaluate(() => document.querySelectorAll('.pk-key.on').length)
  await page.keyboard.up('k')

  await page.screenshot({ path: path.join(OUT, 'piano-playing.png') })

  // 音符列必须与琴键列严格对齐（差 1~2px 是取整，超过 4px 就是映射算错了）
  const align = await page.evaluate(() => {
    const out = []
    for (const n of document.querySelectorAll('.pp-note')) {
      const r = n.getBoundingClientRect()
      if (r.top < 0 || r.top > window.innerHeight) continue
      const key = n.textContent.trim()
      const k = document.querySelector(`.pk-key[data-key="${key}"]`)
      if (!k) continue
      const kr = k.getBoundingClientRect()
      out.push({ key, dx: Math.round((r.left + r.width / 2) - (kr.left + kr.width / 2)) })
    }
    return out
  })
  const worst = align.reduce((m, a) => Math.max(m, Math.abs(a.dx)), 0)
  console.log('音符/琴键横向偏差：', align.length, '个样本，最大', worst, 'px')

  console.log('演奏中：', JSON.stringify(playing))
  console.log('1.5s 后：', JSON.stringify(after))
  console.log('按键高亮：', keyOn, '个；采样：', audioRes.length, '个 →', audioRes.slice(0, 3).join(', '))

  const problems = []
  if (hall.tip) problems.push('桌面端错误显示了手机提示')
  if (!hall.inst) problems.push('大厅没有钢琴卡片')
  if (!songs.items) problems.push('选曲列表为空')
  if (!ready.notes) problems.push('演奏页没有音符')
  if (ready.white !== 18 || ready.black !== 10) problems.push(`键数不对：白 ${ready.white} 黑 ${ready.black}`)
  if (playing.transform === after.transform) problems.push('音符没有下落（transform 没变）')
  if (!(after.noteTop > playing.noteTop)) problems.push('音符没有向下落（方向反了）')
  if (keyOn !== 1) problems.push('按下 K 键没有高亮')
  if (audioRes.length < 12) problems.push(`采样只加载了 ${audioRes.length}/12`)
  if (audioRes.some((r) => !r.startsWith('200'))) problems.push('有采样返回非 200：' + audioRes.filter((r) => !r.startsWith('200')).join(','))
  if (align.length && worst > 4) problems.push(`音符与琴键没对齐（最大偏 ${worst}px）`)
  if (errs.length) problems.push('页面报错：' + errs.slice(0, 3).join(' | '))

  console.log(problems.length ? '❌ ' + problems.join('\n❌ ') : '✅ 全部通过')
  await browser.close()
  process.exit(problems.length ? 1 : 0)
})().catch((e) => { console.error('探针失败：', e.message); process.exit(2) })
