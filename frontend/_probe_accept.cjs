/** 线上验收：记账 tab / 抽屉 / 体重 / 小说 / 通讯录 */
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')
const OUT = path.resolve(__dirname, '../artifacts/_probe')
const BASE = process.env.PROBE_BASE || 'https://yexingchen.cn'
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

  await p.goto(`${BASE}/finance`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(1800)
  await p.screenshot({ path: `${OUT}/acc-fin-overview.png` })

  // 存款 tab
  const clickTab = async (label) => {
    const ok = await p.evaluate((t) => {
      const btns = [...document.querySelectorAll('.fin-tabs button, .fin-tabs [role="tab"], button')]
      const hit = btns.find((b) => (b.textContent || '').trim() === t)
      if (hit) { hit.click(); return true }
      return false
    }, label)
    await p.waitForTimeout(1400)
    return ok
  }
  console.log('存款', await clickTab('存款'))
  await p.screenshot({ path: `${OUT}/acc-fin-savings.png` })
  console.log('公款', await clickTab('公款'))
  await p.screenshot({ path: `${OUT}/acc-fin-public.png` })

  // 记一笔抽屉
  await p.evaluate(() => {
    const el = document.querySelector('.fin-head-right button') || [...document.querySelectorAll('button')].find(b => b.getAttribute('aria-label') === '记一笔')
    if (el) el.click()
  })
  await p.waitForTimeout(1200)
  await p.screenshot({ path: `${OUT}/acc-fin-drawer.png` })
  await p.keyboard.press('Escape').catch(()=>{})

  for (const [url, name] of [['/life','life'],['/novel','novel'],['/contacts','contacts'],['/workbench','home']]) {
    await p.goto(`${BASE}${url}`, { waitUntil: 'networkidle', timeout: 60000 })
    await p.waitForTimeout(1600)
    await p.screenshot({ path: `${OUT}/acc-${name}.png` })
  }
  // 通讯录：点开第一张卡的详情，确认折叠/展开与操作按钮
  await p.goto(`${BASE}/contacts`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(1400)
  await p.evaluate(() => document.querySelector('.ct-name-row')?.click())
  await p.waitForTimeout(600)
  await p.screenshot({ path: `${OUT}/acc-contacts-open.png` })
  console.log('done')
  await b.close()
})()
