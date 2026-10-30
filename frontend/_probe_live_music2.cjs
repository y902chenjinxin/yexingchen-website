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
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })
  const p = await ctx.newPage()
  p.on('pageerror', (e) => console.log('[pageerror]', e.message.slice(0, 160)))
  await p.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(1000)
  await p.fill('input[type="text"], input[placeholder*="邮箱"], input[placeholder*="账号"]', acc).catch(() => {})
  await p.fill('input[type="password"]', pw)
  await p.keyboard.press('Enter')
  await p.waitForTimeout(3500)

  for (const round of [1, 2]) {
    await p.goto(`${BASE}/workbench`, { waitUntil: 'networkidle', timeout: 60000 })
    await p.waitForTimeout(4200)
    const warmed = await p.evaluate(() => performance.getEntriesByType('resource').some((e) => /MusicView-.*\.js/.test(e.name)))
    console.log(`第 ${round} 次：预取${warmed ? '已就绪 ✅' : '未完成'}`)
    const t0 = Date.now()
    // 点侧栏 / 菜单里的「音乐」
    const ok = await p.evaluate(() => {
      const el = Array.from(document.querySelectorAll('a, .nav-item, li, button')).find((x) => (x.textContent || '').trim() === '音乐')
      if (el) { el.click(); return true }
      return false
    })
    if (!ok) { console.log('没找到音乐入口'); break }
    let ms = -1
    for (let i = 0; i < 60; i++) {
      await p.waitForTimeout(100)
      const n = await p.evaluate(() => document.querySelectorAll('.el-table__row').length)
      if (n > 0) { ms = Date.now() - t0; break }
    }
    console.log(`第 ${round} 次站内切换 → 列表可见 ${ms}ms，行数 ${await p.evaluate(() => document.querySelectorAll('.el-table__row').length)}`)

    const detail = await p.evaluate(() => performance.getEntriesByType('resource')
      .filter((e) => e.startTime > performance.timing ? true : true)
      .filter((e) => /\/api\/music|MusicView|element-plus/.test(e.name))
      .map((e) => `${Math.round(e.duration)}ms ${Math.round((e.transferSize || 0) / 1024)}KB ${e.name.split('/').pop().split('?')[0]}`))
    console.log('   ', detail.join(' | ') || '(无)')
  }
  await b.close()
})()
