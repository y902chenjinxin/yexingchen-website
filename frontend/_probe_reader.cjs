/**
 * 阅读器交互探针（v2.46.286）：验证番茄式交互是否真的生效
 *   node _probe_reader.cjs
 * 需要先起 vite dev（5199）。
 */
const { chromium } = require('playwright')

const BASE = 'http://localhost:5199/_probe_reader.html'
const OUT = '../artifacts/_probe'

async function main() {
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } })
  const logs = []
  page.on('console', (m) => logs.push(`[${m.type()}] ${m.text()}`))
  page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message}`))

  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForTimeout(900)

  const q = (sel) => page.evaluate((s) => !!document.querySelector(s), sel)
  const result = {}

  // 1) 初始：顶栏/底栏应该隐藏（无 is-chrome）
  result.initChromeClass = await page.evaluate(() => document.querySelector('.nrd')?.className || '')
  result.barTransform = await page.evaluate(() => {
    const el = document.querySelector('.nrd-bar')
    return el ? getComputedStyle(el).transform : 'no-bar'
  })

  // 2) 点击页面中部 → 应唤出 chrome
  await page.mouse.click(195, 420)
  await page.waitForTimeout(400)
  result.afterMidClick = await page.evaluate(() => document.querySelector('.nrd')?.className || '')
  result.footVisible = await page.evaluate(() => {
    const el = document.querySelector('.nrd-foot')
    if (!el) return false
    const r = el.getBoundingClientRect()
    return r.height > 40 && getComputedStyle(el).opacity !== '0'
  })
  result.hasPrevChap = await page.evaluate(() => !!Array.from(document.querySelectorAll('.nrd-foot-nav')).find((b) => b.textContent.includes('上一章')))
  result.hasNextChap = await page.evaluate(() => !!Array.from(document.querySelectorAll('.nrd-foot-nav')).find((b) => b.textContent.includes('下一章')))
  result.hasOldPager = await page.evaluate(() => !!Array.from(document.querySelectorAll('button')).find((b) => b.textContent.trim() === '上一页'))
  await page.screenshot({ path: `${OUT}/reader-chrome.png` })

  // 3) 点底栏「目录」→ 抽屉出现（并从底部往上）
  await page.evaluate(() => {
    Array.from(document.querySelectorAll('.nrd-foot-tools button')).find((b) => b.textContent.includes('目录'))?.click()
  })
  await page.waitForTimeout(500)
  result.tocOpen = await q('.nrd-sheet-toc')
  result.tocItems = await page.evaluate(() => document.querySelectorAll('.nrd-sheet-toc .nrd-toc-item').length)
  result.tocRect = await page.evaluate(() => {
    const el = document.querySelector('.nrd-sheet-toc')
    if (!el) return null
    const r = el.getBoundingClientRect()
    return { top: Math.round(r.top), bottom: Math.round(r.bottom), h: Math.round(r.height) }
  })
  await page.screenshot({ path: `${OUT}/reader-toc.png` })

  // 4) 目录搜索
  await page.fill('.nrd-sheet-q', '结尾')
  await page.waitForTimeout(300)
  result.tocFiltered = await page.evaluate(() => document.querySelectorAll('.nrd-sheet-toc .nrd-toc-item').length)

  // 5) 点遮罩外的内容区 → 目录应保持（点抽屉内部不关）
  //    关闭目录：点顶栏区域外空白
  await page.evaluate(() => { document.querySelector('.nrd-sheet-q').value = '' })

  // 6) 切到设置抽屉
  await page.evaluate(() => {
    document.querySelector('.nrd-sheet .nrd-ic')?.click()
  })
  await page.waitForTimeout(300)
  await page.mouse.click(195, 420)   // 唤 chrome
  await page.waitForTimeout(300)
  await page.evaluate(() => {
    Array.from(document.querySelectorAll('.nrd-foot-tools button')).find((b) => b.textContent.includes('设置'))?.click()
  })
  await page.waitForTimeout(500)
  result.setOpen = await q('.nrd-sheet-set')
  result.hasCustomColor = await page.evaluate(() => !!document.querySelector('.nrd-color-input'))
  result.hasBgUpload = await page.evaluate(() => !!Array.from(document.querySelectorAll('.nrd-bg-btn')).find((b) => b.textContent.includes('上传图片')))
  result.themeDots = await page.evaluate(() => document.querySelectorAll('.nrd-dot').length)
  result.fontBtns = await page.evaluate(() => document.querySelectorAll('.nrd-seg-fonts button').length)
  result.fontRowOverflow = await page.evaluate(() => {
    const row = document.querySelector('.nrd-seg-fonts')
    if (!row) return null
    return { scrollW: row.scrollWidth, clientW: row.clientWidth, canScroll: row.scrollWidth > row.clientWidth }
  })
  await page.screenshot({ path: `${OUT}/reader-set.png` })

  // 7) 首行缩进是否生效
  result.paraIndent = await page.evaluate(() => {
    const p = document.querySelector('.nrd-p')
    return p ? getComputedStyle(p).textIndent : 'no-p'
  })

  // 8) 分页模式点右侧应翻页（percent 或标题变化）
  await page.evaluate(() => { document.querySelector('.nrd-sheet .nrd-ic')?.click() })
  await page.waitForTimeout(400)
  const before = await page.evaluate(() => document.querySelector('.nrd-pct')?.textContent)
  await page.mouse.click(360, 420)
  await page.waitForTimeout(600)
  const after = await page.evaluate(() => document.querySelector('.nrd-pct')?.textContent)
  result.pageTurn = { before, after, changed: before !== after }

  console.log(JSON.stringify(result, null, 2))
  if (logs.length) console.log('--- console ---\n' + logs.slice(0, 15).join('\n'))
  await browser.close()
}

main().catch((e) => { console.error('PROBE FAIL', e); process.exit(1) })
