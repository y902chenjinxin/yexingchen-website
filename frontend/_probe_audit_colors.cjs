/**
 * 配色巡检 v2（v2.46.313）：不猜类名，直接扫整页
 *   node _probe_audit_colors.cjs
 * 输出：每页「浅底大面积元素」（深色主题下就是白块）+ 文字色 Top5
 */
const { chromium } = require('playwright')
const fs = require('fs')
const BASE = 'https://yexingchen.cn'
const OUT = 'artifacts/_probe/audit'
const env = fs.readFileSync('D:/software/codex/codex_work/.secrets/local.env', 'utf8').split('#项目网站信息').pop()
const ACC = /账号：\s*(\S+)/.exec(env)[1]
const PW = /密码：\s*(\S+)/.exec(env)[1]

const PAGES = [
  '/workbench', '/finance', '/relations',
  '/tool/danmu', '/tool/spin', '/tool/compress', '/tool/pdf', '/tool/watermark',
  '/tool/games', '/life',
]

;(async () => {
  const b = await chromium.launch()
  const ctx = await b.newContext({ viewport: { width: 1280, height: 820 }, deviceScaleFactor: 1 })
  const p = await ctx.newPage()

  await p.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForTimeout(800)
  await p.fill('input[type="text"], input[placeholder*="账号"]', ACC).catch(() => {})
  await p.fill('input[type="password"]', PW)
  await p.keyboard.press('Enter')
  await p.waitForTimeout(3500)

  for (const path of PAGES) {
    await p.goto(`${BASE}${path}`, { waitUntil: 'domcontentloaded', timeout: 60000 })
    await p.waitForTimeout(2300)
    const res = await p.evaluate(() => {
      const parse = (s) => {
        const m = String(s).match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?/)
        if (!m) return null
        return { r: +m[1], g: +m[2], b: +m[3], a: m[4] === undefined ? 1 : +m[4] }
      }
      const lights = []
      const seen = new Set()
      document.querySelectorAll('body *').forEach((el) => {
        const c = getComputedStyle(el)
        if (c.display === 'none' || c.visibility === 'hidden' || +c.opacity < 0.5) return
        const bg = parse(c.backgroundColor)
        if (!bg || bg.a < 0.5) return
        const lum = (0.299 * bg.r + 0.587 * bg.g + 0.114 * bg.b) / 255
        if (lum < 0.72) return
        const r = el.getBoundingClientRect()
        const area = r.width * r.height
        if (area < 4000) return
        const cls = (el.className || '').toString().split(' ').filter(Boolean).slice(0, 2).join('.')
        const key = cls + Math.round(lum * 100)
        if (seen.has(key)) return
        seen.add(key)
        lights.push({ sel: `${el.tagName.toLowerCase()}.${cls}`, lum: +lum.toFixed(2), area: Math.round(area), color: c.backgroundColor })
      })
      const colors = {}
      document.querySelectorAll('body *').forEach((el) => {
        if (!el.textContent || !el.textContent.trim()) return
        const c = getComputedStyle(el).color
        if (c) colors[c] = (colors[c] || 0) + 1
      })
      const top = Object.entries(colors).sort((a, b) => b[1] - a[1]).slice(0, 6)
      return { lights: lights.slice(0, 8), top }
    })
    const name = path.replace(/\//g, '_').replace(/^_/, '')
    console.log(`\n[${path}]`)
    if (res.lights.length) {
      res.lights.forEach((l) => console.log(`   ⚠ 浅底 ${l.sel} lum=${l.lum} area=${l.area} ${l.color}`))
    } else console.log('   ✅ 无大面积浅底')
    console.log('   文字色 Top:', res.top.map(([c, n]) => `${c}(${n})`).join(' '))
    await p.screenshot({ path: `${OUT}/${name}.png` })
  }
  await b.close()
})()
