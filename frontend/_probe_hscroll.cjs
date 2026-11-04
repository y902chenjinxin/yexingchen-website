/* 横向溢出诊断（v2.46.402）
 * 夜星：「记账弹窗为什么能左右滑」—— 要区分是**整页**能滑还是**抽屉内部**能滑。
 * 同时打印关键控件的 computed 背景，确认「灰」是否已经消掉。 */
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
  const ctx = await b.newContext({
    viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2,
    userAgent: 'Mozilla/5.0 (Linux; Android 12; XuanHuangApp) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36 XuanHuangApp/1.0',
  })
  const p = await ctx.newPage()
  await p.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.fill('input[type="text"], input[placeholder*="邮箱"], input[placeholder*="账号"]', acc).catch(() => {})
  await p.fill('input[type="password"]', pw)
  await p.keyboard.press('Enter')
  await p.waitForTimeout(3200)

  await p.goto(`${BASE}/finance`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(1600)

  const pageOverflow = await p.evaluate(() => {
    const se = document.scrollingElement
    const wide = []
    document.querySelectorAll('*').forEach((el) => {
      const r = el.getBoundingClientRect()
      if (r.width > 0 && r.right > window.innerWidth + 1) {
        wide.push({ cls: String(el.className).slice(0, 48), right: Math.round(r.right), w: Math.round(r.width) })
      }
    })
    return {
      inner: window.innerWidth,
      scrollW: se.scrollWidth,
      bodyScrollW: document.body.scrollWidth,
      wide: wide.slice(0, 8),
    }
  })
  console.log('== 页面 ==', JSON.stringify(pageOverflow, null, 1))

  // 打开抽屉
  await p.evaluate(() => {
    const el = document.querySelector('.fin-head-right button') || [...document.querySelectorAll('button')].find((b) => /记一笔/.test(b.textContent || ''))
    if (el) el.click()
  })
  await p.waitForTimeout(1200)

  const drawerOverflow = await p.evaluate(() => {
    const pick = (sel) => {
      const el = document.querySelector(sel)
      if (!el) return null
      const cs = getComputedStyle(el)
      return { sel, cw: el.clientWidth, sw: el.scrollWidth, ox: cs.overflowX, oy: cs.overflowY }
    }
    const wide = []
    document.querySelectorAll('.fin-form--drawer *').forEach((el) => {
      const r = el.getBoundingClientRect()
      const host = document.querySelector('.fin-form--drawer').getBoundingClientRect()
      if (r.width > 0 && r.right > host.right + 1) {
        wide.push({ cls: String(el.className).slice(0, 44), right: Math.round(r.right), w: Math.round(r.width) })
      }
    })
    return {
      drawer: pick('.fin-form--drawer'),
      body: pick('.fin-form--drawer .fin-form-body'),
      wide: wide.slice(0, 8),
    }
  })
  console.log('== 抽屉 ==', JSON.stringify(drawerOverflow, null, 1))

  const chips = await p.evaluate(() => {
    const q = (s) => {
      const el = document.querySelector(s)
      if (!el) return null
      const cs = getComputedStyle(el)
      return { s, bg: cs.backgroundColor, bd: cs.borderTopColor, bf: cs.backdropFilter.slice(0, 30) }
    }
    return {
      tag: q('.fin-mtag'),
      tagOn: q('.fin-mtag.on'),
      fund: q('.fin-form--drawer .fin-fund'),
      cat: q('.fin-form--drawer .fin-cat'),
      tab: q('.fin-form--drawer .fin-tab'),
      input: q('.fin-form--drawer .el-input__wrapper'),
      pool: q('.fin-pool'),
      cell: null,
    }
  })
  console.log('== 控件 ==', JSON.stringify(chips, null, 1))

  await p.goto(`${BASE}/workbench`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(1400)
  const home = await p.evaluate(() => {
    const el = document.querySelector('.abb-cell')
    const cs = el ? getComputedStyle(el) : null
    return {
      cellBg: cs ? cs.backgroundColor : null,
      cellImg: cs ? cs.backgroundImage.slice(0, 80) : null,
      cellBf: cs ? cs.backdropFilter.slice(0, 30) : null,
      bodyBg: getComputedStyle(document.body).backgroundColor,
      htmlBg: getComputedStyle(document.documentElement).backgroundColor,
    }
  })
  console.log('== 首页 ==', JSON.stringify(home, null, 1))

  await b.close()
})()
