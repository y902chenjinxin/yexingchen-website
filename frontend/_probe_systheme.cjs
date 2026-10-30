const { chromium } = require('playwright')
const BASE = 'http://localhost:5199/_probe_reader.html'

const state = () => {
  const root = document.querySelector('.nrd')
  const cs = root ? getComputedStyle(root) : null
  return {
    theme: root ? (root.className.match(/theme-(\w+)/) || [])[1] : null,
    bg: cs ? cs.backgroundColor : null,
    text: cs ? cs.color : null,
    mqDark: window.matchMedia('(prefers-color-scheme: dark)').matches,
    mqLight: window.matchMedia('(prefers-color-scheme: light)').matches,
    stored: (() => { try { return JSON.parse(localStorage.getItem('xuanhuang:reader:settings') || 'null') } catch { return null } })(),
  }
}

async function run(scheme) {
  const b = await chromium.launch()
  const p = await b.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, colorScheme: scheme })
  p.on('pageerror', (e) => console.log('[pageerror]', e.message))
  await p.goto(BASE, { waitUntil: 'networkidle' })
  await p.evaluate(() => localStorage.removeItem('xuanhuang:reader:settings'))
  await p.reload({ waitUntil: 'networkidle' })
  await p.waitForTimeout(1500)
  console.log(`\n=== 系统配色 ${scheme} ===`)
  console.log('进入时:', JSON.stringify(await p.evaluate(state)))

  await p.mouse.click(195, 420); await p.waitForTimeout(350)
  await p.evaluate(() => Array.from(document.querySelectorAll('.nrd-foot-tools button')).find((x) => /设置/.test(x.textContent||''))?.click())
  await p.waitForTimeout(600)

  // 点「跟随系统日/夜」
  const clicked = await p.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('.nrd-seg button')).find((x) => /跟随系统/.test(x.textContent || ''))
    if (!btn) return { ok: false, all: Array.from(document.querySelectorAll('.nrd-seg button')).map((x) => x.textContent.trim()) }
    btn.click()
    return { ok: true, cls: btn.className }
  })
  console.log('点跟随系统:', JSON.stringify(clicked))
  await p.waitForTimeout(1200)
  console.log('点后:', JSON.stringify(await p.evaluate(state)))
  await p.screenshot({ path: `../artifacts/_probe/systheme-${scheme}.png` })
  await b.close()
}

;(async () => { await run('light'); await run('dark') })()
