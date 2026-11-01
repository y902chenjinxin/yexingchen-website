/** 路由切换耗时（v2.46.313）：点侧栏菜单 → 目标页主内容出现 */
const { chromium } = require('playwright')
const fs = require('fs')
const BASE = 'https://yexingchen.cn'
const env = fs.readFileSync('D:/software/codex/codex_work/.secrets/local.env', 'utf8').split('#项目网站信息').pop()
const ACC = /账号：\s*(\S+)/.exec(env)[1], PW = /密码：\s*(\S+)/.exec(env)[1]
const TARGETS = [
  { label: '记账', sel: '.fin-page, .fin-root, .fin-pools' },
  { label: '音乐', sel: '.mu-page, .music-page, audio, .mu-list' },
  { label: '小说', sel: '.novel-shelf, .manage-pane, .el-table' },
  { label: '工作台', sel: '.bento-hero' },
]
;(async () => {
  const b = await chromium.launch()
  const p = await (await b.newContext({ viewport: { width: 1280, height: 820 } })).newPage()
  await p.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForTimeout(800)
  await p.fill('input[type="text"], input[placeholder*="账号"]', ACC).catch(() => {})
  await p.fill('input[type="password"]', PW)
  await p.keyboard.press('Enter')
  await p.waitForTimeout(3500)
  // 预热一轮（让懒加载 chunk 进缓存，模拟日常使用）
  for (const t of TARGETS) {
    await p.evaluate((lb) => {
      const el = Array.from(document.querySelectorAll('.dsb a, .dsb button, .dsb li')).find((x) => (x.textContent || '').trim().startsWith(lb))
      el && el.click()
    }, t.label)
    await p.waitForTimeout(1200)
  }
  console.log('=== 第二次切换（chunk 已缓存）===')
  for (const round of [1, 2]) {
    for (const t of TARGETS) {
      const t0 = Date.now()
      const ok = await p.evaluate((lb) => {
        const el = Array.from(document.querySelectorAll('.dsb a, .dsb button, .dsb li')).find((x) => (x.textContent || '').trim().startsWith(lb))
        if (!el) return false
        el.click()
        return true
      }, t.label)
      if (!ok) { console.log(`  ${t.label}: 入口没找到`); continue }
      const ms = await p.waitForSelector(t.sel, { timeout: 8000 }).then(() => Date.now() - t0).catch(() => -1)
      console.log(`  第${round}轮 ${t.label}: ${ms < 0 ? '超时' : ms + 'ms'}`)
      await p.waitForTimeout(700)
    }
  }
  await b.close()
})()
