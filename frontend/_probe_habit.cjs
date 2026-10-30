/**
 * 习惯弹窗窄屏探针（本地开发用）
 * 依赖：cd frontend && npx vite --port 5199
 * 用法：node _probe_habit.cjs
 *
 * 量三件事：
 *   1) 页面是否横向溢出（root/body scrollWidth > clientWidth）
 *   2) 弹窗是否整个落在一屏内（rect 上下左右都不越界）+ footer 可见
 *   3) 弹窗 body 内部是否纵向滚动、宽度是否够（不产生横向滚动条）
 */
const { chromium } = require('playwright')

const CASES = [
  { name: '390x844', width: 390, height: 844 },
  { name: '360x780', width: 360, height: 780 },
  { name: '320x700', width: 320, height: 700 },
]

;(async () => {
  const browser = await chromium.launch({ args: ['--no-proxy-server'] })
  for (const c of CASES) {
    const ctx = await browser.newContext({
      viewport: { width: c.width, height: c.height },
      deviceScaleFactor: 2,
      isMobile: true,
      hasTouch: true,
    })
    const page = await ctx.newPage()
    const logs = []
    page.on('pageerror', (e) => logs.push('pageerror: ' + e.message))
    await page.goto('http://127.0.0.1:5199/_probe_habit.html?m=1', {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    })
    await page.waitForSelector('.ibtn--primary', { timeout: 15000 })
    await page.waitForTimeout(600)
    // 打开「新建习惯」
    await page.click('.ibtn--primary')
    await page.waitForSelector('.hb-dlg-compact', { timeout: 8000 })
    await page.waitForTimeout(700)
    // 后端没起时的报错 toast 会盖住表单，截图/量测前摘掉
    const killToast = () => page.evaluate(() => {
      document.querySelectorAll('.el-message, .el-notification').forEach((e) => e.remove())
    })
    await killToast()
    await page.waitForTimeout(120)

    // 对照组：摘掉移动端覆盖类，回到修复前（dialog 写死 420px 定宽）的宽度
    const before = await page.evaluate(() => {
      const dlg = document.querySelector('.hb-dlg-compact')
      const cls = dlg.className
      dlg.classList.remove('hb-dlg-compact')
      const b = dlg.getBoundingClientRect()
      const out = {
        dlgW: Math.round(b.width),
        left: Math.round(b.left),
        right: Math.round(b.right),
        overflowX: document.documentElement.scrollWidth - window.innerWidth,
      }
      dlg.className = cls
      return out
    })
    console.log('-- 修复前（去掉 hb-dlg-compact）: ' + JSON.stringify(before))

    const info = await page.evaluate(() => {
      const dlg = document.querySelector('.hb-dlg-compact')
      const body = dlg?.querySelector('.el-dialog__body')
      const foot = dlg?.querySelector('.el-dialog__footer')
      const r = (el) => {
        if (!el) return null
        const b = el.getBoundingClientRect()
        return {
          w: Math.round(b.width), h: Math.round(b.height),
          x: Math.round(b.x), y: Math.round(b.y),
          right: Math.round(b.right), bottom: Math.round(b.bottom),
        }
      }
      const vw = window.innerWidth
      const vh = window.innerHeight
      // 找出所有横向越界的表单元素（罪魁祸首定位）
      const offenders = []
      dlg?.querySelectorAll('*').forEach((el) => {
        const b = el.getBoundingClientRect()
        if (b.width === 0) return
        if (b.right > vw + 1 || b.left < -1) {
          offenders.push({
            cls: el.className && typeof el.className === 'string' ? el.className.slice(0, 60) : el.tagName,
            left: Math.round(b.left), right: Math.round(b.right),
          })
        }
      })
      return {
        vw, vh,
        rootScrollW: document.documentElement.scrollWidth,
        rootClientW: document.documentElement.clientWidth,
        bodyScrollW: document.body.scrollWidth,
        dlg: r(dlg),
        dlgStyle: dlg ? { pos: getComputedStyle(dlg).position, width: getComputedStyle(dlg).width } : null,
        body: r(body),
        bodyScroll: body ? { sh: body.scrollHeight, ch: body.clientHeight, sw: body.scrollWidth, cw: body.clientWidth } : null,
        foot: r(foot),
        footVisible: foot ? foot.getBoundingClientRect().bottom <= vh + 1 : null,
        offenders: offenders.slice(0, 8),
      }
    })
    console.log('===== ' + c.name + ' =====')
    console.log(JSON.stringify(info, null, 1))
    if (logs.length) console.log('LOGS: ' + logs.slice(0, 5).join(' | '))
    await killToast()
    await page.screenshot({ path: `../artifacts/_probe/habit-${c.name}.png` })

    // 「每年」档位：两个数值框最容易被定宽撑破
    await page.click('.hb-seg-btn:nth-child(4)')
    await page.waitForTimeout(500)
    const yearly = await page.evaluate(() => {
      const body = document.querySelector('.hb-dlg-compact .el-dialog__body')
      const nums = Array.from(document.querySelectorAll('.hb-dlg-compact .hb-year .el-input-number')).map((el) => {
        const b = el.getBoundingClientRect()
        return { x: Math.round(b.x), right: Math.round(b.right), w: Math.round(b.width) }
      })
      return {
        bodyW: body ? { cw: body.clientWidth, sw: body.scrollWidth } : null,
        nums,
        vw: window.innerWidth,
      }
    })
    console.log('-- 每年档：' + JSON.stringify(yearly))
    await killToast()
    await page.screenshot({ path: `../artifacts/_probe/habit-${c.name}-yearly.png` })
    await ctx.close()
  }
  await browser.close()
})()
