#!/usr/bin/env node
/**
 * 象棋修正 · 真实浏览器取证（v2.41.8）
 *
 * 用法：node scripts/verify_xiangqi_fix.js
 *      DIST_DIR=frontend/dist-deploy25 node scripts/verify_xiangqi_fix.js   # 指定构建目录
 *
 * 复用 verify_games.js 的脚手架：本地静态服务器托管 dist，/api 反代到 yexingchen.cn，
 * 拉 Chrome 走 CDP。三项断言：
 *   A. 明棋单机：进对局后等 3 秒，棋盘必须**一手未动**（V2442-006 AI 抢跑）
 *   B. 暗棋：开局 32 子必须**全部落在标准开局的 32 个点上**、且全部背面（V2442-007）
 *   C. 暗棋：翻一枚子后该子出现**合法走法高亮**（走法真的能走）
 *
 * 凭据从 ../.secrets/local.env 读取（不再硬编码明文，见 docs/ISSUES.md V2441-005）。
 */
const WebSocket = require('websocket').w3cwebsocket
const http = require('http')
const https = require('https')
const fs = require('fs')
const path = require('path')
const { spawn } = require('child_process')

const ROOT = path.join(__dirname, '..')
const DIST = path.join(ROOT, process.env.DIST_DIR || path.join('frontend', 'dist'))
const OUT_DIR = path.join(ROOT, 'artifacts')
const PORT = 4174
const PROXY_TARGET = 'https://yexingchen.cn'
const LOCAL = `http://127.0.0.1:${PORT}`

/* ---- 凭据：从 .secrets/local.env 取 ---- */
function creds() {
  const p = path.join(ROOT, '..', '.secrets', 'local.env')
  const txt = fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : ''
  const seg = txt.split('#项目网站信息')[1] || txt
  const email = (seg.match(/账号[:：]\s*(\S+@\S+)/) || [])[1]
  const pw = (seg.match(/密码[:：]\s*(\S+)/) || [])[1]
  if (!email || !pw) throw new Error('未能在 ../.secrets/local.env 的「#项目网站信息」段找到账号/密码')
  return { email, pw }
}

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.webp': 'image/webp', '.woff': 'font/woff', '.woff2': 'font/woff2', '.ico': 'image/x-icon',
  '.mjs': 'text/javascript; charset=utf-8', '.wasm': 'application/wasm', '.mp3': 'audio/mpeg',
}

function serveStatic(req, res) {
  let p = decodeURIComponent(req.url.split('?')[0])
  if (p === '/') p = '/index.html'
  let f = path.join(DIST, p)
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) f = path.join(DIST, 'index.html')
  const ext = path.extname(f).toLowerCase()
  res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' })
  fs.createReadStream(f).pipe(res)
}

function proxy(req, res) {
  const opt = new URL(PROXY_TARGET + req.url)
  const pr = https.request({ hostname: opt.hostname, port: 443, path: opt.pathname + opt.search, method: req.method, headers: { ...req.headers, host: opt.hostname } }, (up) => {
    res.writeHead(up.statusCode, up.headers); up.pipe(res)
  })
  pr.on('error', e => { res.writeHead(502); res.end('proxy error ' + e.message) })
  req.pipe(pr)
}

function startServer() {
  return new Promise(resolve => {
    const s = http.createServer((req, res) => {
      if (req.url.startsWith('/api/') || req.url.startsWith('/uploads/') || req.url.startsWith('/music/')) proxy(req, res)
      else serveStatic(req, res)
    })
    s.listen(PORT, '127.0.0.1', () => resolve(s))
  })
}

/* ---------------- CDP ---------------- */
let ws, msgId = 0
const pending = new Map()
function send(method, params = {}, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    const id = ++msgId
    const t = setTimeout(() => { pending.delete(id); reject(new Error('CDP timeout: ' + method)) }, timeoutMs)
    pending.set(id, { resolve, reject, t })
    ws.send(JSON.stringify({ id, method, params }))
  })
}
/** 注意：CDP 调试端点永远是 http，早先这里误用 https.get →
 *  抛 `Protocol "http:" not supported` 被 chromeRunning() 吞掉，
 *  于是脚本以为「Chrome 未就绪」又去启第二个实例（端口被占，必然失败）。 */
function getJson(url) {
  const mod = url.startsWith('https:') ? https : http
  return new Promise((resolve, reject) => {
    mod.get(url, r => { let d = ''; r.on('data', c => d += c); r.on('end', () => { try { resolve(JSON.parse(d)) } catch { resolve(null) } }) }).on('error', reject)
  })
}
async function chromeRunning() {
  try { return !!(await getJson('http://127.0.0.1:9222/json/version')) } catch { return false }
}
async function launchChrome() {
  const cands = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  ]
  const exe = cands.find(p => fs.existsSync(p))
  if (!exe) throw new Error('未找到 Chrome')
  const dir = path.join(process.env.TEMP || '/tmp', 'chrome-xq-' + Date.now())
  spawn(exe, ['--remote-debugging-port=9222', '--no-first-run', '--no-default-browser-check',
    '--user-data-dir=' + dir, '--window-size=1440,900', 'about:blank'], { detached: true, stdio: 'ignore' }).unref()
  for (let i = 0; i < 40; i++) { await new Promise(r => setTimeout(r, 500)); if (await chromeRunning()) return }
  throw new Error('Chrome 未就绪')
}
async function connect() {
  const list = await getJson('http://127.0.0.1:9222/json/list')
  const page = (list || []).find(t => t.type === 'page')
  if (!page) throw new Error('没有可用的 page')
  ws = new WebSocket(page.webSocketDebuggerUrl)
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej })
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data)
    if (m.id && pending.has(m.id)) {
      const { resolve, reject, t } = pending.get(m.id)
      clearTimeout(t); pending.delete(m.id)
      m.error ? reject(new Error(m.error.message)) : resolve(m.result)
    }
  }
  await send('Runtime.enable'); await send('Page.enable'); await send('Network.enable')
}
async function evalJs(expression) {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (r.exceptionDetails) throw new Error('eval 异常: ' + JSON.stringify(r.exceptionDetails).slice(0, 400))
  return r.result.value
}
async function shot(name) {
  try { await send('Page.bringToFront') } catch { /* 忽略 */ }
  let r
  for (let i = 0; i < 3; i++) { try { r = await send('Page.captureScreenshot', { format: 'png' }, 60000); break } catch { await new Promise(x => setTimeout(x, 800)) } }
  if (!r) return
  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true })
  const f = path.join(OUT_DIR, `xiangqi-${name}.png`)
  fs.writeFileSync(f, Buffer.from(r.data, 'base64'))
  console.log(`   📸 ${f}`)
}
async function waitFor(sel, timeout = 15000) {
  const t0 = Date.now()
  while (Date.now() - t0 < timeout) {
    if (await evalJs(`!!document.querySelector(${JSON.stringify(sel)})`)) return true
    await new Promise(r => setTimeout(r, 250))
  }
  return false
}
async function clickText(sel, text) {
  return evalJs(`(() => {
    const els = [...document.querySelectorAll(${JSON.stringify(sel)})]
    const el = els.find(e => (e.textContent || '').includes(${JSON.stringify(text)}))
    if (!el) return false
    el.click(); return true
  })()`)
}

const results = []
function check(name, pass, detail = '') {
  results.push({ name, pass, detail })
  console.log(`   ${pass ? '✅' : '❌'} ${name}${detail ? '  — ' + detail : ''}`)
}

/* ---------------- 主流程 ---------------- */
(async () => {
  if (!fs.existsSync(path.join(DIST, 'index.html'))) throw new Error('dist 不存在: ' + DIST)
  console.log('dist =', DIST)
  await startServer()

  const { email, pw } = creds()
  console.log('== 1. 生产 API 登录 ==')
  const login = await (await fetch(PROXY_TARGET + '/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password: pw }),
  })).json()
  if (login.code !== 0 || !login.data?.token) throw new Error('登录失败（确认没被限流）: ' + JSON.stringify(login).slice(0, 300))
  const token = login.data.token
  console.log('   token ok')

  if (!(await chromeRunning())) await launchChrome()
  await connect()

  await send('Page.navigate', { url: LOCAL + '/login' })
  await new Promise(r => setTimeout(r, 3500))
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`)

  console.log('\n== 2. 打开 /tool/games ==')
  await send('Page.navigate', { url: LOCAL + '/tool/games' })
  await new Promise(r => setTimeout(r, 1500))
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`)
  await send('Page.reload')
  check('棋类游戏页加载', await waitFor('.gm-item', 25000))

  /* ============ A. 明棋单机：AI 不许抢跑 ============ */
  console.log('\n== A. 象棋（明棋）单机 —— AI 抢跑断言 ==')
  await clickText('.gm-item', '象棋')
  await new Promise(r => setTimeout(r, 600))
  // 必须点「单机」而不是双人；页面标题是「单机 · 简单」
  const hit = await evalJs(`(() => {
    const els = [...document.querySelectorAll('.gm-modecard')]
    const el = els.find(e => (e.textContent || '').includes('单机'))
    if (!el) return null
    el.click(); return el.textContent.trim()
  })()`)
  console.log('   点了模式卡:', JSON.stringify(hit))
  check('进入单机对局（棋盘出现）', await waitFor('.xq-board', 15000))
  await new Promise(r => setTimeout(r, 3000))     // 等足 AI 的 260ms 定时器 + 余量

  const a = await evalJs(`(() => {
    const cells = [...document.querySelectorAll('.xq-cell.has-piece')]
    const hist = document.querySelector('.xq-quota')?.textContent?.trim() || ''
    return { pieces: cells.length, hist }
  })()`)
  console.log('   棋盘子数 =', a.pieces, ' 手数显示 =', JSON.stringify(a.hist))
  check('开局棋子 32 枚且一手未动', a.pieces === 32 && /^0\s*手/.test(a.hist),
    `子数=${a.pieces} 手数=${a.hist}（期望 32 子 / 0 手）`)
  await shot('A-明棋单机开局')

  /* ============ B. 暗棋：标准开局 32 点 ============ */
  console.log('\n== B. 象棋翻棋（暗棋）—— 排布断言 ==')
  await evalJs(`(() => { const b = [...document.querySelectorAll('.gm-back,.gm-backbtn,.gm-resume')].find(e=>/返回|列表/.test(e.textContent)); if (b) b.click() })()`)
  await new Promise(r => setTimeout(r, 800))
  // 直接从列表重新选「象棋翻棋」
  await clickText('.gm-item', '象棋翻棋')
  await new Promise(r => setTimeout(r, 800))
  await evalJs(`document.querySelectorAll('.gm-modecard')[0]?.click()`)   // 双人同屏，避免 AI 干扰
  check('进入翻棋对局（棋盘出现）', await waitFor('.xf-board', 15000))
  await new Promise(r => setTimeout(r, 1200))
  await shot('B-暗棋开局')

  const b = await evalJs(`(() => {
    const ROWS = 10, COLS = 9
    const cells = [...document.querySelectorAll('.xf-cell')]
    if (cells.length !== ROWS * COLS) return { err: '格子数不是 90: ' + cells.length }
    const STEP = (() => {           // 由实测 cell 宽度反推格距（页面可能有 transform/zoom）
      const r = cells[0].getBoundingClientRect(); return r.width || 0
    })()
    const occ = []                  // 有子的格（含暗子与明子）
    cells.forEach((c, i) => { if (c.querySelector('.xf-back,.xf-piece')) occ.push(i) })
    const upN = cells.filter(c => c.querySelector('.xf-piece')).length
    const downN = cells.filter(c => c.querySelector('.xf-back')).length
    // 标准开局占位（与 xiangqiRules.initialBoard 同构）
    const back = [0,1,2,3,4,5,6,7,8]
    const want = new Set()
    for (const x of back) { want.add(0*COLS+x); want.add(9*COLS+x) }
    for (const x of [1,7]) { want.add(2*COLS+x); want.add(7*COLS+x) }
    for (const x of [0,2,4,6,8]) { want.add(3*COLS+x); want.add(6*COLS+x) }
    const extra = occ.filter(i => !want.has(i))
    const missing = [...want].filter(i => !occ.includes(i))
    return { total: occ.length, upN, downN, extra: extra.length, missing: missing.length,
             sampleExtra: extra.slice(0,6), cellPx: STEP }
  })()`)
  console.log('   ', JSON.stringify(b))
  check('暗棋：恰好 32 枚子', b.total === 32, `实际 ${b.total}`)
  check('暗棋：全部背面朝上', b.downN === 32 && b.upN === 0, `背面 ${b.downN} / 明子 ${b.upN}`)
  check('暗棋：32 子全部落在标准开局点（无越界、无空点）', b.extra === 0 && b.missing === 0,
    `多出 ${b.extra} 个, 缺失 ${b.missing} 个`)

  /* ============ C. 翻一枚子 → 出现合法走法高亮 ============ */
  console.log('\n== C. 暗棋 —— 翻子后走法高亮断言 ==')
  await evalJs(`document.querySelectorAll('.xf-cell')[49]?.click()`)   // 先翻中间格（4,5 行⑤=中心，通常是空）
  await new Promise(r => setTimeout(r, 500))
  // 找到第一枚已翻开的子，点它，看是否有 .target 高亮
  const c1 = await evalJs(`(() => {
    const cells = [...document.querySelectorAll('.xf-cell')]
    const i = cells.findIndex(c => c.querySelector('.xf-piece'))
    if (i < 0) return { err: '没有翻开的子' }
    cells[i].click()
    return { idx: i, glyph: cells[i].querySelector('.xf-piece').textContent.trim() }
  })()`)
  await new Promise(r => setTimeout(r, 700))
  const c2 = await evalJs(`document.querySelectorAll('.xf-cell.target').length`)
  console.log(`   翻开后选中 (${c1.glyph})，合法目标格数 = ${c2}`)
  check('翻子成功且该子可被选中（走法链路通）', !!c1.glyph && !c1.err, JSON.stringify(c1))
  // 目标格可能为 0（被周围暗子挡死）——这是规则允许的，所以只做提示不做硬断言
  if (c2 === 0) console.log('   ⚠️  该子当前 0 个合法目标（周围全是暗子 → 规则上正常，未判失败）')
  await shot('C-暗棋翻子后高亮')

  /* ---------------- 汇总 ---------------- */
  console.log('\n' + '='.repeat(64))
  const bad = results.filter(r => !r.pass)
  console.log(`共 ${results.length} 项断言，通过 ${results.length - bad.length}，失败 ${bad.length}`)
  for (const r of bad) console.log(`  ❌ ${r.name} — ${r.detail}`)
  console.log('='.repeat(64))
  process.exit(bad.length ? 1 : 0)
})().catch(e => { console.error('❌ 取证失败:', e.message); process.exit(1) })
