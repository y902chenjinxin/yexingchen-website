const { chromium } = require('playwright')
const fs = require('fs')
const BASE = 'https://yexingchen.cn'
function creds() {
  const env = fs.readFileSync('D:/software/codex/codex_work/.secrets/local.env', 'utf8')
  const seg = env.split('#项目网站信息').pop()
  return { acc: /账号：\s*(\S+)/.exec(seg)[1], pw: /密码：\s*(\S+)/.exec(seg)[1] }
}
;(async () => {
  const { acc, pw } = creds()
  const b = await chromium.launch()
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, serviceWorkers: process.env.NO_SW ? 'block' : 'allow' })
  const p = await ctx.newPage()
  p.on('pageerror', (e) => console.log('[pageerror]', e.message.slice(0, 160)))

  await p.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(1000)
  await p.fill('input[type="text"], input[placeholder*="邮箱"], input[placeholder*="账号"]', acc).catch(() => {})
  await p.fill('input[type="password"]', pw)
  await p.keyboard.press('Enter')
  await p.waitForTimeout(3000)

  const t0 = Date.now()
  await p.goto(`${BASE}/music`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  // 等列表出现
  let appeared = 0
  for (let i = 0; i < 40; i++) {
    await p.waitForTimeout(250)
    const n = await p.evaluate(() => document.querySelectorAll('.mu-item, .music-item, .el-table__row, [class*="mu-"] li').length)
    if (n > 0) { appeared = n; break }
  }
  console.log(`列表出现 ${appeared} 项，耗时 ${((Date.now() - t0) / 1000).toFixed(1)}s`)
  await p.waitForTimeout(4000)   // 让后台请求跑一会儿
  await p.screenshot({ path: '../artifacts/_probe/live-music.png' })

  const res = await p.evaluate(() => performance.getEntriesByType('resource').map((e) => ({
    n: e.name.replace(location.origin, '').split('?')[0],
    dur: Math.round(e.duration),
    kb: Math.round((e.transferSize || 0) / 1024),
    init: e.initiatorType,
  })).filter((x) => x.dur > 80 || x.kb > 50))

  const api = res.filter((x) => x.n.startsWith('/api/'))
  const assets = res.filter((x) => !x.n.startsWith('/api/'))
  console.log('\n--- API 请求 ---')
  api.sort((a, b) => b.dur - a.dur).slice(0, 15).forEach((x) => console.log(`  ${x.dur}ms  ${x.kb}KB  ${x.n}`))
  console.log('\n--- 静态资源 ---')
  assets.sort((a, b) => b.dur - a.dur).slice(0, 10).forEach((x) => console.log(`  ${x.dur}ms  ${x.kb}KB  ${x.n}`))

  const total = await p.evaluate(() => performance.getEntriesByType('resource').reduce((s, e) => s + (e.transferSize || 0), 0))
  console.log(`\n总传输: ${Math.round(total / 1024)}KB`)
  await b.close()
})()
