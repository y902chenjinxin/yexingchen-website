/**
 * 实时观战面板：把 playwright 操作现网的全过程推流到浏览器
 * 访问 http://localhost:5299 （present_files 打开即右侧面板）
 *   /      → 面板页面
 *   /sse   → 画面帧 + 日志（Server-Sent Events）
 */
const http = require('http')
const fs = require('fs')
const { chromium } = require('playwright')

const PORT = 5299
const BASE = 'https://yexingchen.cn'
const W = 400
const H = 820

let clients = []
let latestFrame = ''
let steps = []
let status = '启动中'

function sse(res, event, data) {
  res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`)
}
function broadcast(event, data) {
  for (const c of clients) { try { sse(c, event, data) } catch { /* 忽略 */ } }
}
function log(text, kind = 'op') {
  const item = { t: new Date().toLocaleTimeString('zh-CN', { hour12: false }), text, kind }
  steps.push(item)
  broadcast('log', item)
  console.log(`[${item.t}] ${text}`)
}
function setStatus(s) { status = s; broadcast('status', s) }

const PAGE = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>阅读器实测 · 实时画面</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin:0; background:#0b0e14; color:#d7dce5;
    font:13px/1.6 -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
    display:flex; flex-direction:column; height:100vh; overflow:hidden; }
  header { padding:10px 14px; border-bottom:1px solid #1c2230; display:flex; align-items:center; gap:10px; flex-shrink:0; }
  header b { font-size:13px; font-weight:600; color:#eef1f6; letter-spacing:.02em; }
  #st { font-size:11.5px; color:#7c8798; }
  #st::before { content:''; display:inline-block; width:6px; height:6px; border-radius:50%;
    background:#3ba55d; margin-right:6px; vertical-align:1px; animation:pulse 1.4s infinite; }
  @keyframes pulse { 50% { opacity:.25; } }
  main { flex:1; display:flex; min-height:0; }
  .stage { flex:0 0 auto; width:${W}px; padding:12px; display:flex; align-items:center; justify-content:center;
    background:radial-gradient(circle at 50% 40%, #151a24 0%, #0b0e14 70%); }
  .phone { position:relative; width:${W - 24}px; border-radius:20px; overflow:hidden;
    box-shadow:0 18px 50px -18px #000, 0 0 0 1px #232a38; background:#12161f; }
  .phone img { display:block; width:100%; height:auto; }
  .phone .ph { padding:${Math.round((H / W) * 100)}% 0; }
  aside { flex:1; min-width:0; border-left:1px solid #1c2230; display:flex; flex-direction:column; }
  .ttl { padding:8px 12px; font-size:11px; letter-spacing:.14em; color:#5f6b7d; text-transform:uppercase;
    border-bottom:1px solid #161c27; flex-shrink:0; }
  #logs { flex:1; overflow-y:auto; padding:8px 12px 24px; }
  .li { display:flex; gap:8px; padding:4px 0; font-size:12.2px; border-bottom:1px dashed #151b25; }
  .li .tm { color:#4d586a; font-variant-numeric:tabular-nums; flex-shrink:0; }
  .li .tx { color:#c3cad6; word-break:break-word; }
  .li.warn .tx { color:#e0b252; }
  .li.bad .tx { color:#e2725f; }
  .li.ok .tx { color:#57ab6f; }
  .li.data .tx { color:#6fa8dc; font-family:ui-monospace,Menlo,monospace; font-size:11.4px; }
</style></head><body>
<header><b>阅读器 · 现网实测 v2.46.296</b><span id="st">连接中…</span></header>
<main>
  <div class="stage"><div class="phone"><img id="v" alt="实时画面"><div class="ph" id="ph"></div></div></div>
  <aside><div class="ttl">操作时间线</div><div id="logs"></div></aside>
</main>
<script>
  let v = document.getElementById('v')
  const logs = document.getElementById('logs')
  const st = document.getElementById('st')
  let buf = null
  const es = new EventSource('/sse')
  es.addEventListener('frame', (e) => {
    const src = 'data:image/jpeg;base64,' + JSON.parse(e.data)
    if (!buf) { v.src = src; document.getElementById('ph').style.display = 'none' }
    else { buf.src = src }
    const tmp = buf; buf = v; v = tmp
  })
  es.addEventListener('log', (e) => {
    const d = JSON.parse(e.data)
    const li = document.createElement('div')
    li.className = 'li ' + (d.kind || '')
    li.innerHTML = '<span class="tm">' + d.t + '</span><span class="tx"></span>'
    li.querySelector('.tx').textContent = d.text
    logs.appendChild(li)
    logs.scrollTop = logs.scrollHeight
  })
  es.addEventListener('status', (e) => { st.textContent = JSON.parse(e.data) })
  es.onerror = () => { st.textContent = '连接已断开' }
</script></body></html>`

const server = http.createServer((req, res) => {
  if (req.url === '/sse') {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    })
    res.write(': ok\n\n')
    clients.push(res)
    sse(res, 'status', status)
    for (const s of steps) sse(res, 'log', s)
    if (latestFrame) sse(res, 'frame', latestFrame)
    req.on('close', () => { clients = clients.filter((c) => c !== res) })
    return
  }
  res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' })
  res.end(PAGE)
})

function creds() {
  const env = fs.readFileSync('D:/software/codex/codex_work/.secrets/local.env', 'utf8')
  const seg = env.split('#项目网站信息').pop()
  return { acc: /账号：\s*(\S+)/.exec(seg)[1], pw: /密码：\s*(\S+)/.exec(seg)[1] }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function measure(p, tag) {
  const g = await p.evaluate(() => {
    const box = (sel) => {
      const el = document.querySelector(sel)
      if (!el) return null
      const r = el.getBoundingClientRect()
      return Math.round(r.top) + '~' + Math.round(r.bottom) + ' (h' + Math.round(r.height) + ')'
    }
    const nrd = document.querySelector('.nrd')
    const nr = nrd ? nrd.getBoundingClientRect() : null
    return {
      视口: window.innerHeight + ' · 可视 ' + (window.visualViewport ? Math.round(window.visualViewport.height) : 'n/a'),
      容器: nr ? Math.round(nr.top) + '~' + Math.round(nr.bottom) + ' (h' + Math.round(nr.height) + ')' : '未进入',
      底栏: box('.nrd-foot'),
      底栏按钮: box('.nrd-foot-tools'),
      抽屉: box('.nrd-sheet'),
      白区高度: nr ? Math.round(window.innerHeight - nr.bottom) : null,
      按钮在屏内: (() => {
        const t = document.querySelector('.nrd-foot-tools')
        if (!t) return '底栏未渲染'
        const r = t.getBoundingClientRect()
        return r.bottom <= window.innerHeight + 1 && r.top >= 0 ? '是 ✅' : '否 ❌ 底边 ' + Math.round(r.bottom)
      })(),
    }
  })
  for (const [k, v] of Object.entries(g)) {
    if (v === null || v === undefined) continue
    log(`${k}：${v}`, k === '白区高度' && v > 0 ? 'bad' : 'data')
  }
}

async function run() {
  const { acc, pw } = creds()
  const b = await chromium.launch()
  const ctx = await b.newContext({
    viewport: { width: W, height: H }, isMobile: true, hasTouch: true, deviceScaleFactor: 2,
  })
  const p = await ctx.newPage()

  // CDP 逐帧推流
  const cdp = await ctx.newCDPSession(p)
  cdp.on('Page.screencastFrame', async ({ data, sessionId }) => {
    latestFrame = data
    broadcast('frame', data)
    try { await cdp.send('Page.screencastFrameAck', { sessionId }) } catch { /* 忽略 */ }
  })
  await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 62, maxWidth: W * 2, maxHeight: H * 2, everyNthFrame: 1 })

  p.on('pageerror', (e) => log('页面报错：' + e.message.slice(0, 160), 'bad'))

  setStatus('登录中')
  log('打开现网登录页', 'op')
  await p.goto(`${BASE}/login`, { waitUntil: 'networkidle', timeout: 60000 })
  await sleep(1200)
  await p.fill('input[type="text"], input[placeholder*="邮箱"], input[placeholder*="账号"]', acc).catch(() => {})
  await p.fill('input[type="password"]', pw)
  await p.keyboard.press('Enter')
  await sleep(2600)
  log('已登录 → 工作台', 'ok')

  setStatus('进入小说列表')
  await p.goto(`${BASE}/novel`, { waitUntil: 'networkidle', timeout: 60000 })
  await sleep(3200)
  const warm = await p.evaluate(() => {
    const hit = performance.getEntriesByType('resource').some((e) => /NovelReadView-.*\.js/.test(e.name))
    return hit ? '已预取 ✅' : '未预取'
  })
  log(`小说书架已加载（阅读器 chunk ${warm}）`, 'ok')

  setStatus('打开《诸神愚戏》')
  log('点击《诸神愚戏》（1463 章）', 'op')
  const t0 = Date.now()
  await p.evaluate(() => {
    const t = Array.from(document.querySelectorAll('.ns-title')).find((x) => /诸神愚戏/.test(x.textContent || ''))
    t && t.click()
  })
  for (let i = 0; i < 30; i++) {
    await sleep(500)
    const st = await p.evaluate(() => ({
      loading: !!document.querySelector('.nrd-loading'),
      paras: document.querySelectorAll('.nrd-p').length,
    }))
    if (st.paras > 0) {
      log(`正文出现，耗时 ${((Date.now() - t0) / 1000).toFixed(1)}s（段落 ${st.paras}）`, 'warn')
      break
    }
    if (i === 6) log('仍在「正在打开…」——整屏米白，这就是你看到的白', 'warn')
  }
  await sleep(600)
  await measure(p, 'enter')

  const perf = await p.evaluate(() => performance.getEntriesByType('resource')
    .filter((e) => /\/api\/novels|NovelReadView|epub/.test(e.name))
    .map((e) => {
      const name = e.name.split('/').pop().split('?')[0]
      return `${name} · ${Math.round(e.duration)}ms · ${Math.round((e.transferSize || 0) / 1024)}KB`
    }))
  log('—— 本轮资源耗时 ——', 'data')
  for (const line of perf) log(line, 'data')

  setStatus('点页面唤菜单')
  log('点击页面中部 → 底栏应滑出', 'op')
  await p.mouse.click(W / 2, H * 0.5)
  await sleep(700)
  await measure(p, 'chrome')

  setStatus('打开目录')
  log('点底栏「目录」', 'op')
  const okToc = await p.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('.nrd-foot-tools button')).find((x) => /目录/.test(x.textContent || ''))
    if (!btn) return false
    btn.click()
    return true
  })
  if (!okToc) log('底栏按钮没找到 —— 底栏根本没在屏幕上', 'bad')
  await sleep(900)
  await measure(p, 'toc')

  setStatus('打开设置')
  await p.evaluate(() => { const x = document.querySelector('.nrd-sheet .nrd-ic'); x && x.textContent.includes('×') && x.click() })
  await sleep(500)
  await p.mouse.click(W / 2, H * 0.5)
  await sleep(500)
  await p.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('.nrd-foot-tools button')).find((x) => /设置/.test(x.textContent || ''))
    btn && btn.click()
  })
  await sleep(900)
  await measure(p, 'set')

  setStatus('完成（面板保持，可继续操作）')
  log('实测完成，画面保留', 'ok')
  // 保持浏览器活着，方便继续观察
  await new Promise(() => {})
}

server.listen(PORT, '127.0.0.1', () => {
  console.log(`LIVE PANEL: http://localhost:${PORT}`)
  run().catch((e) => {
    log('脚本异常：' + e.message.slice(0, 200), 'bad')
    setStatus('出错')
  })
})
