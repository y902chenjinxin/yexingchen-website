const { chromium } = require('playwright')
const BASE = 'http://localhost:5199/_probe_reader.html'

const state = () => {
  const root = document.querySelector('.nrd')
  const cs = root ? getComputedStyle(root) : null
  const onBtn = Array.from(document.querySelectorAll('.nrd-seg button')).find((b) => b.classList.contains('on') && /关闭|跟随系统|按时间/.test(b.textContent))
  return {
    theme: root ? (root.className.match(/theme-(\w+)/) || [])[1] : null,
    bg: cs?.backgroundColor,
    autoOn: onBtn ? onBtn.textContent.trim() : null,
    hint: document.querySelector('.nrd-hint')?.textContent.replace(/\s+/g, ' ').trim() || null,
    storedAuto: (() => { try { return JSON.parse(localStorage.getItem('xuanhuang:reader:settings') || 'null')?.autoTheme } catch { return null } })(),
  }
}

;(async () => {
  const b = await chromium.launch()
  const p = await b.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, colorScheme: 'light' })
  p.on('pageerror', (e) => console.log('[pageerror]', e.message))
  await p.goto(BASE, { waitUntil: 'networkidle' })
  await p.evaluate(() => localStorage.removeItem('xuanhuang:reader:settings'))
  await p.reload({ waitUntil: 'networkidle' })
  await p.waitForTimeout(1500)
  await p.mouse.click(195, 420); await p.waitForTimeout(350)
  await p.evaluate(() => Array.from(document.querySelectorAll('.nrd-foot-tools button')).find((x) => /设置/.test(x.textContent||''))?.click())
  await p.waitForTimeout(600)

  console.log('本机时间:', await p.evaluate(() => new Date().toLocaleString('zh-CN')))
  console.log('0 初始:', JSON.stringify(await p.evaluate(state)))

  const click = (label) => p.evaluate((l) => {
    const btn = Array.from(document.querySelectorAll('.nrd-seg button')).find((x) => x.textContent.trim() === l)
    btn && btn.click()
    return !!btn
  }, label)

  console.log('点「跟随系统」:', await click('跟随系统'))
  await p.waitForTimeout(700)
  console.log('1:', JSON.stringify(await p.evaluate(state)))

  console.log('点「按时间」:', await click('按时间'))
  await p.waitForTimeout(700)
  console.log('2:', JSON.stringify(await p.evaluate(state)), '← 当前 00:30 应判为夜间')

  console.log('点「关闭」:', await click('关闭'))
  await p.waitForTimeout(700)
  console.log('3:', JSON.stringify(await p.evaluate(state)), '← 保持当前离线，不再自动改')

  await p.screenshot({ path: '../artifacts/_probe/autotheme.png' })
  await b.close()
})()
