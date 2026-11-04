/**
 * 本地液态玻璃观感探针（仅开发用）
 * 起 vite dev（端口 5199）+ 本地后端（8000）后：
 *   cd frontend && node _probe_glass.cjs
 * 产出：artifacts/_probe/glass-*.png（竖屏 390×844 dpr2，开触摸模拟）
 */
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const OUT = path.resolve(__dirname, '../artifacts/_probe')
const BASE = process.env.PROBE_BASE || 'http://127.0.0.1:5199'

function creds() {
  const env = fs.readFileSync('D:/software/codex/codex_work/.secrets/local.env', 'utf8')
  const seg = env.split('#项目网站信息').pop()
  return {
    acc: /账号：\s*(\S+)/.exec(seg)[1],
    pw: /密码：\s*(\S+)/.exec(seg)[1],
  }
}

const PAGES = [
  { url: '/workbench', name: 'home' },
  { url: '/finance', name: 'finance' },
  { url: '/life', name: 'life' },
  { url: '/contacts', name: 'contacts' },
  { url: '/novel', name: 'novel' },
]

;(async () => {
  const { acc, pw } = creds()
  const b = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await b.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
    deviceScaleFactor: 2,
    userAgent: 'Mozilla/5.0 (Linux; Android 12; XuanHuangApp) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36 XuanHuangApp/1.0',
  })
  const p = await ctx.newPage()
  p.on('pageerror', (e) => console.log('[pageerror]', e.message))
  p.on('console', (m) => { if (m.type() === 'error') console.log('[err]', m.text().slice(0, 160)) })

  await p.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(900)
  await p.fill('input[type="text"], input[placeholder*="邮箱"], input[placeholder*="账号"]', acc).catch(() => {})
  await p.fill('input[type="password"]', pw)
  await p.keyboard.press('Enter')
  await p.waitForTimeout(3200)
  console.log('登录后:', p.url(), '| is-mobile:', await p.evaluate(() => document.querySelector('#app')?.className))

  for (const it of PAGES) {
    await p.goto(`${BASE}${it.url}`, { waitUntil: 'networkidle', timeout: 60000 })
    await p.waitForTimeout(1800)
    if (process.env.THEME) {
      await p.evaluate((t) => document.documentElement.setAttribute('data-theme', t), process.env.THEME)
      await p.waitForTimeout(700)
    }
    await p.screenshot({ path: `${OUT}/glass-${it.name}${process.env.THEME ? '-' + process.env.THEME : ''}.png` })
    // 滚到中部再截一张：看平铺光斑是否让中下部也有彩晕
    await p.evaluate(() => window.scrollTo({ top: 760, behavior: 'instant' }))
    await p.waitForTimeout(600)
    await p.screenshot({ path: `${OUT}/glass-${it.name}${process.env.THEME ? '-' + process.env.THEME : ''}-mid.png` })
    await p.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }))
    const probe = await p.evaluate(() => {
      const pick = ['.abb-cell', '.abb-hero', '.glass-card', '.fin-kpi', '.mt-tabbar', '.life-col']
      const out = {}
      for (const s of pick) {
        const el = document.querySelector(s)
        if (!el) continue
        const cs = getComputedStyle(el)
        out[s] = {
          bg: cs.backgroundColor,
          img: (cs.backgroundImage || '').slice(0, 60),
          blur: cs.backdropFilter,
          border: cs.borderTopColor,
          shadow: (cs.boxShadow || '').slice(0, 70),
          color: cs.color,
        }
      }
      const app = document.querySelector('#app')
      out['#app'] = app ? { bg: (getComputedStyle(app).backgroundImage || '').slice(0, 90) } : null
      const tb = document.querySelector('.mt-tab')
      out['.mt-tab'] = tb ? { color: getComputedStyle(tb).color } : null
      return out
    })
    console.log(`--- ${it.name} ---`)
    console.log(JSON.stringify(probe, null, 1))
  }

  // 底栏近景
  const tb = await p.$('.mt-tabbar')
  if (tb) await tb.screenshot({ path: `${OUT}/glass-tabbar.png` })

  await b.close()
})()
