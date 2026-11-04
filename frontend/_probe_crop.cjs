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
;(async () => {
  const { acc, pw } = creds()
  const b = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 3,
    userAgent: 'Mozilla/5.0 (Linux; Android 12; XuanHuangApp) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36 XuanHuangApp/1.0' })
  const p = await ctx.newPage()
  await p.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.fill('input[type="text"], input[placeholder*="邮箱"], input[placeholder*="账号"]', acc).catch(()=>{})
  await p.fill('input[type="password"]', pw)
  await p.keyboard.press('Enter')
  await p.waitForTimeout(3200)
  await p.goto(`${BASE}/finance`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(1500)
  await p.evaluate(() => {
    const el = document.querySelector('.fin-head-right button') || [...document.querySelectorAll('button')].find(b => /记一笔/.test(b.textContent||''))
    if (el) el.click()
  })
  await p.waitForTimeout(1200)
  const box = await p.locator('.fin-form--drawer').boundingBox()
  await p.screenshot({ path: `${OUT}/crop-drawer.png`, clip: { x: box.x, y: box.y, width: box.width, height: Math.min(box.height, 300) } })
  console.log('saved', JSON.stringify(box))
  await b.close()
})()
