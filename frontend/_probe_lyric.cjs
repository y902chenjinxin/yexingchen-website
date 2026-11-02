/**
 * 现网播放页歌词实测：登录 → /music → 播放第一首 → /now-playing → 量歌词几何
 * 目的：确认「当前行是否在中间」「容器高度是否被限制」「是否真的滚动了」
 *
 * 跑法：node _probe_lyric.cjs
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

const measure = () => {
  const box = document.querySelector('.fp-lyric')
  if (!box) return { ok: false, why: 'no .fp-lyric' }
  const cs = getComputedStyle(box)
  const lines = [...box.querySelectorAll('.fp-lyric-line')]
  const act = box.querySelector('.fp-lyric-line.on')
  const br = box.getBoundingClientRect()
  const ar = act ? act.getBoundingClientRect() : null
  const stage = document.querySelector('.fp-stage')
  const bar = document.querySelector('.fp-bar')
  return {
    ok: true,
    winH: window.innerHeight,
    boxH: Math.round(br.height),
    boxTop: Math.round(br.top),
    boxBottom: Math.round(br.bottom),
    cssHeight: cs.height,
    cssPadding: cs.paddingTop + '/' + cs.paddingBottom,
    scrollTop: Math.round(box.scrollTop),
    scrollH: Math.round(box.scrollHeight),
    clientH: box.clientHeight,
    lineCount: lines.length,
    lineH: lines[0] ? Math.round(lines[0].getBoundingClientRect().height) : 0,
    activeIdx: act ? lines.indexOf(act) : -1,
    activeTop: ar ? Math.round(ar.top) : null,
    activeCenter: ar ? Math.round(ar.top + ar.height / 2) : null,
    boxCenter: Math.round(br.top + br.height / 2),
    stageH: stage ? Math.round(stage.getBoundingClientRect().height) : null,
    barTop: bar ? Math.round(bar.getBoundingClientRect().top) : null,
    synced: !box.classList.contains('no-sync'),
    timeText: (document.querySelector('.fp-time') || {}).textContent || '',
    audioT: (() => { const a = document.querySelector('audio'); return a ? Math.round(a.currentTime * 10) / 10 : 'no-audio' })(),
    audioPaused: (() => { const a = document.querySelector('audio'); return a ? a.paused : 'no-audio' })(),
  }
}

;(async () => {
  const { acc, pw } = creds()
  const b = await chromium.launch()
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 })
  const p = await ctx.newPage()
  p.on('pageerror', (e) => console.log('[pageerror]', e.message))

  console.log('1) 登录…')
  await p.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(1000)
  await p.fill('input[placeholder*="邮箱"], input[placeholder*="账号"]', acc).catch(() => {})
  await p.fill('input[type="password"]', pw)
  await p.click('button:has-text("登录"), button[type="submit"]')
  await p.waitForTimeout(3000)
  console.log('   url =', p.url())

  console.log('2) 进音乐页并播放第一首…')
  await p.goto(`${BASE}/music`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(2000)
  const playBtn = await p.$('.mini-btn.play-btn')
  if (playBtn) { await playBtn.click() } else { console.log('   !! 没找到播放按钮') }
  await p.waitForTimeout(1500)

  console.log('3) 打开全屏播放页…')
  await p.goto(`${BASE}/now-playing`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(2500)

  // 进播放页后可能被暂停（路由切换），点一下播放
  const bigPlay = await p.$('.fp-play')
  if (bigPlay) { await bigPlay.click().catch(() => {}) }
  console.log('   播放中：', await p.evaluate(() => (document.querySelector('.fp-info-title')||{}).textContent))
  await p.waitForTimeout(3000)
  // 点第 8 句 → 跳到那句的时间点（歌词行自带 @click seek），这样不用干等
  const line8 = await p.$('.fp-lyric-line:nth-child(8)')
  if (line8) await line8.click().catch(() => {})
  await p.waitForTimeout(4000)

  const m1 = await p.evaluate(measure)
  console.log('4) 量几何：', JSON.stringify(m1, null, 2))

  await p.screenshot({ path: path.join(OUT, 'lyric-probe.png') })
  console.log('   截图 ->', path.join(OUT, 'lyric-probe.png'))

  await b.close()
})().catch((e) => { console.error(e); process.exit(1) })
