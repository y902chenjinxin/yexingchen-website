#!/usr/bin/env node
/**
 * 棋类游戏端到端取证（本地 dist + 生产 API 代理）
 *
 * 用法：node scripts/verify_games.js
 *
 * 做三件事：
 *   1. 起一个本地静态服务器托管 frontend/dist，并把 /api /uploads /music 反代到 yexingchen.cn
 *      （dist 是刚构建的新代码，API 用生产后端，避免本地没起 uvicorn）
 *   2. 拉 Chrome（--remote-debugging-port=9222）走 CDP
 *   3. 依次验证：
 *        - 五子棋：棋子是否落在交叉点、悔棋配额、提示语是否压棋盘、夜间主题对比度
 *        - 飞行棋：双人/三人/四人模式是否真能进入对局、在线邀请面板是否出现
 *      截图落在 artifacts/
 */
const WebSocket = require('websocket').w3cwebsocket
const http = require('http')
const https = require('https')
const fs = require('fs')
const path = require('path')
const { spawn } = require('child_process')

const ROOT = path.join(__dirname, '..')
const DIST = path.join(ROOT, 'frontend', 'dist')
const OUT_DIR = path.join(ROOT, 'artifacts')
const PORT = 4173
const PROXY_TARGET = 'https://yexingchen.cn'
const LOCAL = `http://127.0.0.1:${PORT}`
const EMAIL = 'admin@yexingchen.cn'
const PASSWORD = 'Chen@12345678'

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.mp4': 'video/mp4',
  '.webmanifest': 'application/manifest+json',
  '.map': 'application/json',
}

/* ---------------- 静态 + 反代 ---------------- */
function serveStatic(req, res) {
  let p = decodeURIComponent(req.url.split('?')[0])
  if (p === '/') p = '/index.html'
  let file = path.join(DIST, p)
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    // SPA 兜底：无扩展名的一律回 index.html
    if (!path.extname(p)) file = path.join(DIST, 'index.html')
    else { res.writeHead(404); res.end('not found'); return }
  }
  const ext = path.extname(file).toLowerCase()
  res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' })
  fs.createReadStream(file).pipe(res)
}

async function proxy(req, res) {
  try {
    const chunks = []
    for await (const c of req) chunks.push(c)
    const body = chunks.length ? Buffer.concat(chunks) : undefined
    const headers = { ...req.headers }
    delete headers.host
    delete headers.connection
    const r = await fetch(PROXY_TARGET + req.url, {
      method: req.method, headers, body, redirect: 'manual',
    })
    const out = {}
    r.headers.forEach((v, k) => { if (k.toLowerCase() !== 'content-encoding') out[k] = v })
    res.writeHead(r.status, out)
    res.end(Buffer.from(await r.arrayBuffer()))
  } catch (e) {
    res.writeHead(502, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ error: 'proxy fail: ' + e.message }))
  }
}

function startServer() {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      const u = req.url.split('?')[0]
      if (u.startsWith('/api/') || u.startsWith('/uploads/') || u.startsWith('/music/')) return proxy(req, res)
      serveStatic(req, res)
    })
    srv.listen(PORT, '127.0.0.1', () => { console.log(`[server] ${LOCAL} -> ${DIST}`); resolve(srv) })
  })
}

/* ---------------- CDP ---------------- */
let ws, msgId = 0
const consoleErrors = []
const failedRequests = []

function send(method, params = {}, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    const id = ++msgId
    ws.send(JSON.stringify({ id, method, params }))
    const handler = (event) => {
      const r = JSON.parse(event.data)
      if (r.id === id) { ws.removeEventListener('message', handler); resolve(r) }
    }
    ws.addEventListener('message', handler)
    setTimeout(() => { ws.removeEventListener('message', handler); reject(new Error('timeout ' + method)) }, timeoutMs)
  })
}

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let b = ''; res.on('data', c => b += c); res.on('end', () => resolve(JSON.parse(b)))
    }).on('error', reject)
  })
}

function chromeRunning() {
  return new Promise((resolve) => {
    const req = http.get('http://127.0.0.1:9222/json', () => resolve(true))
    req.on('error', () => resolve(false))
    req.setTimeout(1500, () => { req.destroy(); resolve(false) })
  })
}

async function launchChrome() {
  const paths = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  ]
  const exe = paths.find(p => fs.existsSync(p))
  if (!exe) throw new Error('Chrome not found')
  const dir = path.join(process.env.TEMP || '/tmp', 'chrome-verify-' + Date.now())
  console.log('[browser] launching Chrome')
  spawn(exe, ['--remote-debugging-port=9222', '--no-first-run', '--no-default-browser-check',
    '--window-size=1440,1000', `--user-data-dir=${dir}`], { detached: true, stdio: 'ignore' }).unref()
  await new Promise(r => setTimeout(r, 4500))
}

async function connect() {
  const targets = await getJson('http://127.0.0.1:9222/json')
  const page = targets.find(t => t.type === 'page') || targets[0]
  ws = new WebSocket(page.webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject })
  ws.onmessage = (event) => {
    const m = JSON.parse(event.data)
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
      consoleErrors.push((m.params.args || []).map(a => a.value || a.description || '').join(' '))
    }
    if (m.method === 'Runtime.exceptionThrown') {
      consoleErrors.push('EXCEPTION: ' + (m.params.exceptionDetails?.exception?.description || m.params.exceptionDetails?.text))
    }
    if (m.method === 'Network.responseReceived') {
      const { url, status } = m.params.response
      if (url.includes('/api/') && status >= 400) failedRequests.push(`${status} ${url}`)
    }
  }
  await send('Runtime.enable')
  await send('Page.enable')
  await send('Network.enable')
}

async function evalJs(expression) {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (r.result?.exceptionDetails) throw new Error('eval: ' + (r.result.exceptionDetails.exception?.description || ''))
  return r.result?.result?.value
}

async function shot(name) {
  // 截图偶发挂起/发暗（页面有常驻 CSS 动画 + 大 payload + 窗口不在前台时合成器给旧帧）
  // → 先 bringToFront，再重试 2 次并放宽超时
  try { await send('Page.bringToFront') } catch { /* 忽略 */ }
  await new Promise(r => setTimeout(r, 250))
  let r = null
  for (let i = 0; i < 2; i++) {
    try { r = await send('Page.captureScreenshot', { format: 'png' }, 60000); break }
    catch (e) { console.log(`  [warn] screenshot retry (${i + 1}): ${e.message}`) }
  }
  if (!r?.result?.data) { console.log('  [warn] screenshot failed:', name); return null }
  fs.mkdirSync(OUT_DIR, { recursive: true })
  const p = path.join(OUT_DIR, name)
  fs.writeFileSync(p, Buffer.from(r.result.data, 'base64'))
  console.log('  [shot]', p)
  return p
}

/** 轮询等待选择器出现（固定 sleep 不可靠） */
async function waitFor(sel, timeout = 15000) {
  const t0 = Date.now()
  while (Date.now() - t0 < timeout) {
    const ok = await evalJs(`!!document.querySelector(${JSON.stringify(sel)})`)
    if (ok) return true
    await new Promise(r => setTimeout(r, 300))
  }
  return false
}

/** 轮询等待条件表达式为真 */
async function waitUntil(expr, timeout = 10000) {
  const t0 = Date.now()
  while (Date.now() - t0 < timeout) {
    if (await evalJs(`!!(${expr})`)) return true
    await new Promise(r => setTimeout(r, 250))
  }
  return false
}

/** 等路由进场动画收尾：island-inner 无 transform、opacity=1（否则量到缩放中的坐标） */
async function settle(timeout = 6000) {
  await waitUntil(`(() => {
    const el = document.querySelector('.island-inner')
    if (!el) return true
    const cs = getComputedStyle(el)
    return cs.transform === 'none' && cs.opacity === '1'
  })()`, timeout)
  await new Promise(r => setTimeout(r, 300))
}

/** 按可见文字点按钮 */
async function clickText(sel, text) {
  return evalJs(`(() => {
    const els = [...document.querySelectorAll(${JSON.stringify(sel)})]
    const el = els.find(e => e.innerText && e.innerText.includes(${JSON.stringify(text)}))
    if (!el) return 'NOT_FOUND'
    el.click()
    return 'OK'
  })()`)
}

const results = []
function check(name, pass, detail) {
  results.push({ name, pass, detail })
  console.log(`  [${pass ? 'PASS' : 'FAIL'}] ${name}${detail ? ' — ' + detail : ''}`)
}

/* ---------------- 主流程 ---------------- */
(async () => {
  const server = await startServer()

  console.log('== 1. 生产 API 登录 ==')
  const login = await (await fetch(PROXY_TARGET + '/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  })).json()
  if (login.code !== 0 || !login.data?.token) throw new Error('login failed: ' + JSON.stringify(login).slice(0, 300))
  const token = login.data.token
  console.log('  token ok')

  if (!(await chromeRunning())) await launchChrome()
  await connect()

  await send('Page.navigate', { url: LOCAL + '/login' })
  await new Promise(r => setTimeout(r, 4000))
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`)

  console.log('== 2. 打开 /tool/games ==')
  consoleErrors.length = 0
  failedRequests.length = 0
  await send('Page.navigate', { url: LOCAL + '/tool/games' })
  await new Promise(r => setTimeout(r, 1500))
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`)
  await send('Page.reload')
  const okList = await waitFor('.gm-item', 20000)
  check('棋类游戏页加载（左栏出现）', okList)
  const theme = await evalJs(`JSON.stringify({ theme: document.documentElement.getAttribute('data-theme'), bg: getComputedStyle(document.body).backgroundColor })`)
  console.log('  theme:', theme)

  /* ================= 五子棋 ================= */
  console.log('\n== 3. 五子棋 ==')
  await clickText('.gm-item', '五子棋')
  await waitFor('.gm-modecard', 8000)
  const modeN = await evalJs(`document.querySelectorAll('.gm-modecard').length`)
  check('五子棋模式卡渲染', modeN >= 3, `count=${modeN}`)
  await clickText('.gm-modecard', '双人同屏')
  await waitFor('.gk-board', 10000)
  await settle()                                // 等进场动画收尾，再量坐标

  // 3.1 交叉点几何：格子中心是否与网格线重合
  //     注意：页面可能有祖先 transform/zoom，getBoundingClientRect 是缩放后坐标，
  //     而 getComputedStyle 的 px 是缩放前 —— 所以「格宽/线距」必须从 rect 实测反推。
  const geo = await evalJs(`(() => {
    const board = document.querySelector('.gk-board')
    const grid = document.querySelector('.gk-grid')
    const cells = [...document.querySelectorAll('.gk-cell')]
    if (!board || !grid || !cells.length) return { err: 'no board/grid/cells' }
    const g = grid.getBoundingClientRect()
    const n = parseFloat(getComputedStyle(board).getPropertyValue('--n'))
    const r0 = cells[0].getBoundingClientRect()
    const cellPx = r0.width                       // 实测格宽（已含缩放）
    // 网格线的真实周期 = 一个格宽（repeating-linear-gradient 每 var(--cell) 重复一次），
    // 不能用 grid.width/(n-1) —— 覆盖层宽度是 cell*(n-1)+1px（多出的 1px 给最后一条线留厚度），
    // 那样除会把线距算大 0.07px，末端累积成 1px 假偏差。
    const lineGap = cellPx
    // 覆盖层应恰好跨过 n-1 个格距（+1px 线厚）
    const spanOk = Math.abs(g.width - (cellPx * (n - 1) + 1)) < 1.5
    // 取 4 个角的格子中心，与「该位置应有的网格线交点」比较
    const picks = [0, n - 1, n * (n - 1), n * n - 1]
    let maxDev = 0
    for (const i of picks) {
      const r = cells[i].getBoundingClientRect()
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2
      const col = i % n, row = Math.floor(i / n)
      const lineX = g.left + col * lineGap
      const lineY = g.top + row * lineGap
      maxDev = Math.max(maxDev, Math.abs(cx - lineX), Math.abs(cy - lineY))
    }
    // 祖先 transform/zoom 诊断
    const chain = []
    for (let el = board; el && el !== document.documentElement; el = el.parentElement) {
      const cs = getComputedStyle(el)
      if (cs.transform !== 'none' || cs.zoom !== 'normal') chain.push(el.className + ' {transform:' + cs.transform + ',zoom:' + cs.zoom + '}')
    }
    return {
      n, cellCss: getComputedStyle(board).getPropertyValue('--cell').trim(),
      cellMeasured: Math.round(cellPx * 100) / 100,
      gridW: Math.round(g.width * 100) / 100,
      spanOk, maxDev: Math.round(maxDev * 100) / 100, chain,
    }
  })()`)
  check('棋子交叉点对齐（格心=线交点，偏差<1px）', geo.maxDev != null && geo.maxDev < 1,
    `cellCss=${geo.cellCss} cell实测=${geo.cellMeasured} gridW=${geo.gridW} maxDev=${geo.maxDev}px`)
  check('网格覆盖层恰好跨 n-1 个格距', geo.spanOk === true, `gridW=${geo.gridW} 期望≈${(geo.cellMeasured * (geo.n - 1) + 1).toFixed(2)}`)
  if (geo.chain?.length) console.log('  祖先缩放链:', JSON.stringify(geo.chain))

  // 3.2 落子后棋子圆心是否在线交点上
  const stoneGeo = await evalJs(`(() => {
    const board = document.querySelector('.gk-board')
    const grid = document.querySelector('.gk-grid')
    const cells = [...document.querySelectorAll('.gk-cell')]
    const n = parseFloat(getComputedStyle(board).getPropertyValue('--n'))
    const g = grid.getBoundingClientRect()
    const lineGap = g.width / (n - 1)
    // 点第 8 行第 8 列（中心区）
    const target = 7 * n + 7
    cells[target].click()
    return new Promise(res => setTimeout(() => {
      const st = cells[target].querySelector('.gk-stone')
      if (!st) return res({ err: 'stone not rendered' })
      const r = st.getBoundingClientRect()
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2
      const lineX = g.left + 7 * lineGap, lineY = g.top + 7 * lineGap
      res({ dev: Math.round(Math.max(Math.abs(cx - lineX), Math.abs(cy - lineY)) * 100) / 100 })
    }, 400))
  })()`)
  check('落子圆心落在交叉点（偏差<1px）', stoneGeo.dev != null && stoneGeo.dev < 1, `dev=${stoneGeo.dev}px`)

  // 3.3 提示语不压棋盘
  const overlap = await evalJs(`(() => {
    const board = document.querySelector('.gk-board').getBoundingClientRect()
    const hints = [...document.querySelectorAll('.gk-hint, .gk-locknote')]
      .filter(e => e.offsetParent !== null)
      .map(e => {
        const r = e.getBoundingClientRect()
        const hit = !(r.bottom <= board.top || r.top >= board.bottom || r.right <= board.left || r.left >= board.right)
        return { cls: e.className, top: Math.round(r.top), boardTop: Math.round(board.top), overlap: hit }
      })
    return hints
  })()`)
  const anyOverlap = Array.isArray(overlap) && overlap.some(h => h.overlap)
  check('提示语不覆盖棋盘', !anyOverlap, JSON.stringify(overlap))

  // 3.4 悔棋：配额 + 真的撤掉一手
  const before = await evalJs(`document.querySelectorAll('.gk-stone').length`)
  const quotaText = await evalJs(`document.querySelector('.gk-quota')?.innerText || ''`)
  await clickText('.gk-btn', '悔棋')
  await new Promise(r => setTimeout(r, 500))
  const after = await evalJs(`document.querySelectorAll('.gk-stone').length`)
  const quotaText2 = await evalJs(`document.querySelector('.gk-quota')?.innerText || ''`)
  check('悔棋生效（棋子数减少）', after < before, `${before} -> ${after}`)
  check('悔棋配额显示且递减', quotaText2 && quotaText2 !== quotaText, `"${quotaText}" -> "${quotaText2}"`)

  // 3.5 夜间主题对比度
  const night = await evalJs(`(() => {
    const b = document.querySelector('.gk-board')
    const hint = document.querySelector('.gk-hint')
    const cs = getComputedStyle(b)
    return {
      theme: document.documentElement.getAttribute('data-theme'),
      boardBgImage: cs.backgroundImage.slice(0, 90),
      boardBgColor: cs.backgroundColor,
      lineColor: cs.getPropertyValue('--gk-line').trim(),
      hintColor: hint ? getComputedStyle(hint).color : '',
      shellBg: getComputedStyle(document.querySelector('.gk-shell')).backgroundImage.slice(0, 70),
    }
  })()`)
  console.log('  night style:', JSON.stringify(night))
  const hasWood = /gradient/.test(night.boardBgImage || '') && night.boardBgImage !== 'none'
  check('夜间主题棋盘为深木纹实底（非透明）', hasWood, night.boardBgImage)
  check('夜间主题网格线可见（非空色值）', !!night.lineColor, `--gk-line=${night.lineColor}`)
  // 落一枚子并把棋盘滚到视野中央，便于看图核验
  await evalJs(`(() => {
    const cells = [...document.querySelectorAll('.gk-cell')]
    const n = 15
    cells[7 * n + 8]?.click()
    document.querySelector('.gk-board')?.scrollIntoView({ block: 'center' })
    return 1
  })()`)
  await new Promise(r => setTimeout(r, 1400))
  // 诊断：为何整页发暗 —— 查 island-inner 的透明度/变换 + 覆盖在棋盘中心的最上层元素
  const dim = await evalJs(`(() => {
    const inner = document.querySelector('.island-inner')
    const cs = inner ? getComputedStyle(inner) : null
    const b = document.querySelector('.gk-board')?.getBoundingClientRect()
    const top = b ? document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2) : null
    const fixed = [...document.querySelectorAll('body *')].filter(el => {
      const s = getComputedStyle(el)
      if (s.position !== 'fixed' && s.position !== 'absolute') return false
      const r = el.getBoundingClientRect()
      return r.width > innerWidth * 0.8 && r.height > innerHeight * 0.8 && s.visibility !== 'hidden'
    }).map(el => ({ cls: el.className?.toString().slice(0, 60), z: getComputedStyle(el).zIndex, op: getComputedStyle(el).opacity, bg: getComputedStyle(el).backgroundColor }))
    return JSON.stringify({
      innerOpacity: cs?.opacity, innerTransform: cs?.transform,
      innerFilter: cs?.filter, topEl: top ? top.className?.toString().slice(0, 60) : null,
      fixedOverlays: fixed,
    })
  })()`)
  console.log('  dim 诊断:', dim)
  await shot('games_gomoku.png')

  // 3.6 放大模式：左主棋盘 + 右辅栏（主次分明）+ 顶部头部不压棋局
  await clickText('.gm-op', '放大')
  await new Promise(r => setTimeout(r, 1000))
  await settle()
  const big = await evalJs(`(() => {
    const board = document.querySelector('.gk-board')
    const shell = document.querySelector('.gk-shell')
    const head = document.querySelector('.gm-head')
    const stage = document.querySelector('.gm-stage')
    if (!board || !shell || !head) return { err: 'missing el' }
    const b = board.getBoundingClientRect(), s = shell.getBoundingClientRect(), h = head.getBoundingClientRect()
    const ov = (r1, r2) => !(r1.bottom <= r2.top || r1.top >= r2.bottom || r1.right <= r2.left || r1.left >= r2.right)
    return {
      boardW: Math.round(b.width), boardH: Math.round(b.height),
      shellW: Math.round(s.width),
      sideBySide: s.left >= b.right - 2,
      shellOverBoard: ov(s, b),
      headOverShell: ov(h, s),
      headOverBoard: ov(h, b),
      stageScrollable: stage.scrollHeight > stage.clientHeight + 2,
    }
  })()`)
  check('放大：棋盘放大（>560）且辅栏移到右侧', big.sideBySide === true && big.boardW > 560, JSON.stringify(big))
  check('放大：头部不压玩家条/棋盘（无顶部凸出重叠）',
    big.headOverShell === false && big.headOverBoard === false, JSON.stringify(big))
  await shot('games_gomoku_big.png')

  /* ================= 飞行棋 ================= */
  console.log('\n== 4. 飞行棋 ==')
  await clickText('.gm-op', '返回列表')
  await new Promise(r => setTimeout(r, 600))
  await clickText('.gm-item', '飞行棋')
  await waitFor('.gm-modecard', 8000)
  const ludoModes = await evalJs(`[...document.querySelectorAll('.gm-modecard')].map(e => e.innerText.replace(/\\n/g,' '))`)
  check('飞行棋模式卡 = 双人/三人/四人/在线', Array.isArray(ludoModes) && ludoModes.length === 4, JSON.stringify(ludoModes))

  for (const [label, expect] of [['双人同屏', 2], ['三人同屏', 3], ['四人同屏', 4]]) {
    await clickText('.gm-modecard', label)
    const ok = await waitFor('.lb-board', 10000)
    await settle()
    await evalJs(`document.querySelector('.lb-board')?.scrollIntoView({ block: 'center' })`)
    await new Promise(r => setTimeout(r, 700))
    const info = await evalJs(`JSON.stringify({
      players: document.querySelectorAll('.lb-player').length,
      pieces: document.querySelectorAll('.lb-piece').length,
      trackCells: document.querySelectorAll('.lb-cell').length,
      hasLocknote: !!document.querySelector('.lb-locknote'),
    })`)
    const d = JSON.parse(info || '{}')
    check(`飞行棋「${label}」进入对局`, ok && d.players === expect, `${info}`)
    await shot(`games_ludo_${label}.png`)
    await clickText('.gm-op', '返回列表')
    await new Promise(r => setTimeout(r, 700))
    await clickText('.gm-item', '飞行棋')
    await waitFor('.gm-modecard', 8000)
  }

  // 在线邀请面板
  await clickText('.gm-modecard', '在线')
  await waitFor('.lb-online', 8000)
  // 家人列表是异步拉的，必须等 option 真的出现再判（否则误判「没有可邀请的账号」）
  const optOk = await waitUntil(`document.querySelectorAll('.lb-select option').length > 0`, 10000)
  const online = await evalJs(`JSON.stringify({
    panel: !!document.querySelector('.lb-online'),
    select: !!document.querySelector('.lb-select'),
    options: [...document.querySelectorAll('.lb-select option')].map(o => o.textContent.trim()),
    inviteBtn: !!document.querySelector('.lb-online .lb-btn.primary'),
    text: (document.querySelector('.lb-online')?.innerText || '').slice(0, 120)
  })`)
  const od = JSON.parse(online || '{}')
  check('飞行棋在线邀请面板可用', od.panel && od.inviteBtn, online)
  check('飞行棋在线可邀请家人（下拉有成员）', optOk && od.options?.length > 0, JSON.stringify(od.options))
  await shot('games_ludo_online.png')

  console.log('\n== 5. 控制台错误 ==')
  console.log(consoleErrors.length ? consoleErrors.slice(0, 20).join('\n') : '(none)')
  console.log('== 6. 失败请求 ==')
  console.log(failedRequests.length ? failedRequests.slice(0, 20).join('\n') : '(none)')

  const failed = results.filter(r => !r.pass)
  console.log(`\n===== 汇总：${results.length - failed.length}/${results.length} 通过 =====`)
  if (failed.length) failed.forEach(f => console.log('  FAIL:', f.name, '—', f.detail))

  ws.close()
  server.close()
  process.exit(failed.length ? 1 : 0)
})().catch((e) => { console.error('[FAIL]', e.stack || e.message); process.exit(1) })