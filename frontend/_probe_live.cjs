/**
 * 现网阅读器实测：登录 → 小说 → 打开一本书 → 点页面 → 点目录/设置 → 量几何
 * 目的：复现夜星反馈的「底部白块」「抽屉展示不全」
 */
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const OUT = path.resolve(__dirname, '../artifacts/_probe')
const BASE = process.env.PROBE_BASE || 'https://yexingchen.cn'

function creds() {
  const env = fs.readFileSync('D:/software/codex/codex_work/.secrets/local.env', 'utf8')
  const seg = env.split('#项目网站信息').pop()
  const acc = /账号：\s*(\S+)/.exec(seg)[1]
  const pw = /密码：\s*(\S+)/.exec(seg)[1]
  return { acc, pw }
}

const geo = () => {
  const box = (sel) => {
    const el = document.querySelector(sel)
    if (!el) return null
    const r = el.getBoundingClientRect()
    return { top: Math.round(r.top), bottom: Math.round(r.bottom), h: Math.round(r.height) }
  }
  const nrd = document.querySelector('.nrd')
  const nr = nrd ? nrd.getBoundingClientRect() : null
  return {
    innerH: window.innerHeight,
    innerW: window.innerWidth,
    vvH: window.visualViewport ? Math.round(window.visualViewport.height) : null,
    vvTop: window.visualViewport ? Math.round(window.visualViewport.offsetTop) : null,
    docH: document.documentElement.scrollHeight,
    bodyBg: getComputedStyle(document.body).backgroundColor,
    nrd: nr ? { top: Math.round(nr.top), bottom: Math.round(nr.bottom), h: Math.round(nr.height), inlineH: nrd.style.height || '(none)', padB: getComputedStyle(nrd).paddingBottom } : null,
    buiVar: nrd ? getComputedStyle(nrd).getPropertyValue('--bui-bottom').trim() : null,
    foot: box('.nrd-foot'),
    footTools: box('.nrd-foot-tools'),
    sheetToc: box('.nrd-sheet-toc'),
    sheetSet: box('.nrd-sheet-set'),
    // 容器底部到可视区底部的空白（>0 就是白块高度）
    gapBelowNrd: nr ? Math.round(window.innerHeight - nr.bottom) : null,
    isChrome: nrd ? nrd.classList.contains('is-chrome') : null,
  }
}

;(async () => {
  const { acc, pw } = creds()
  const b = await chromium.launch()
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 })
  const p = await ctx.newPage()
  p.on('pageerror', (e) => console.log('[pageerror]', e.message))
  p.on('console', (m) => { if (m.type() === 'error') console.log('[console.error]', m.text().slice(0, 200)) })

  console.log('1) 登录…')
  await p.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(1200)
  await p.fill('input[type="text"], input[placeholder*="邮箱"], input[placeholder*="账号"]', acc).catch(() => {})
  await p.fill('input[type="password"]', pw)
  await p.keyboard.press('Enter')
  await p.waitForTimeout(3500)
  console.log('   登录后 URL:', p.url())

  console.log('2) 去小说列表…')
  await p.goto(`${BASE}/novel`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(2000)
  await p.screenshot({ path: `${OUT}/live-novel-list.png` })

  console.log('3) 打开第一本书…')
  const opened = await p.evaluate(() => {
    const t = Array.from(document.querySelectorAll('.ns-title, .ns-item, .novel-card, .card')).find((x) => /诸神愚戏/.test(x.textContent || ''))
    if (t) { t.click(); return 'by-title:' + t.className }
    const btn = Array.from(document.querySelectorAll('button')).find((x) => /阅读/.test(x.textContent || ''))
    if (btn) { btn.click(); return 'by-button' }
    return 'not-found'
  })
  console.log('   打开方式:', opened)
  await p.waitForTimeout(6000)
  await p.screenshot({ path: `${OUT}/live-reader-enter.png` })
  console.log('   进入后几何:', JSON.stringify(await p.evaluate(geo), null, 2))
  await p.screenshot({ path: `${OUT}/live-reader-enter.png` })

  console.log('4) 点页面中部唤菜单…')
  await p.mouse.click(195, 420)
  await p.waitForTimeout(500)
  console.log('   唤菜单后:', JSON.stringify(await p.evaluate(geo), null, 2))
  await p.screenshot({ path: `${OUT}/live-reader-chrome.png` })

  console.log('5) 点「目录」…')
  const clickedToc = await p.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('.nrd-foot-tools button')).find((x) => /目录/.test(x.textContent || ''))
    if (!btn) return { ok: false, tools: Array.from(document.querySelectorAll('.nrd-foot-tools button')).map((x) => x.textContent.trim()) }
    btn.click()
    return { ok: true }
  })
  console.log('   ', JSON.stringify(clickedToc))
  await p.waitForTimeout(700)
  console.log('   目录打开后:', JSON.stringify(await p.evaluate(geo), null, 2))
  await p.screenshot({ path: `${OUT}/live-reader-toc.png` })

  console.log('6) 关目录 → 开设置…')
  await p.evaluate(() => { const x = Array.from(document.querySelectorAll('.nrd-sheet-toc .nrd-ic')).find((e) => e.textContent.includes('×')); x && x.click() })
  await p.waitForTimeout(400)
  await p.mouse.click(195, 420)
  await p.waitForTimeout(400)
  await p.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('.nrd-foot-tools button')).find((x) => /设置/.test(x.textContent || ''))
    btn && btn.click()
  })
  await p.waitForTimeout(700)
  console.log('   设置打开后:', JSON.stringify(await p.evaluate(geo), null, 2))
  await p.screenshot({ path: `${OUT}/live-reader-set.png` })

  await b.close()
  console.log('DONE')
})()
