/** 全站扫描：找出剩余的「硬描边 / 实色大块 / 底部遮挡」，并逐页截图 */
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')
const OUT = path.resolve(__dirname, '../artifacts/_probe')
const BASE = process.env.PROBE_BASE || 'https://yexingchen.cn'
function creds() {
  const env = fs.readFileSync('D:/software/codex/codex_work/.secrets/local.env', 'utf8')
  const seg = env.split('#项目网站信息').pop()
  return { acc: /账号：\s*(\S+)/.exec(seg)[1], pw: /密码：\s*(\S+)/.exec(seg)[1] }
}
const ROUTES = [
  ['/workbench', 'home'],
  ['/notes', 'notes'],
  ['/assistant', 'assistant'],
  ['/music', 'music'],
  ['/tool', 'tools'],
  ['/finance', 'finance'],
  ['/contacts', 'contacts'],
  ['/novel', 'novel'],
  ['/life', 'life'],
  ['/study', 'study'],
  ['/video', 'video'],
  ['/footprint', 'footprint'],
]
;(async () => {
  const { acc, pw } = creds()
  const b = await chromium.launch({ args: ['--no-proxy-server'] })
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2,
    userAgent: 'Mozilla/5.0 (Linux; Android 12; XuanHuangApp) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36 XuanHuangApp/1.0' })
  const p = await ctx.newPage()
  await p.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.fill('input[type="text"], input[placeholder*="邮箱"], input[placeholder*="账号"]', acc).catch(()=>{})
  await p.fill('input[type="password"]', pw)
  await p.keyboard.press('Enter')
  await p.waitForTimeout(3200)

  const report = []
  for (const [url, name] of ROUTES) {
    try {
      await p.goto(`${BASE}${url}`, { waitUntil: 'networkidle', timeout: 45000 })
      await p.waitForTimeout(1500)
      const r = await p.evaluate(() => {
        const out = { hard: [], solid: [], over: [] }
        const vw = innerWidth, vh = innerHeight
        document.querySelectorAll('#app *').forEach((el) => {
          const cs = getComputedStyle(el)
          const rect = el.getBoundingClientRect()
          if (rect.width < 8 || rect.height < 8) return
          if (rect.bottom < 0 || rect.top > vh) return
          const bw = parseFloat(cs.borderTopWidth) + parseFloat(cs.borderLeftWidth)
          const bc = cs.borderTopColor
          const hasBorder = bw >= 1.5 && bc && !/rgba\(0, 0, 0, 0\)|transparent/.test(bc)
          if (hasBorder && !el.closest('.el-popper') && !el.matches('input,textarea,img,svg,path,button')) {
            out.hard.push(`${el.className.toString().slice(0, 46)}|${cs.borderTopWidth}|${bc}`)
          }
          // 面积 > 25% 视口的实色（非透明）背景 → 疑似「大色块」
          const solidBg = cs.backgroundColor && !/rgba\(0, 0, 0, 0\)|transparent/.test(cs.backgroundColor)
          if (solidBg && rect.width * rect.height > vw * vh * 0.25) {
            out.solid.push(`${el.className.toString().slice(0, 40)}|${cs.backgroundColor}`)
          }
        })
        return {
          hard: [...new Set(out.hard)].slice(0, 8),
          hardCount: out.hard.length,
          solid: [...new Set(out.solid)].slice(0, 6),
          pad: getComputedStyle(document.querySelector('#app')).paddingBottom,
        }
      })
      report.push({ name, url, ...r })
      await p.screenshot({ path: `${OUT}/sw-${name}.png` })
    } catch (e) {
      report.push({ name, url, err: String(e).slice(0, 80) })
    }
  }
  for (const r of report) {
    console.log(`\n## ${r.name} ${r.url}  pad=${r.pad || '-'} hard=${r.hardCount ?? '-'}`)
    if (r.err) { console.log('  ERR', r.err); continue }
    r.hard.forEach((h) => console.log('  BORDER', h))
    r.solid.forEach((s) => console.log('  SOLID ', s))
  }
  await b.close()
})()
