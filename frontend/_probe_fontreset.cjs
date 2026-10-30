/**
 * 复现「调了边距/行距 → 切字体 → 回默认」
 * 逐步读：CSS 变量实际值 / localStorage / 滑块显示值
 */
const { chromium } = require('playwright')
const path = require('path')

const OUT = path.resolve(__dirname, '../artifacts/_probe')
const BASE = 'http://localhost:5199/_probe_reader.html'

const snap = () => {
  const root = document.querySelector('.nrd')
  const cs = root ? getComputedStyle(root) : null
  let ls = null
  try { ls = JSON.parse(localStorage.getItem('xuanhuang:reader:settings') || 'null') } catch { /* 忽略 */ }
  const slider = (label) => {
    const row = Array.from(document.querySelectorAll('.nrd-set-row')).find((r) => r.querySelector('span')?.textContent.trim() === label)
    const inp = row?.querySelector('input[type=range]')
    const em = row?.querySelector('em')
    return inp ? { value: inp.value, shown: em?.textContent.trim() } : null
  }
  return {
    css: cs ? {
      pad: cs.getPropertyValue('--nrd-pad').trim(),
      lh: cs.getPropertyValue('--nrd-lh').trim(),
      size: cs.getPropertyValue('--nrd-size').trim(),
      font: cs.getPropertyValue('--nrd-font').trim().slice(0, 22),
    } : null,
    stored: ls ? { padding: ls.padding, lineHeight: ls.lineHeight, size: ls.size, font: ls.font } : null,
    ui: { 行距: slider('行距'), 边距: slider('边距'), 字号: slider('字号') },
  }
}

;(async () => {
  const b = await chromium.launch()
  const p = await b.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })
  p.on('pageerror', (e) => console.log('[pageerror]', e.message))
  await p.goto(BASE, { waitUntil: 'networkidle' })
  await p.evaluate(() => localStorage.removeItem('xuanhuang:reader:settings'))
  await p.reload({ waitUntil: 'networkidle' })
  await p.waitForTimeout(1500)

  // 唤 chrome → 开设置
  await p.mouse.click(195, 420)
  await p.waitForTimeout(400)
  await p.evaluate(() => {
    Array.from(document.querySelectorAll('.nrd-foot-tools button')).find((x) => /设置/.test(x.textContent || ''))?.click()
  })
  await p.waitForTimeout(600)
  console.log('0 初始:', JSON.stringify(await p.evaluate(snap)))

  // 拖边距到 44、行距到 2.3、字号 22
  await p.evaluate(() => {
    const set = (label, val) => {
      const row = Array.from(document.querySelectorAll('.nrd-set-row')).find((r) => r.querySelector('span')?.textContent.trim() === label)
      const inp = row?.querySelector('input[type=range]')
      if (!inp) return false
      inp.value = val
      inp.dispatchEvent(new Event('input', { bubbles: true }))
      inp.dispatchEvent(new Event('change', { bubbles: true }))
      return true
    }
    set('边距', 44)
    set('行距', 2.3)
    set('字号', 22)
  })
  await p.waitForTimeout(500)
  console.log('1 调整后:', JSON.stringify(await p.evaluate(snap)))

  // 切字体（点「黑体」）
  const clicked = await p.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('.nrd-seg-fonts button')).find((x) => /黑体/.test(x.textContent || ''))
    if (!btn) return { ok: false, list: Array.from(document.querySelectorAll('.nrd-seg-fonts button')).map((x) => x.textContent.trim()) }
    btn.click()
    return { ok: true }
  })
  console.log('2 点字体:', JSON.stringify(clicked))
  await p.waitForTimeout(2500)
  console.log('3 切字体后:', JSON.stringify(await p.evaluate(snap)))

  await p.screenshot({ path: `${OUT}/font-reset-after.png` })

  // 重新加载页面 → 看是否持久化
  await p.reload({ waitUntil: 'networkidle' })
  await p.waitForTimeout(1800)
  await p.mouse.click(195, 420)
  await p.waitForTimeout(300)
  await p.evaluate(() => {
    Array.from(document.querySelectorAll('.nrd-foot-tools button')).find((x) => /设置/.test(x.textContent || ''))?.click()
  })
  await p.waitForTimeout(600)
  console.log('4 重进后:', JSON.stringify(await p.evaluate(snap)))

  await b.close()
})()
