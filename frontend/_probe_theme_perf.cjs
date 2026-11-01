/**
 * 主题切换耗时测量（v2.46.313）
 *   node _probe_theme_perf.cjs
 * 对比：①直接改 data-theme（无动画）②点击「白天/夜间」（走 View Transitions 揭示）
 */
const { chromium } = require('playwright')
const fs = require('fs')
const BASE = 'https://yexingchen.cn'
const env = fs.readFileSync('D:/software/codex/codex_work/.secrets/local.env', 'utf8').split('#项目网站信息').pop()
const ACC = /账号：\s*(\S+)/.exec(env)[1]
const PW = /密码：\s*(\S+)/.exec(env)[1]

;(async () => {
  const b = await chromium.launch()
  const ctx = await b.newContext({ viewport: { width: 1280, height: 820 } })
  const p = await ctx.newPage()
  await p.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForTimeout(800)
  await p.fill('input[type="text"], input[placeholder*="账号"]', ACC).catch(() => {})
  await p.fill('input[type="password"]', PW)
  await p.keyboard.press('Enter')
  await p.waitForTimeout(3500)

  const install = async () => {
    await p.evaluate(() => {
      window.__lt = []
      window.__po = new PerformanceObserver((l) => l.getEntries().forEach((e) => window.__lt.push(e.duration)))
      window.__po.observe({ entryTypes: ['longtask'] })
    })
  }

  for (const path of ['/profile', '/workbench']) {
    await p.goto(`${BASE}${path}`, { waitUntil: 'domcontentloaded', timeout: 60000 })
    await p.waitForTimeout(2200)

    // ① 直接改属性：纯样式重算 + 重绘成本
    await install()
    const direct = await p.evaluate(async () => {
      const t0 = performance.now()
      document.documentElement.dataset.theme = 'day'
      const tSet = performance.now() - t0
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))
      const tFrame = performance.now() - t0
      await new Promise((r) => setTimeout(r, 900))
      const lt = window.__lt || []
      window.__po && window.__po.disconnect()
      return { tSet: +tSet.toFixed(1), tFrame: +tFrame.toFixed(0), longTotal: Math.round(lt.reduce((a, c) => a + c, 0)), longMax: Math.round(Math.max(0, ...lt)), n: lt.length }
    })
    console.log(`[${path}] 直接改属性:`, JSON.stringify(direct))

    // 回到夜间
    await p.evaluate(() => { document.documentElement.dataset.theme = 'night' })
    await p.waitForTimeout(1200)

    // ② 点「白天」按钮：View Transitions 揭示
    const hasSeg = await p.evaluate(() => !!document.querySelector('.theme-seg'))
    if (!hasSeg) { console.log(`[${path}] 没有 .theme-seg，跳过点击测试`); continue }
    await install()
    const t0 = Date.now()
    await p.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('.theme-seg button, .theme-seg *')).find((x) => (x.textContent || '').trim() === '白天')
      if (btn) btn.click()
    })
    // 等动画/切换完成：轮询 data-theme + 固定等待
    await p.waitForFunction(() => document.documentElement.dataset.theme === 'day', { timeout: 15000 }).catch(() => {})
    const elapsed = Date.now() - t0
    await p.waitForTimeout(1500)
    const click = await p.evaluate(() => {
      const lt = window.__lt || []
      window.__po && window.__po.disconnect()
      const anims = document.getAnimations ? document.getAnimations().map((a) => a.constructor.name) : []
      return { longTotal: Math.round(lt.reduce((a, c) => a + c, 0)), longMax: Math.round(Math.max(0, ...lt)), n: lt.length, anims: anims.slice(0, 4) }
    })
    console.log(`[${path}] 点击切换: 属性生效 ${elapsed}ms`, JSON.stringify(click))
    await p.evaluate(() => { document.documentElement.dataset.theme = 'night' })
    await p.waitForTimeout(800)
  }
  await b.close()
})()
