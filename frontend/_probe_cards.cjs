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
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5 })
  const p = await ctx.newPage()
  await p.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(1000)
  await p.fill('input[type="text"], input[placeholder*="邮箱"], input[placeholder*="账号"]', acc).catch(() => {})
  await p.fill('input[type="password"]', pw)
  await p.keyboard.press('Enter')
  await p.waitForTimeout(4000)
  await p.goto(`${BASE}/workbench`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(3500)

  const state = await p.evaluate(() => {
    const kn = document.querySelector('.kn')
    const qz = document.querySelector('.qz')
    return {
      知识卡展开: !!kn?.querySelector('.kn-body'),
      知识卡提示: kn?.querySelector('.kn-hint')?.textContent.trim().slice(0, 30) || null,
      答题卡展开: !!qz?.querySelector('.qz-opts'),
      答题卡提示: qz?.querySelector('.qz-hint')?.textContent.trim().slice(0, 30) || null,
      知识卡高: kn ? Math.round(kn.getBoundingClientRect().height) : null,
      答题卡高: qz ? Math.round(qz.getBoundingClientRect().height) : null,
    }
  })
  console.log('默认状态:', JSON.stringify(state, null, 0))
  await p.evaluate(() => document.querySelector('.kn')?.scrollIntoView({ block: 'center' }))
  await p.waitForTimeout(700)
  await p.screenshot({ path: '../artifacts/_probe/cards-collapsed.png' })

  // 点开知识卡 + 答题卡
  await p.evaluate(() => {
    const knBtn = document.querySelector('.kn .fbtn'); knBtn && knBtn.click()
    const qzBtn = document.querySelector('.qz .fbtn'); qzBtn && qzBtn.click()
  })
  await p.waitForTimeout(900)
  const after = await p.evaluate(() => ({
    知识卡展开: !!document.querySelector('.kn .kn-body'),
    答题卡展开: !!document.querySelector('.qz .qz-opts'),
    知识卡高: Math.round(document.querySelector('.kn').getBoundingClientRect().height),
    答题卡高: Math.round(document.querySelector('.qz').getBoundingClientRect().height),
  }))
  console.log('点开后:', JSON.stringify(after))
  await p.evaluate(() => document.querySelector('.kn')?.scrollIntoView({ block: 'start' }))
  await p.waitForTimeout(500)
  await p.screenshot({ path: '../artifacts/_probe/cards-expanded.png' })
  await b.close()
})()
