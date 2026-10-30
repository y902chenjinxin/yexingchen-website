const { chromium } = require('playwright')
const BASE = 'http://localhost:5199/_probe_reader.html'

const state = () => {
  let ls = null
  try { ls = JSON.parse(localStorage.getItem('xuanhuang:reader:settings') || 'null') } catch {}
  const btn = Array.from(document.querySelectorAll('.nrd-set-foot .nrd-btn')).find((b) => /恢复默认|再点一次/.test(b.textContent))
  return {
    stored: ls ? { padding: ls.padding, lineHeight: ls.lineHeight, size: ls.size, font: ls.font } : null,
    resetBtnText: btn ? btn.textContent.trim() : null,
    armed: btn ? btn.classList.contains('armed') : null,
  }
}

;(async () => {
  const b = await chromium.launch()
  const p = await b.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })
  p.on('pageerror', (e) => console.log('[pageerror]', e.message))
  await p.goto(BASE, { waitUntil: 'networkidle' })
  await p.waitForTimeout(1500)
  await p.mouse.click(195, 420); await p.waitForTimeout(350)
  await p.evaluate(() => Array.from(document.querySelectorAll('.nrd-foot-tools button')).find((x) => /设置/.test(x.textContent||''))?.click())
  await p.waitForTimeout(600)

  // 先设一组非默认值
  await p.evaluate(() => {
    const set = (label, val) => {
      const row = Array.from(document.querySelectorAll('.nrd-set-row')).find((r) => r.querySelector('span')?.textContent.trim() === label)
      const inp = row?.querySelector('input[type=range]')
      if (inp) { inp.value = val; inp.dispatchEvent(new Event('input', { bubbles: true })) }
    }
    set('边距', 44); set('行距', 2.3)
  })
  await p.waitForTimeout(500)
  console.log('A 设好非默认:', JSON.stringify(await p.evaluate(state)))

  // 点一次恢复默认
  await p.evaluate(() => Array.from(document.querySelectorAll('.nrd-set-foot .nrd-btn')).find((b) => /恢复默认/.test(b.textContent))?.click())
  await p.waitForTimeout(400)
  console.log('B 点一次后:', JSON.stringify(await p.evaluate(state)), '← 值应保持 44/2.3，按钮应变「再点一次确认」')

  // 等 3.5s 自动撤销
  await p.waitForTimeout(3500)
  console.log('C 等3.5s后:', JSON.stringify(await p.evaluate(state)), '← 按钮应回到「恢复默认」')

  // 连点两次
  const clickReset = () => p.evaluate(() => Array.from(document.querySelectorAll('.nrd-set-foot .nrd-btn')).find((b) => /恢复默认|再点一次/.test(b.textContent))?.click())
  await clickReset(); await p.waitForTimeout(300); await clickReset()
  await p.waitForTimeout(600)
  console.log('D 连点两次后:', JSON.stringify(await p.evaluate(state)), '← 应回到默认 20/1.9')

  await p.screenshot({ path: '../artifacts/_probe/reset-arm.png' })
  await b.close()
})()
