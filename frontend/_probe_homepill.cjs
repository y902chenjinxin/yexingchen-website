const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')
const OUT = path.resolve(__dirname, '../artifacts/_probe')
const BASE = 'https://yexingchen.cn'
function creds() {
  const env = fs.readFileSync('D:/software/codex/codex_work/.secrets/local.env', 'utf8')
  const seg = env.split('#项目网站信息').pop()
  return { acc: /账号：\s*(\S+)/.exec(seg)[1], pw: /密码：\s*(\S+)/.exec(seg)[1] }
}
;(async () => {
  const { acc, pw } = creds()
  const b = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 3,
    userAgent: 'Mozilla/5.0 (Linux; Android 12; XuanHuangApp) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36 XuanHuangApp/1.0' })
  const p = await ctx.newPage()
  await p.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.fill('input[type="text"], input[placeholder*="邮箱"], input[placeholder*="账号"]', acc).catch(()=>{})
  await p.fill('input[type="password"]', pw)
  await p.keyboard.press('Enter')
  await p.waitForTimeout(3200)
  await p.goto(`${BASE}/workbench`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(2000)
  const info = await p.evaluate(() => {
    const pick = (el) => {
      const cs = getComputedStyle(el)
      const r = el.getBoundingClientRect()
      return { cls: String(el.className).slice(0, 40), w: Math.round(r.width), h: Math.round(r.height),
        bg: cs.backgroundColor, img: cs.backgroundImage.slice(0, 60), bf: cs.backdropFilter, bd: cs.borderTopWidth + ' ' + cs.borderTopColor, r: cs.borderRadius }
    }
    const cells = [...document.querySelectorAll('.abb-cell')].slice(0, 3).map(pick)
    // 所有「看起来像胶囊」的小元素：圆角>=999 或宽高比宽扁 且 有背景
    const pills = []
    document.querySelectorAll('#app *').forEach((el) => {
      const cs = getComputedStyle(el)
      const r = el.getBoundingClientRect()
      if (r.width < 30 || r.width > 300 || r.height < 16 || r.height > 60) return
      const rad = parseFloat(cs.borderTopLeftRadius)
      if (rad >= 12 && cs.backgroundColor !== 'rgba(0, 0, 0, 0)') {
        pills.push({ ...pick(el), rad: Math.round(rad) })
      }
    })
    return { cells, pills: pills.slice(0, 24) }
  })
  console.log(JSON.stringify(info, null, 1))
  const grid = await p.locator('.abb-grid').boundingBox()
  if (grid) await p.screenshot({ path: `${OUT}/crop-home-grid.png`, clip: { x: 0, y: grid.y - 40, width: 390, height: 300 } })
  await b.close()
})()
