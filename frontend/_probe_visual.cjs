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
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 })
  const p = await ctx.newPage()
  await p.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(1000)
  await p.fill('input[type="text"], input[placeholder*="邮箱"], input[placeholder*="账号"]', acc).catch(() => {})
  await p.fill('input[type="password"]', pw)
  await p.keyboard.press('Enter')
  await p.waitForTimeout(3000)

  await p.goto(`${BASE}/novel`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(2500)
  await p.screenshot({ path: '../artifacts/_probe/shelf-new.png' })
  console.log('书架已截图')

  // 进书 → 唤 chrome
  await p.evaluate(() => {
    const t = Array.from(document.querySelectorAll('.ns-title')).find((x) => /诸神愚戏/.test(x.textContent || ''))
    t && t.click()
  })
  for (let i = 0; i < 25; i++) {
    await p.waitForTimeout(600)
    if (await p.evaluate(() => document.querySelectorAll('.nrd-p').length)) break
  }
  await p.waitForTimeout(800)
  await p.mouse.click(195, 420)
  await p.waitForTimeout(700)
  await p.screenshot({ path: '../artifacts/_probe/footer-new.png' })
  console.log('底栏已截图')

  await p.evaluate(() => {
    Array.from(document.querySelectorAll('.nrd-foot-tools button')).find((x) => /设置/.test(x.textContent || ''))?.click()
  })
  await p.waitForTimeout(800)
  await p.screenshot({ path: '../artifacts/_probe/sheet-new.png' })
  console.log('设置抽屉已截图')
  const hasReset = await p.evaluate(() => /恢复默认/.test(document.querySelector('.nrd-set-foot')?.textContent || ''))
  console.log('抽屉底部还有「恢复默认」吗:', hasReset)
  await b.close()
})()
