/**
 * 现网复现：改边距/行距 → 切字体 → 看是否回默认
 * 同时监控：滑块 DOM 值 / localStorage / CSS 变量 / 是否触发 resetAll
 */
const { chromium } = require('playwright')
const fs = require('fs')

const BASE = 'https://yexingchen.cn'
function creds() {
  const env = fs.readFileSync('D:/software/codex/codex_work/.secrets/local.env', 'utf8')
  const seg = env.split('#项目网站信息').pop()
  return { acc: /账号：\s*(\S+)/.exec(seg)[1], pw: /密码：\s*(\S+)/.exec(seg)[1] }
}

const snap = () => {
  const root = document.querySelector('.nrd')
  const cs = root ? getComputedStyle(root) : null
  let ls = null
  try { ls = JSON.parse(localStorage.getItem('xuanhuang:reader:settings') || 'null') } catch { /* 忽略 */ }
  const rowOf = (label) => Array.from(document.querySelectorAll('.nrd-set-row'))
    .find((r) => r.querySelector('span')?.textContent.trim() === label)
  const slider = (label) => {
    const inp = rowOf(label)?.querySelector('input[type=range]')
    return inp ? inp.value : null
  }
  // 面板底部的按钮文字，用来判断是否误触「恢复默认」
  const footBtns = Array.from(document.querySelectorAll('.nrd-set-foot .nrd-btn')).map((b) => b.textContent.trim())
  return {
    css: cs ? { pad: cs.getPropertyValue('--nrd-pad').trim(), lh: cs.getPropertyValue('--nrd-lh').trim(), size: cs.getPropertyValue('--nrd-size').trim() } : null,
    stored: ls ? { padding: ls.padding, lineHeight: ls.lineHeight, size: ls.size, font: ls.font } : null,
    ui: { 边距: slider('边距'), 行距: slider('行距'), 字号: slider('字号') },
    fontActive: document.querySelector('.nrd-seg-fonts button.on')?.textContent.trim() || null,
    footBtns,
  }
}

;(async () => {
  const { acc, pw } = creds()
  const b = await chromium.launch()
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })
  const p = await ctx.newPage()
  p.on('pageerror', (e) => console.log('[pageerror]', e.message.slice(0, 200)))

  await p.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(1000)
  await p.fill('input[type="text"], input[placeholder*="邮箱"], input[placeholder*="账号"]', acc).catch(() => {})
  await p.fill('input[type="password"]', pw)
  await p.keyboard.press('Enter')
  await p.waitForTimeout(3000)

  await p.goto(`${BASE}/novel`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(3000)
  await p.evaluate(() => {
    const t = Array.from(document.querySelectorAll('.ns-title')).find((x) => /诸神愚戏/.test(x.textContent || ''))
    t && t.click()
  })
  for (let i = 0; i < 20; i++) {
    await p.waitForTimeout(800)
    if (await p.evaluate(() => document.querySelectorAll('.nrd-p').length)) break
  }
  await p.waitForTimeout(600)

  // 唤 chrome → 设置抽屉
  const openSet = async () => {
    await p.mouse.click(195, 420)
    await p.waitForTimeout(400)
    await p.evaluate(() => {
      Array.from(document.querySelectorAll('.nrd-foot-tools button')).find((x) => /设置/.test(x.textContent || ''))?.click()
    })
    await p.waitForTimeout(700)
  }
  await openSet()
  console.log('0 初始:', JSON.stringify(await p.evaluate(snap)))

  // 拖边距 / 行距 / 字号
  const ok = await p.evaluate(() => {
    const set = (label, val) => {
      const row = Array.from(document.querySelectorAll('.nrd-set-row')).find((r) => r.querySelector('span')?.textContent.trim() === label)
      const inp = row?.querySelector('input[type=range]')
      if (!inp) return false
      inp.value = val
      inp.dispatchEvent(new Event('input', { bubbles: true }))
      return true
    }
    return { 边距: set('边距', 44), 行距: set('行距', 2.3), 字号: set('字号', 22) }
  })
  console.log('1 拖动结果:', JSON.stringify(ok))
  await p.waitForTimeout(800)
  console.log('2 调整后:', JSON.stringify(await p.evaluate(snap)))

  // 切字体
  const fontClicked = await p.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('.nrd-seg-fonts button')).find((x) => /黑体/.test(x.textContent || ''))
    if (!btn) return { ok: false, all: Array.from(document.querySelectorAll('.nrd-seg-fonts button')).map((x) => x.textContent.trim()) }
    btn.click()
    return { ok: true }
  })
  console.log('3 点字体:', JSON.stringify(fontClicked))

  for (const ms of [300, 1200, 3000]) {
    await p.waitForTimeout(ms)
    console.log(`4 切字体后 +${ms}ms:`, JSON.stringify(await p.evaluate(snap)))
  }

  await p.screenshot({ path: '../artifacts/_probe/live-font-switch.png' })

  // 关面板再开，看滑块显示
  await p.evaluate(() => { document.querySelector('.nrd-sheet-head .nrd-ic')?.click() })
  await p.waitForTimeout(400)
  await openSet()
  console.log('5 重开面板:', JSON.stringify(await p.evaluate(snap)))

  await b.close()
})()
