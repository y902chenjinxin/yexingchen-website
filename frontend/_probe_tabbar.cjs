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
  const b = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2,
    userAgent: 'Mozilla/5.0 (Linux; Android 12; XuanHuangApp) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36 XuanHuangApp/1.0' })
  const p = await ctx.newPage()
  await p.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.fill('input[type="text"], input[placeholder*="邮箱"], input[placeholder*="账号"]', acc).catch(()=>{})
  await p.fill('input[type="password"]', pw)
  await p.keyboard.press('Enter')
  await p.waitForTimeout(3200)
  await p.goto(`${BASE}/workbench`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(1500)
  const info = await p.evaluate(() => {
    const tb = document.querySelector('.mt-tabbar')
    const np = document.querySelector('.npbar')
    const app = document.querySelector('#app')
    const r = (el) => el ? { top: Math.round(el.getBoundingClientRect().top), h: Math.round(el.getBoundingClientRect().height), bottom: Math.round(el.getBoundingClientRect().bottom) } : null
    return {
      vh: window.innerHeight,
      tabbar: r(tb),
      npbar: r(np),
      appPadBottom: app ? getComputedStyle(app).paddingBottom : null,
      hasNpbar: document.body.classList.contains('has-npbar'),
      npbarBg: np ? getComputedStyle(np).backgroundColor : null,
    }
  })
  console.log(JSON.stringify(info, null, 1))
  await b.close()
})()
