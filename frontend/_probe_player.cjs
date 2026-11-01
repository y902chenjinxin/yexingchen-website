/** 全屏播放器（Folia 风格改版）本地验收
 *  不碰 /music（dev 下被代理到后端）：直接 mock「上次听到哪」，让 App 启动即恢复曲目，
 *  再点底部播放条信息区进入 /now-playing —— 与真实用户路径一致。
 *  用法：PROBE_BASE=http://localhost:5303 node _probe_player.cjs
 */
const { chromium } = require('playwright')
const BASE = process.env.PROBE_BASE || 'http://localhost:5303'
const b64u = (o) => Buffer.from(JSON.stringify(o)).toString('base64url')
const JWT = [b64u({ alg: 'HS256', typ: 'JWT' }), b64u({ sub: '1', exp: Math.floor(Date.now() / 1000) + 86400 * 30 }), 'sig' ].join('.')

/* 2 秒静音 WAV */
function silentWav() {
  const rate = 8000, samples = rate * 2
  const buf = Buffer.alloc(44 + samples)
  buf.write('RIFF', 0); buf.writeUInt32LE(36 + samples, 4); buf.write('WAVE', 8)
  buf.write('fmt ', 12); buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(1, 22)
  buf.writeUInt32LE(rate, 24); buf.writeUInt32LE(rate, 28); buf.writeUInt16LE(1, 32); buf.writeUInt16LE(8, 34)
  buf.write('data', 36); buf.writeUInt32LE(samples, 40)
  buf.fill(128, 44)
  return buf
}

const TRACKS = [
  { id: 1, title: '今日見た夕陽も 零れ落ち', artist: 'ロスト・シルフィード', duration: 269, category: '日系' },
  { id: 2, title: '夜航西飞', artist: '陈鸿宇', duration: 245, category: '民谣' },
  { id: 3, title: 'Pink + White', artist: 'Frank Ocean', duration: 184, category: 'R&B' },
]

;(async () => {
  const b = await chromium.launch()
  for (const vp of [
    { name: 'mobile', width: 390, height: 844, isMobile: true },
    { name: 'desktop', width: 1440, height: 900, isMobile: false },
  ]) {
    const ctx = await b.newContext({
      viewport: { width: vp.width, height: vp.height },
      isMobile: vp.isMobile, hasTouch: true, deviceScaleFactor: 2,
    })
    await ctx.route((u) => u.pathname.startsWith('/api/'), (r) => {
      const u = r.request().url()
      const j = (d) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 0, data: d }) })
      if (/\/stream/.test(u)) return r.fulfill({ status: 200, contentType: 'audio/wav', body: silentWav() })
      if (/\/api\/auth\/me/.test(u)) return j({ id: 1, username: 'probe', is_super_admin: 1 })
      if (/\/api\/music\/playback/.test(u)) return j({ track: TRACKS[0], position: 42 })
      if (/\/api\/music\/uploaders/.test(u)) return j([])
      if (/\/api\/music/.test(u)) return j({ list: TRACKS, total: TRACKS.length })
      return j({ list: [], total: 0 })
    })
    await ctx.addInitScript((t) => {
      localStorage.setItem('token', t)
      localStorage.setItem('np_minimized', '0')
    }, JWT)

    const p = await ctx.newPage()
    p.on('pageerror', (e) => { if (!/slice/.test(e.message)) console.log('[pageerror]', e.message.slice(0, 120)) })

    await p.goto(`${BASE}/now-playing`, { waitUntil: 'domcontentloaded', timeout: 60000 })
    await p.waitForTimeout(3200)
    // 点播放键，进入「正在播放」态（标题转暖金）
    await p.evaluate(() => document.querySelector('.fp-play')?.click())
    await p.waitForTimeout(1600)
    console.log(`\n[${vp.name}] url=${p.url()} playing=${await p.evaluate(() => !!document.querySelector('.fp-title.is-playing'))}`)

    const geo = await p.evaluate(() => {
      const box = (s) => { const e = document.querySelector(s); if (!e) return `${s}: none`; const r = e.getBoundingClientRect(); return `${s}: ${Math.round(r.width)}x${Math.round(r.height)} @${Math.round(r.left)},${Math.round(r.top)}` }
      const t = document.querySelector('.fp-title')
      const root = document.querySelector('.fp')
      return {
        rows: ['.fp', '.fp-top', '.fp-stage', '.fp-title', '.fp-sub', '.fp-bar', '.fp-card', '.fp-play', '.fp-range'].map(box),
        title: t ? t.textContent : '(none)',
        font: t ? getComputedStyle(t).fontSize : '-',
        hue: root ? getComputedStyle(root).getPropertyValue('--fp-hue').trim() : '-',
      }
    })
    console.log(JSON.stringify(geo, null, 1))
    await p.screenshot({ path: `artifacts/_probe/player_${vp.name}.png` })

    await p.evaluate(() => document.querySelector('.fp-more')?.click())
    await p.waitForTimeout(700)
    console.log(`[${vp.name}] 面板: ${await p.evaluate(() => !!document.querySelector('.fp-panel'))}`)
    await p.screenshot({ path: `artifacts/_probe/player_${vp.name}_panel.png` })

    /* 下一首：验证主视觉/色相跟着换 */
    await p.evaluate(() => { if (document.querySelector('.fp-panel')) document.querySelector('.fp-more').click() })
    await p.waitForTimeout(300)
    await p.evaluate(() => document.querySelectorAll('.fp-step')[1].click())
    await p.waitForTimeout(1400)
    const after = await p.evaluate(() => ({
      title: document.querySelector('.fp-title')?.textContent,
      hue: getComputedStyle(document.querySelector('.fp')).getPropertyValue('--fp-hue').trim(),
    }))
    console.log(`[${vp.name}] 下一首后:`, JSON.stringify(after))
    await p.screenshot({ path: `artifacts/_probe/player_${vp.name}_next.png` })
    await ctx.close()
  }
  await b.close()
})()
