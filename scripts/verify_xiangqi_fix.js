#!/usr/bin/env node
/**
 * 象棋修正 · 真实浏览器取证（v2.41.8）
 *
 * 用法：node scripts/verify_xiangqi_fix.js
 *      DIST_DIR=frontend/dist-deploy25 node scripts/verify_xiangqi_fix.js   # 指定构建目录
 *      SITE=https://yexingchen.cn node scripts/verify_xiangqi_fix.js        # 直接打生产（部署后取证）
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
/** 传了 SITE 就跳过本地静态服务器、直接验收生产（部署后取证用）。 */
const SITE = (process.env.SITE || '').replace(/\/$/, '')
const BASE = SITE || LOCAL

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
  if (!SITE) await startServer()

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

  await send('Page.navigate', { url: BASE + '/login' })
  await new Promise(r => setTimeout(r, 3500))
  // 清 SW + CacheStorage：否则可能被旧 SW 托着看旧界面（假阴性/假阳性都发生过）
  await evalJs(`(async () => {
    try { const rs = await navigator.serviceWorker.getRegistrations(); await Promise.all(rs.map(x => x.unregister())) } catch {}
    try { const ks = await caches.keys(); await Promise.all(ks.map(n => caches.delete(n))) } catch {}
    return 'cleared'
  })()`)
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`)

  console.log('\n== 2. 打开 /tool/games ==')
  await send('Page.navigate', { url: BASE + '/tool/games' })
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

  /* ============ A0. 明棋：兵在自己半场只有「向前」一个落点（不许因改暗棋而松动） ============ */
  console.log('\n== A0. 明棋兵卒仍守原规则（只有前进） ==')
  const p0 = await evalJs(`(() => {
    const cells = [...document.querySelectorAll('.xq-cell')]
    const i = cells.findIndex((c, k) => (k / 9 | 0) === 6 && /兵/.test(c.textContent))
    if (i < 0) return { err: '第 7 行（y=6）找不到红兵' }
    cells[i].click()
    return { i }
  })()`)
  await new Promise(r => setTimeout(r, 400))
  const p1 = await evalJs(`(() => {
    const cells = [...document.querySelectorAll('.xq-cell')]
    const t = cells.map((c, k) => (c.classList.contains('target') ? k : -1)).filter(k => k >= 0)
    return { targets: t, forward: ${p0.i} - 9 }
  })()`)
  console.log(`   红兵 @${p0.i} → 落点 ${JSON.stringify(p1.targets)}（前进= ${p1.forward}）`)
  check('明棋红兵在自家半场只有「向前」1 个落点', p1.targets.length === 1 && p1.targets[0] === p1.forward,
    `落点=${JSON.stringify(p1.targets)}`)
  await evalJs(`(() => { const c = document.querySelector('.xq-cell.sel'); if (c) c.click() })()`)

  /* ============ A2. 反向断言：玩家走一步后 AI 必须应一手 ============
     光验「开局不动」不够 —— 修过头会把 AI 彻底修死，所以必须证明它还下棋。 */
  console.log('\n== A2. 玩家走一步 → AI 应一手（防「把 AI 修死」） ==')
  const mv = await evalJs(`(() => {
    const cells = [...document.querySelectorAll('.xq-cell')]
    const i = cells.findIndex(c => c.querySelector('.xq-piece.red'))
    if (i < 0) return { err: '没找到红子' }
    cells[i].click()
    return { i, g: cells[i].querySelector('.xq-piece').textContent.trim() }
  })()`)
  await new Promise(r => setTimeout(r, 500))
  const tg = await evalJs(`(() => {
    const cells = [...document.querySelectorAll('.xq-cell')]
    const t = cells.find(c => c.classList.contains('target'))
    if (!t) return -1
    const idx = cells.indexOf(t); t.click(); return idx
  })()`)
  await new Promise(r => setTimeout(r, 2600))          // 等 AI 的 260ms 定时器 + 余量
  const a2 = await evalJs(`(() => {
    const hist = document.querySelector('.xq-quota')?.textContent?.trim() || ''
    const active = document.querySelector('.xq-player.active')?.textContent?.trim() || ''
    return { hist, active, pieces: document.querySelectorAll('.xq-cell.has-piece').length }
  })()`)
  console.log(`   玩家走「${mv.g}」→ 落点 ${tg}；之后 手数=${a2.hist} 轮到=${a2.active}`)
  check('玩家落子后 AI 应一手（手数=2）', /^2\s*手/.test(a2.hist), `手数=${a2.hist}（期望 2 手）`)
  check('AI 应手后轮到玩家（不锁死）', /红方/.test(a2.active), `active=${a2.active}`)
  await shot('A2-明棋玩家走一步后')

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

  /* ============ C. 翻两枚 → 回合回到先翻者 → 选明子出现高亮 ============
     注意「双人同屏」下翻子后**回合换人**，所以必须翻两枚让回合转回来，
     再去点第一枚明子才可能被选中（只翻一枚就点 → 必然「选不中」，是规则不是 bug）。 */
  console.log('\n== C. 暗棋 —— 翻子后选中与走法高亮断言 ==')
  const flipAt = async () => {
    const i = await evalJs(`(() => {
      const cells = [...document.querySelectorAll('.xf-cell')]
      return cells.findIndex(c => c.querySelector('.xf-back'))
    })()`)
    await evalJs(`document.querySelectorAll('.xf-cell')[${i}]?.click()`)
    await new Promise(r => setTimeout(r, 700))
    return i
  }
  const iA = await flipAt()
  const iB = await flipAt()
  const c1 = await evalJs(`(() => {
    const cells = [...document.querySelectorAll('.xf-cell')]
    const g = i => cells[i]?.querySelector('.xf-piece')?.textContent?.trim() || ''
    return { upN: cells.filter(c => c.querySelector('.xf-piece')).length,
             downN: cells.filter(c => c.querySelector('.xf-back')).length,
             a: g(${iA}), b: g(${iB}),
             bSide: (cells[${iB}]?.querySelector('.xf-piece')?.className || '') }
  })()`)
  console.log(`   翻开 A(${iA})="${c1.a}"  B(${iB})="${c1.b}"  明子 ${c1.upN} / 暗子 ${c1.downN}`)
  check('翻子成功（两次翻棋各翻出一枚明子）', c1.upN === 2 && c1.downN === 30,
    `明子 ${c1.upN} / 暗子 ${c1.downN}（期望 2 / 30）`)

  await evalJs(`document.querySelectorAll('.xf-cell')[${iA}]?.click()`)   // 回合已转回先翻者
  await new Promise(r => setTimeout(r, 700))
  const c2 = await evalJs(`(() => {
    const cells = [...document.querySelectorAll('.xf-cell')]
    const el = cells[${iA}]
    return { cellClass: el.className, targets: document.querySelectorAll('.xf-cell.target').length }
  })()`)
  console.log(`   点回第一枚明子 → cellClass="${c2.cellClass}" 合法目标 ${c2.targets} 格`)
  check('翻出的明子可被选中（走法链路通）', c2.cellClass.includes('sel'), `cellClass=${c2.cellClass}`)
  // 目标为 0 是规则允许的（周围全暗子挡死），只提示不判失败
  if (c2.targets === 0) console.log('   ⚠️  该子当前 0 个合法目标（周围全是暗子 → 规则上正常）')
  await shot('C-暗棋翻子后高亮')

  /* ============ C2. 暗棋兵/卒 = 四向一格（含横走 / 后退，V2442-010） ============
     断言口径：兵/卒的落点集合 === 「4 邻格里可走的那些格」（空 or 已翻开的敌子）。
     旧规则（只能前进 + 过河才横走）下，自家半场的兵不会有横走/后退高亮 → 这条会红。 */
  console.log('\n== C2. 暗棋兵/卒 —— 四向一格（可横走、可后退） ==')
  let pawnIdx = -1
  for (let k = 0; k < 12 && pawnIdx < 0; k++) {
    pawnIdx = await evalJs(`(() => {
      const cells = [...document.querySelectorAll('.xf-cell')]
      return cells.findIndex(c => /[兵卒]/.test(c.querySelector('.xf-piece')?.textContent || ''))
    })()`)
    if (pawnIdx < 0) await flipAt()
  }
  let pawn = null
  for (let k = 0; k < 4 && pawnIdx >= 0; k++) {
    pawn = await evalJs(`(() => {
      const cells = [...document.querySelectorAll('.xf-cell')]
      const i = ${pawnIdx}
      const el = cells[i]
      el.click()
      const p = el.querySelector('.xf-piece')
      if (!p) return { err: '该格没有明子' }
      const mine = p.className.includes('red') ? 'red' : 'black'
      const x = i % 9, y = (i / 9) | 0
      const nb = []
      if (x > 0) nb.push(i - 1)
      if (x < 8) nb.push(i + 1)
      if (y > 0) nb.push(i - 9)
      if (y < 9) nb.push(i + 9)
      const movable = nb.filter(j => {
        const q = cells[j]
        const qp = q.querySelector('.xf-piece')
        if (qp) return !qp.className.includes(mine)          // 已翻开的敌子可吃
        return !q.querySelector('.xf-back')                  // 空格可走；暗子挡路不可吃
      })
      const targets = nb.filter(j => cells[j].classList.contains('target'))
      const back = mine === 'red' ? i + 9 : i - 9            // 红兵朝上走 → 后退=y+1
      const side = [i - 1, i + 1]
      return { idx: i, glyph: p.textContent.trim(), sel: el.classList.contains('sel'),
               movable: movable.slice().sort((a, b) => a - b),
               targets: targets.slice().sort((a, b) => a - b),
               backOk: movable.includes(back), backHit: targets.includes(back),
               sideOk: side.some(s => movable.includes(s)), sideHit: side.some(s => targets.includes(s)) }
    })()`)
    if (pawn && pawn.sel) break
    await flipAt()                                            // 不是本方颜色 → 翻一手换手再试
  }
  console.log('   兵/卒 @' + pawnIdx + ' 「' + (pawn && pawn.glyph) + '」'
    + '  可走邻格 ' + JSON.stringify(pawn && pawn.movable)
    + '  高亮 ' + JSON.stringify(pawn && pawn.targets)
    + '  | 后退可选=' + (pawn && pawn.backOk) + ' 后退高亮=' + (pawn && pawn.backHit)
    + ' 横向可选=' + (pawn && pawn.sideOk) + ' 横向高亮=' + (pawn && pawn.sideHit))
  check('暗棋兵/卒可被选中（能验证）', !!(pawn && pawn.sel), JSON.stringify(pawn && pawn.movable))
  check('暗棋兵/卒落点 == 四邻可走格（不受河界/前进限制）',
    !!(pawn && JSON.stringify(pawn.movable) === JSON.stringify(pawn.targets)),
    `可走 ${JSON.stringify(pawn && pawn.movable)} vs 高亮 ${JSON.stringify(pawn && pawn.targets)}`)
  if (pawn && pawn.backOk) check('暗棋兵/卒「后退」在可选时确实高亮', pawn.backHit === true, `后退高亮=${pawn.backHit}`)
  else console.log('   ⚠️  本局这枚兵/卒的后退格被占，未取到「后退」样本（引擎层 probe_pawn.mjs 已断言四向）')
  await shot('C2-暗棋兵卒四向')

  /* ============ D. （SITE 模式）生产 SW 版本与本次构建一致 ============ */
  if (SITE) {
    console.log('\n== D. 生产 SW 版本一致性 ==')
    const localSw = fs.readFileSync(path.join(DIST, 'sw.js'), 'utf8')
    const wantV = (localSw.match(/xuanhuang-v(\d+)/) || [])[1]
    const remoteTxt = await (await fetch(SITE + '/sw.js')).text()
    const gotV = (remoteTxt.match(/xuanhuang-v(\d+)/) || [])[1]
    console.log(`   本地构建 SW = v${wantV}，生产 SW = v${gotV}`)
    check('生产 SW 版本 == 本次构建版本', !!wantV && wantV === gotV, `本地 v${wantV} / 生产 v${gotV}`)
  }

  /* ---------------- 汇总 ---------------- */
  console.log('\n' + '='.repeat(64))
  const bad = results.filter(r => !r.pass)
  console.log(`共 ${results.length} 项断言，通过 ${results.length - bad.length}，失败 ${bad.length}`)
  for (const r of bad) console.log(`  ❌ ${r.name} — ${r.detail}`)
  console.log('='.repeat(64))
  process.exit(bad.length ? 1 : 0)
})().catch(e => { console.error('❌ 取证失败:', e.message); process.exit(1) })
