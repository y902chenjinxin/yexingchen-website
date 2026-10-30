/**
 * 现网验证：设备 A 改设置 → 设备 B（全新上下文，无本地缓存）应拿到同样的设置
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
  return {
    pad: cs ? cs.getPropertyValue('--nrd-pad').trim() : null,
    lh: cs ? cs.getPropertyValue('--nrd-lh').trim() : null,
    font: cs ? cs.getPropertyValue('--nrd-font').trim().slice(0, 14) : null,
    stored: ls ? { padding: ls.padding, lineHeight: ls.lineHeight, font: ls.font, autoTheme: ls.autoTheme } : null,
  }
}

async function openBook(b, label) {
  const { acc, pw } = creds()
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })
  const p = await ctx.newPage()
  await p.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(1000)
  await p.fill('input[type="text"], input[placeholder*="邮箱"], input[placeholder*="账号"]', acc).catch(() => {})
  await p.fill('input[type="password"]', pw)
  await p.keyboard.press('Enter')
  await p.waitForTimeout(3000)
  await p.goto(`${BASE}/novel`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(2500)
  await p.evaluate(() => {
    const t = Array.from(document.querySelectorAll('.ns-title')).find((x) => /诸神愚戏/.test(x.textContent || ''))
    t && t.click()
  })
  for (let i = 0; i < 20; i++) {
    await p.waitForTimeout(800)
    if (await p.evaluate(() => document.querySelectorAll('.nrd-p').length)) break
  }
  await p.waitForTimeout(800)
  console.log(`[${label}] 进入后:`, JSON.stringify(await p.evaluate(snap)))
  return { ctx, p }
}

async function openSet(p) {
  await p.mouse.click(195, 420)
  await p.waitForTimeout(400)
  await p.evaluate(() => {
    Array.from(document.querySelectorAll('.nrd-foot-tools button')).find((x) => /设置/.test(x.textContent || ''))?.click()
  })
  await p.waitForTimeout(700)
}

;(async () => {
  const b = await chromium.launch()

  // ---- 设备 A：改设置 ----
  const A = await openBook(b, 'A 设备')
  await openSet(A.p)
  await A.p.evaluate(() => {
    const set = (label, val) => {
      const row = Array.from(document.querySelectorAll('.nrd-set-row')).find((r) => r.querySelector('span')?.textContent.trim() === label)
      const inp = row?.querySelector('input[type=range]')
      if (inp) { inp.value = val; inp.dispatchEvent(new Event('input', { bubbles: true })) }
    }
    set('边距', 46); set('行距', 2.2)
    const fontBtn = Array.from(document.querySelectorAll('.nrd-seg-fonts button')).find((x) => /楷体/.test(x.textContent || ''))
    fontBtn && fontBtn.click()
    const timeBtn = Array.from(document.querySelectorAll('.nrd-seg button')).find((x) => x.textContent.trim() === '按时间')
    timeBtn && timeBtn.click()
  })
  await A.p.waitForTimeout(3000)   // 等防抖推送（1.5s）+ 网络
  console.log('[A] 改完后:', JSON.stringify(await A.p.evaluate(snap)))
  await A.ctx.close()

  // ---- 设备 B：全新上下文（无 localStorage / 无缓存）----
  const B = await openBook(b, 'B 设备')
  await B.p.waitForTimeout(1500)   // 等 pullSettings 回来
  console.log('[B] 拉到:', JSON.stringify(await B.p.evaluate(snap)), '← 应与 A 一致（边距 46 / 行距 2.2 / 楷体）')
  await B.p.screenshot({ path: '../artifacts/_probe/sync-device-b.png' })
  await B.ctx.close()

  await b.close()
})()
