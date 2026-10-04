#!/usr/bin/env node
/**
 * v2.44 牌类在线对局 · 端到端取证
 *
 * 用法：node scripts/verify_game_tables.js
 *   默认：本地静态服务器托管 frontend/dist（刚构建的新代码），/api 反代到生产；
 *   设 YX_PROXY=http://127.0.0.1:8000 可改指向本地后端（避免生产登录限流）。
 *   设 YX_TARGET=https://yexingchen.cn 则直接对生产站取证（带 SW / 登录态 / CDN）。
 *
 * 覆盖：
 *   1. 建房页渲染：游戏从 ?game= 取，底注三档 chip 渲染（曾因 STAKES/stakes 命名不一致整块空）
 *   2. 大富翁席位 chip（2–8 人）渲染
 *   3. 建房成功 → 跳到 /tool/games/table/<id> → 等待房 4 个席位
 *   4. 全程零控制台错误 / 零失败请求
 * 截图落 artifacts/
 */
const WebSocket = require('websocket').w3cwebsocket
const http = require('http')
const fs = require('fs')
const path = require('path')
const { spawn } = require('child_process')

const ROOT = path.join(__dirname, '..')
const DIST = path.join(ROOT, 'frontend', 'dist')
const OUT_DIR = path.join(ROOT, 'artifacts')
const PORT = 4175
const CDP_PORT = 9444
const PROXY_TARGET = process.env.YX_PROXY || 'https://yexingchen.cn'
const LOCAL = `http://127.0.0.1:${PORT}`
const TARGET = process.env.YX_TARGET || LOCAL

function loadCreds() {
  let email = process.env.YX_EMAIL
  let password = process.env.YX_PASSWORD
  if (!email || !password) {
    try {
      const seg = fs.readFileSync(path.join(ROOT, '..', '.secrets', 'local.env'), 'utf8')
        .split('#项目网站信息').pop()
      email = email || (seg.match(/账号[:：]\s*(\S+@\S+)/) || [])[1]
      password = password || (seg.match(/密码[:：]\s*(\S+)/) || [])[1]
    } catch { /* 读不到时交给调用方报错 */ }
  }
  return { email, password }
}

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.webp': 'image/webp', '.ico': 'image/x-icon', '.woff': 'font/woff', '.woff2': 'font/woff2',
  '.mp4': 'video/mp4', '.webmanifest': 'application/manifest+json', '.map': 'application/json',
}

function serveStatic(req, res) {
  let p = decodeURIComponent(req.url.split('?')[0])
  if (p === '/') p = '/index.html'
  let file = path.join(DIST, p)
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
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
    delete headers.host; delete headers.connection
    const r = await fetch(PROXY_TARGET + req.url, { method: req.method, headers, body, redirect: 'manual' })
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
    srv.listen(PORT, '127.0.0.1', () => { console.log(`[server] ${LOCAL} -> ${DIST}  (api -> ${PROXY_TARGET})`); resolve(srv) })
  })
}

let ws, msgId = 0
const consoleErrors = []
const failedRequests = []
const results = []

function check(name, pass, detail) {
  results.push({ name, pass, detail })
  console.log(`  [${pass ? 'PASS' : 'FAIL'}] ${name}${detail ? ' — ' + detail : ''}`)
}

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
    http.get(url, (res) => { let b = ''; res.on('data', c => b += c); res.on('end', () => resolve(JSON.parse(b))) }).on('error', reject)
  })
}

function chromeRunning() {
  return new Promise((resolve) => {
    const req = http.get(`http://127.0.0.1:${CDP_PORT}/json`, () => resolve(true))
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
  const dir = path.join(process.env.TEMP || '/tmp', 'chrome-verify-gt-' + Date.now())
  console.log('[browser] launching Chrome (headless=new)')
  spawn(exe, [`--remote-debugging-port=${CDP_PORT}`, '--no-first-run', '--no-default-browser-check',
    '--window-size=1600,1000', '--disable-backgrounding-occluded-windows',
    '--disable-renderer-backgrounding', '--disable-background-timer-throttling',
    '--disable-features=CalculateNativeWinOcclusion',
    '--headless=new', '--disable-gpu',
    `--user-data-dir=${dir}`], { detached: true, stdio: 'ignore' }).unref()
  for (let i = 0; i < 40; i++) { await new Promise(r => setTimeout(r, 500)); if (await chromeRunning()) return }
  throw new Error('Chrome 未就绪')
}

let connecting = null
async function connect() {
  const targets = await getJson(`http://127.0.0.1:${CDP_PORT}/json`)
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
  ws.onclose = () => { console.log('  [warn] CDP socket closed') }
  ws.onerror = () => { /* 关闭后由 ensureConn 重连 */ }
  await send('Runtime.enable'); await send('Page.enable'); await send('Network.enable')
}

async function ensureConn() {
  if (ws && ws.readyState === 1) return
  if (!connecting) {
    connecting = connect().catch((e) => { console.log('  [warn] reconnect failed:', e.message) })
      .finally(() => { connecting = null })
  }
  await connecting
  if (!ws || ws.readyState !== 1) throw new Error('CDP reconnect failed')
}

async function evalJs(expression) {
  await ensureConn()
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (r.result?.exceptionDetails) throw new Error('eval: ' + (r.result.exceptionDetails.exception?.description || ''))
  return r.result?.result?.value
}

/** 重毛玻璃/3D 面板在 1600×1000 软件渲染下整层栅格化极慢，captureScreenshot 会超时并拖断 CDP；
 *  自愈：第 2 次起降到 1280×800 再试（与 verify_card_games.js 同策略）。 */
const FALLBACK_METRICS = { width: 1280, height: 800 }
async function shot(name) {
  let r = null
  for (let i = 0; i < 3; i++) {
    const useMetrics = i >= 1 ? FALLBACK_METRICS : null
    try {
      await ensureConn()
      await send('Page.bringToFront')
      if (useMetrics) await send('Emulation.setDeviceMetricsOverride', { deviceScaleFactor: 1, mobile: false, ...useMetrics })
      await new Promise(x => setTimeout(x, 600))
      r = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false }, 45000)
      if (r?.result?.data) break
      r = null
    } catch (e) {
      console.log(`  [warn] screenshot retry ${i + 1}/3 (${name}): ${e.message}`)
      await new Promise(x => setTimeout(x, 900))
    } finally {
      if (useMetrics) { try { await send('Emulation.clearDeviceMetricsOverride') } catch { /* 忽略 */ } }
    }
  }
  if (!r?.result?.data) { console.log('  [warn] screenshot failed:', name); return null }
  try {
    fs.mkdirSync(OUT_DIR, { recursive: true })
    const p = path.join(OUT_DIR, name)
    fs.writeFileSync(p, Buffer.from(r.result.data, 'base64'))
    console.log('  [shot]', p)
    return p
  } catch (e) { console.log(`  [warn] screenshot write failed: ${e.message}`); return null }
}

async function waitFor(sel, timeout = 15000) {
  const t0 = Date.now()
  while (Date.now() - t0 < timeout) {
    if (await evalJs(`!!document.querySelector(${JSON.stringify(sel)})`)) return true
    await new Promise(r => setTimeout(r, 300))
  }
  return false
}

async function waitUntil(expr, timeout = 12000) {
  const t0 = Date.now()
  while (Date.now() - t0 < timeout) {
    if (await evalJs(`!!(${expr})`)) return true
    await new Promise(r => setTimeout(r, 250))
  }
  return false
}

async function settle(timeout = 6000) {
  await waitUntil(`(() => {
    const el = document.querySelector('.island-inner')
    if (!el) return true
    const cs = getComputedStyle(el)
    return cs.transform === 'none' && cs.opacity === '1'
  })()`, timeout)
  await new Promise(r => setTimeout(r, 300))
}

async function navigate(url) {
  await send('Page.navigate', { url })
  await new Promise(r => setTimeout(r, 800))
}

async function loginToken(email, password) {
  const r = await fetch(PROXY_TARGET + '/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const body = await r.json().catch(() => ({}))
  if (r.status !== 200 || body?.code !== 0) {
    throw new Error(`登录失败 HTTP ${r.status} ${JSON.stringify(body).slice(0, 200)}`)
  }
  return body.data.token
}

/** 直连后端（Node fetch）调 API，带 token；失败抛错。 */
async function apiJson(pathname, { method = 'GET', token, body } = {}) {
  const headers = {}
  if (token) headers.Authorization = `Bearer ${token}`
  if (body) headers['Content-Type'] = 'application/json'
  const r = await fetch(PROXY_TARGET + pathname, {
    method, headers, body: body ? JSON.stringify(body) : undefined,
  })
  const j = await r.json().catch(() => ({}))
  if (r.status >= 400 || (j && j.code !== undefined && j.code !== 0)) {
    throw new Error(`${method} ${pathname} -> ${r.status} ${JSON.stringify(j).slice(0, 200)}`)
  }
  return j.data
}

async function main() {
  let token = process.env.YX_TOKEN
  if (!token) {
    const { email, password } = loadCreds()
    if (!email || !password) throw new Error('未能在 ../.secrets/local.env 的「#项目网站信息」段找到账号/密码')
    token = await loginToken(email, password)
  }
  console.log('  [auth] token 就绪')

  // 清场：退出上次遗留的等待/进行中牌桌，保证等待房与开局断言互不污染
  // （否则房主同时挂在多张桌上时，新桌会被旧桌的 leave 连带解散，出现假失败）。
  try {
    const mine = await apiJson('/api/game/rooms/mine', { token })
    const actives = ((mine && mine.list) || []).filter(r => ['waiting', 'playing'].includes(r.status))
    for (const r of actives) {
      await apiJson(`/api/game/rooms/${r.id}/leave`, { method: 'POST', token }).catch(() => {})
    }
    if (actives.length) console.log(`  [clean] 退出遗留牌桌 ${actives.length} 张`)
  } catch { /* 清理失败不阻断 */ }

  let srv = null
  if (TARGET === LOCAL) srv = await startServer()
  else console.log(`[server] 直连目标 ${TARGET}（不经本地静态服务器）`)

  await launchChrome()
  await connect()

  // 在应用启动前注入 token（Page.addScriptToEvaluateOnNewDocument 对每个新文档生效）。
  // 否则首屏无登录态会被路由守卫踢到 /login，既产生 LoginView 懒加载竞态（CSS preload 报错），
  // 也多一次无谓跳转。
  await send('Page.addScriptToEvaluateOnNewDocument', {
    source: `try { localStorage.setItem('token', ${JSON.stringify(token)}) } catch (e) {}`,
  })

  /* ---------- 1) 掼蛋建房页：底注 chip ---------- */
  console.log('\n[1] 掼蛋建房页 · 底注档位')
  await navigate(`${TARGET}/tool/games/table/new?game=guandan`)
  await waitFor('.gtv-card')
  await settle()
  const gdTitle = await evalJs(`document.querySelector('.gtv-head-tx b')?.textContent || ''`)
  check('建房页标题含「掼蛋」', gdTitle.includes('掼蛋'), gdTitle)
  const stakeTexts = await evalJs(`[...document.querySelectorAll('.gtv-chip')].map(b => b.textContent.trim())`)
  check('底注三档渲染', Array.isArray(stakeTexts) && stakeTexts.length === 3, JSON.stringify(stakeTexts))
  check('含「100 豆」档', (stakeTexts || []).some(t => t.includes('100 豆')), JSON.stringify(stakeTexts))
  check('含「2000 豆」档', (stakeTexts || []).some(t => t.includes('2000 豆')), JSON.stringify(stakeTexts))
  await shot('gt_table_create_guandan.png')

  /* ---------- 2) 大富翁建房页：席位 chip ---------- */
  console.log('\n[2] 大富翁建房页 · 席位档位')
  await navigate(`${TARGET}/tool/games/table/new?game=monopoly`)
  await waitFor('.gtv-card')
  await settle()
  const allChips = await evalJs(`[...document.querySelectorAll('.gtv-chip')].map(b => b.textContent.trim())`)
  const seatChips = (allChips || []).filter(t => /^\d+ 人$/.test(t))
  check('大富翁席位档 2–8 共 7 档', seatChips.length === 7, JSON.stringify(seatChips))
  check('大富翁底注档同在', (allChips || []).some(t => t.includes('2000 豆')), JSON.stringify(allChips))
  await shot('gt_table_create_monopoly.png')

  /* ---------- 3) 建房 → 等待房 ---------- */
  console.log('\n[3] 掼蛋建房 → 等待房')
  await navigate(`${TARGET}/tool/games/table/new?game=guandan`)
  await waitFor('.gtv-card')
  await settle()
  // 点「建房并邀请」（无家人可邀也能建，空位开局时由机器人补）
  await evalJs(`(() => { const b=[...document.querySelectorAll('.gtv-btn')].find(x=>x.textContent.includes('建房并邀请')); if(b) b.click(); return !!b })()`)
  const routed = await waitUntil(`/\\/tool\\/games\\/table\\/\\d+/.test(location.pathname)`, 20000)
  check('建房后跳到 /tool/games/table/<id>', routed, await evalJs('location.pathname'))
  const seatCount = await waitUntil(`document.querySelectorAll('.gtv-seat').length === 4`, 15000)
  const seats = await evalJs(`[...document.querySelectorAll('.gtv-seat-name')].map(e=>e.textContent.trim())`)
  check('等待房渲染 4 个席位', seatCount, JSON.stringify(seats))
  const hasStart = await evalJs(`!![...document.querySelectorAll('.gtv-btn')].find(b=>b.textContent.includes('开始牌局'))`)
  check('房主可见「开始牌局」', hasStart)
  await settle()
  await shot('gt_table_waiting_room.png')

  /* ---------- 4) 在线对局：双人开局 → 牌桌投影渲染 ---------- */
  console.log('\n[4] 在线对局 · 双人开局 → 掼蛋牌桌投影')
  const B_EMAIL = process.env.YX_B_EMAIL || 'verify-b@local.test'
  const B_PWD = process.env.YX_B_PWD || 'Verify@12345678'
  const B_UID = Number(process.env.YX_B_UID) || 2
  // 允许直接注入第二席 token（生产只有 admin/lisa 两账号、无 lisa 密码时，
  // 用服务端密钥铸 JWT 注入，等价于 lisa 本人登录）。
  let tokenB = process.env.YX_B_TOKEN || null
  if (!tokenB) { try { tokenB = await loginToken(B_EMAIL, B_PWD) } catch { /* 生产无该账号则跳过 */ } }
  if (!tokenB) {
    console.log('  [skip] 第二席家人不可用（生产环境无该账号），跳过在线对局取证')
  } else {
    const room = await apiJson('/api/game/rooms', {
      method: 'POST', token,
      body: { game_key: 'guandan', invitee_user_ids: [B_UID], base_stake: 100 },
    })
    const rid = room.id
    await apiJson(`/api/game/rooms/${rid}/join`, { method: 'POST', token: tokenB })
    const started = await apiJson(`/api/game/rooms/${rid}/start`, { method: 'POST', token })
    check('在线掼蛋开局（status=playing · AI 补位 2 席）', started.status === 'playing', started.status)
    await navigate(`${TARGET}/tool/games/table/${rid}`)
    await waitFor('.gt-shell', 20000)
    await settle()
    const gd = await evalJs(`(() => ({
      shell: !!document.querySelector('.gt-shell'),
      hand: document.querySelectorAll('.gd-hand .gt-card').length,
      seats: document.querySelectorAll('.gt-seat').length,
      history: !!document.querySelector('.gd-history'),
      acts: [...document.querySelectorAll('.gd-actions .gt-btn')].map(b => b.textContent.trim()),
    }))()`)
    check('在线牌桌渲染（掼蛋投影态）', gd.shell === true, JSON.stringify(gd))
    check('在线投影：我方手牌 27 张', gd.hand === 27, `hand=${gd.hand}`)
    check('在线牌桌 3 席位 + 自己手牌区', gd.seats === 3, `seats=${gd.seats}`)
    check('在线牌桌含右侧出牌历史竖栏', gd.history === true, JSON.stringify(gd))
    await shot('gt_table_online_play.png')
  }

  /* ---------- 5) 控制台 / 请求健康 ---------- */
  console.log('\n[5] 控制台与网络')
  const realErrors = consoleErrors.filter(e => !/favicon|ResizeObserver/i.test(e))
  check('零控制台错误', realErrors.length === 0, realErrors.slice(0, 3).join(' | '))
  check('零失败 API 请求', failedRequests.length === 0, failedRequests.slice(0, 3).join(' | '))

  const failed = results.filter(r => !r.pass)
  console.log(`\n===== 结果：${results.length - failed.length}/${results.length} 通过 =====`)
  if (failed.length) { failed.forEach(f => console.log('  FAIL:', f.name, f.detail || '')); process.exitCode = 1 }

  if (srv) srv.close()
  process.exit(process.exitCode || 0)
}

main().catch((e) => { console.error('FATAL', e); process.exit(1) })
