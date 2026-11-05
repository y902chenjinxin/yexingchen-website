const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')
const OUT = path.resolve(__dirname, '../artifacts/_probe')
const BASE = 'https://yexingchen.cn'
function creds() {
  const env = fs.readFileSync('D:/software/codex/codex_work/.secrets/local.env', 'utf8')
  const seg = env.split('#项目网站信息').pop()
  return { acc: /账号：\s*(\S+)/.exec(seg)[1], pw: /密码：\s*(\S+)/.exec(seg)[1] }
}
async function shot(page, theme, url, name, clipSel) {
  await page.goto(`${BASE}${url}`, { waitUntil: 'networkidle', timeout: 60000 })
  await page.evaluate((t) => { document.documentElement.dataset.theme = t }, theme)
  await page.waitForTimeout(1400)
  if (clipSel) {
    const b = await page.locator(clipSel).boundingBox()
    if (b) {
      await page.screenshot({ path: `${OUT}/${theme}-${name}.png`,
        clip: { x: 0, y: Math.max(0, b.y - 30), width: 390, height: Math.min(b.height + 60, 520) } })
      return
    }
  }
  await page.screenshot({ path: `${OUT}/${theme}-${name}.png` })
}
;(async () => {
  const { acc, pw } = creds()
  const b = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2,
    userAgent: 'Mozilla/5.0 (Linux; Android 12; XuanHuangApp) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36 XuanHuangApp/1.0' })
  const p = await ctx.newPage()
  await p.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.fill('input[type="text"], input[placeholder*="邮箱"], input[placeholder*="账号"]', acc).catch(()=>{})
  await p.fill('input[type="password"]', pw)
  await p.keyboard.press('Enter')
  await p.waitForTimeout(3200)
  const diag = {}
  for (const theme of ['day', 'night']) {
    await shot(p, theme, '/workbench', 'home', '.abb-grid')
    await shot(p, theme, '/finance', 'fin', null)
    diag[theme] = await p.evaluate(() => {
      const cell = document.querySelector('.abb-cell')
      const mt = document.querySelector('.fin-mtag:not(.on)')
      const g = (el) => el ? { bg: getComputedStyle(el).backgroundColor, c: getComputedStyle(el).color } : null
      return { theme: document.documentElement.dataset.theme, cell: g(cell), mtag: g(mt) }
    })
  }
  console.log(JSON.stringify(diag, null, 1))
  await b.close()
})()
