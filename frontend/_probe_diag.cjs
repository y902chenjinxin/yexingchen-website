/** 一次性诊断：底栏/输入框的 computed 值到底被谁压了 */
const { chromium } = require('playwright')
const fs = require('fs')
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
  await p.waitForTimeout(1500)

  const tab = await p.evaluate(() => {
    const el = document.querySelector('.mt-tabbar')
    if (!el) return 'no .mt-tabbar'
    const cs = getComputedStyle(el)
    return { bg: cs.backgroundColor, bgImg: cs.backgroundImage.slice(0, 140), bf: cs.backdropFilter, op: cs.opacity, z: cs.zIndex }
  })
  console.log('TABBAR', JSON.stringify(tab, null, 1))

  const pad = await p.evaluate(() => {
    const app = document.querySelector('#app')
    return { hasNp: document.body.classList.contains('has-npbar'), pad: getComputedStyle(app).paddingBottom, npbar: !!document.querySelector('.npbar') }
  })
  console.log('PAD', JSON.stringify(pad))

  // 打开抽屉
  await p.evaluate(() => {
    const el = document.querySelector('.fin-head-right button') || [...document.querySelectorAll('button')].find(b => /记一笔/.test(b.textContent||''))
    if (el) el.click()
  })
  await p.waitForTimeout(1200)
  const inp = await p.evaluate(() => {
    const drawer = document.querySelector('.fin-form--drawer')
    if (!drawer) return 'no drawer'
    const pick = (sel) => {
      const el = drawer.querySelector(sel)
      if (!el) return null
      const cs = getComputedStyle(el)
      return { cls: el.className, color: cs.color, fill: cs.webkitTextFillColor, op: cs.opacity,
        val: (el.value || '').slice(0, 20), ph: el.placeholder || '',
        bg: getComputedStyle(el.parentElement).backgroundColor }
    }
    return {
      drawerBg: getComputedStyle(drawer).backgroundColor,
      drawerImg: getComputedStyle(drawer).backgroundImage.slice(0, 120),
      amount: pick('input[type="text"], .fin-amount input, input:not([type])'),
      date: pick('input[placeholder*="日期"], .el-date-editor input, input[readonly]'),
      all: [...drawer.querySelectorAll('input')].map(i => ({ t: i.type, cls: i.className, val: i.value, ph: i.placeholder,
        color: getComputedStyle(i).color, fill: getComputedStyle(i).webkitTextFillColor })).slice(0, 6)
    }
  })
  console.log('INPUT', JSON.stringify(inp, null, 1))
  await b.close()
})()
