/** 诊断 2：公款 hero 的青色描边来源 + 输入框药丸的真实底 */
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
  await p.evaluate(() => {
    const btns = [...document.querySelectorAll('button')]
    const hit = btns.find((b) => (b.textContent || '').trim() === '公款')
    if (hit) hit.click()
  })
  await p.waitForTimeout(1200)

  const hero = await p.evaluate(() => {
    const el = document.querySelector('.fin-pool-hero')
    if (!el) return 'no hero'
    const cs = getComputedStyle(el)
    const par = el.parentElement
    const pcs = getComputedStyle(par)
    const val = el.querySelector('.fin-pool-hero-val')
    return {
      heroCls: el.className,
      border: cs.border,
      bs: cs.boxShadow.slice(0, 260),
      bg: cs.backgroundColor,
      parentCls: par.className,
      parentBorder: pcs.borderTopColor + ' | ' + pcs.borderTopWidth,
      parentBs: pcs.boxShadow.slice(0, 200),
      valColor: val ? getComputedStyle(val).color : null,
      // 找 ::after / ::before 的样式（同元素伪类取不到，只能看父级是否带伪元素）
      parentAfter: pcs.content
    }
  })
  console.log('HERO', JSON.stringify(hero, null, 1))

  await p.evaluate(() => {
    const el = document.querySelector('.fin-head-right button') || [...document.querySelectorAll('button')].find(b => /记一笔/.test(b.textContent||''))
    if (el) el.click()
  })
  await p.waitForTimeout(1000)
  const wrap = await p.evaluate(() => {
    const d = document.querySelector('.fin-form--drawer')
    const out = []
    d.querySelectorAll('.el-input__wrapper, .fin-amount, .fin-date').forEach((w) => {
      const cs = getComputedStyle(w)
      out.push({ cls: w.className, bg: cs.backgroundColor, img: cs.backgroundImage.slice(0, 100),
        bs: cs.boxShadow.slice(0, 140), op: cs.opacity, filter: cs.filter, blend: cs.mixBlendMode,
        border: cs.borderTopColor })
    })
    return out.slice(0, 4)
  })
  console.log('WRAP', JSON.stringify(wrap, null, 1))
  await b.close()
})()
