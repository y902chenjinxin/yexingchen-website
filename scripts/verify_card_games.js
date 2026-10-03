#!/usr/bin/env node
/**
 * 棋牌三件套端到端取证（本地 dist + 生产 API 代理）
 *
 * 用法：node scripts/verify_card_games.js
 *
 * 本地静态服务器托管 frontend/dist（刚构建的新代码），/api 反代到 yexingchen.cn；
 * 拉 Chrome（--remote-debugging-port=9222）走 CDP，依次验证：
 *   1. 掼蛋：单人 3AI 能进桌、手牌 27 张、四个操作键在、能出牌且 AI 应招
 *   2. 四川麻将：定缺面板出现、选缺后进对局、手牌 13/14 张、能出牌
 *   3. 大富翁：52 格棋盘、2 人席、掷骰后日志推进
 *   4. 个人中心「积分中心」面板渲染（积分/欢乐豆/签到按钮）
 * 截图落在 artifacts/
 */
const WebSocket = require('websocket').w3cwebsocket
const http = require('http')
const fs = require('fs')
const path = require('path')
const { spawn } = require('child_process')

const ROOT = path.join(__dirname, '..')
const DIST = path.join(ROOT, 'frontend', 'dist')
const OUT_DIR = path.join(ROOT, 'artifacts')
const PORT = 4174
/** 专用调试端口：避免复用别的取证脚本留下的、未带「抗后台节流」参数的 Chrome 实例
 *  （那种实例下 captureScreenshot 会挂起）。 */
const CDP_PORT = 9333
const PROXY_TARGET = 'https://yexingchen.cn'
const LOCAL = `http://127.0.0.1:${PORT}`
/** 设 YX_TARGET=https://yexingchen.cn 可跳过本地 dist，直接对生产站取证
 *  （验证带 Service Worker / 登录态 / CDN 的真实链路，而非本地构建产物）。 */
const TARGET = process.env.YX_TARGET || LOCAL

/** 凭据读取：优先环境变量 YX_EMAIL / YX_PASSWORD，否则读 <repo>/../.secrets/local.env。
 *  ⚠️ 不要把生产账号密码写进脚本 —— 本仓库是公开仓库（见 docs/ISSUES.md V2441-005）。 */
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
    srv.listen(PORT, '127.0.0.1', () => { console.log(`[server] ${LOCAL} -> ${DIST}`); resolve(srv) })
  })
}

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
  const dir = path.join(process.env.TEMP || '/tmp', 'chrome-verify-card-' + Date.now())
  console.log('[browser] launching Chrome (headless=new)')
  // 牌桌有 backdrop-filter 毛玻璃 + 常驻 CSS 动画：有头窗口一旦被遮挡，合成器就被节流，
  // captureScreenshot 会挂起并拖断 CDP（实测 guandan/大富翁必挂）。headless=new 离屏渲染
  // 不受遮挡影响，配合 --disable-gpu 截图稳定在百毫秒级。
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

/** 断线自动重连：截图挂起常伴随 socket 掉线，不能让后续断言整体中断 */
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

/** 截图：完全非致命（失败只告警，不中断流程）。
 *  headless=new 离屏渲染，不需要再注入「降载样式」——早期有头版本给全页 * 元素加
 *  animation-play-state/backdrop-filter !important 会触发整页重排重绘，反而让
 *  captureScreenshot 更易超时，故已移除。
 *  重毛玻璃/3D 牌桌（麻将对局、大富翁棋盘）在 1600×1000 软件渲染下整层栅格化极慢，
 *  captureScreenshot 会超时并拖断 CDP；自愈策略：第 2 次起降到 1280×800 再试。 */
const FALLBACK_METRICS = { width: 1280, height: 800 }
async function shot(name, metrics) {
  let r = null
  for (let i = 0; i < 3; i++) {
    const useMetrics = metrics || (i >= 1 ? FALLBACK_METRICS : null)
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
  if (!r?.result?.data) { console.log('  [warn] screenshot failed (finally):', name); return null }
  try {
    fs.mkdirSync(OUT_DIR, { recursive: true })
    const p = path.join(OUT_DIR, name)
    fs.writeFileSync(p, Buffer.from(r.result.data, 'base64'))
    console.log('  [shot]', p)
    return p
  } catch (e) {
    console.log(`  [warn] screenshot write failed (${name}): ${e.message}`)
    return null
  }
}

async function waitFor(sel, timeout = 15000) {
  const t0 = Date.now()
  while (Date.now() - t0 < timeout) {
    if (await evalJs(`!!document.querySelector(${JSON.stringify(sel)})`)) return true
    await new Promise(r => setTimeout(r, 300))
  }
  return false
}

async function waitUntil(expr, timeout = 10000) {
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

async function clickText(sel, text) {
  return evalJs(`(() => {
    const els = [...document.querySelectorAll(${JSON.stringify(sel)})]
    const el = els.find(e => e.innerText && e.innerText.includes(${JSON.stringify(text)}))
    if (!el) return 'NOT_FOUND'
    el.click(); return 'OK'
  })()`)
}

const results = []
function check(name, pass, detail) {
  results.push({ name, pass, detail })
  console.log(`  [${pass ? 'PASS' : 'FAIL'}] ${name}${detail ? ' — ' + detail : ''}`)
}

async function backToList() {
  await clickText('.gm-op', '返回列表')
  await new Promise(r => setTimeout(r, 700))
}

async function openGame(label, modeLabel) {
  await clickText('.gm-item', label)
  await waitFor('.gm-modecard', 8000)
  await clickText('.gm-modecard', modeLabel)
  await new Promise(r => setTimeout(r, 900))
  await settle()
}

/* ---------------- 主流程 ---------------- */
(async () => {
  const server = TARGET === LOCAL ? await startServer() : null
  if (!server) console.log(`[target] 直连 ${TARGET}（跳过本地静态服务器）`)

  console.log('== 1. 生产 API 登录 ==')
  const { email: EMAIL, password: PASSWORD } = loadCreds()
  if (!EMAIL || !PASSWORD) throw new Error('未能在 ../.secrets/local.env 的「#项目网站信息」段找到账号/密码')
  const login = await (await fetch(PROXY_TARGET + '/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
  })).json()
  if (login.code !== 0 || !login.data?.token) throw new Error('login failed: ' + JSON.stringify(login).slice(0, 300))
  const token = login.data.token
  console.log('  token ok')

  if (!(await chromeRunning())) await launchChrome()
  await connect()

  await send('Page.navigate', { url: TARGET + '/login' })
  await new Promise(r => setTimeout(r, 4000))
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`)

  console.log('== 2. 打开 /tool/games ==')
  consoleErrors.length = 0; failedRequests.length = 0
  await send('Page.navigate', { url: TARGET + '/tool/games' })
  await new Promise(r => setTimeout(r, 1500))
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`)
  await send('Page.reload')
  const okList = await waitFor('.gm-item', 20000)
  check('棋类游戏页加载（左栏出现）', okList)
  const items = await evalJs(`[...document.querySelectorAll('.gm-item')].map(e => e.innerText.split('\\n')[0])`)
  console.log('  游戏列表:', JSON.stringify(items))
  check('列表含掼蛋 / 四川麻将 / 大富翁',
    ['掼蛋', '四川麻将', '大富翁'].every(n => (items || []).some(t => t.includes(n))), JSON.stringify(items))

  /* ================= 掼蛋 ================= */
  console.log('\n== 3. 掼蛋（单人 · 3 AI） ==')
  await openGame('掼蛋', '单人')
  const gdOk = await waitFor('.gt-shell.gd', 10000)
  await settle()
  const gd = await evalJs(`(() => {
    const hand = [...document.querySelectorAll('.gd-hand .gt-card')]
    const btns = [...document.querySelectorAll('.gd-actions .gt-btn')].map(b => ({ t: b.innerText.trim(), dis: b.disabled }))
    return JSON.stringify({
      shell: !!document.querySelector('.gt-shell.gd'),
      hand: hand.length,
      actions: btns,
      seats: document.querySelectorAll('.gt-seat').length,
      title: document.querySelector('.gt-title')?.innerText || '',
    })
  })()`)
  const g = JSON.parse(gd || '{}')
  check('掼蛋进入对局（牌桌渲染）', gdOk && g.shell === true, gd)
  check('掼蛋手牌 27 张', g.hand === 27, `hand=${g.hand}`)
  check('掼蛋四个操作键（出牌/不要/提示/重选）',
    Array.isArray(g.actions) && g.actions.length === 4, JSON.stringify(g.actions))
  check('掼蛋四席位（对家/左家/右家 + 自己手牌区）', g.seats === 3, `seats=${g.seats}`)
  await shot('card_guandan_start.png')

  // 出牌：若轮到自己，点「提示」→「出牌」；否则等 AI 先走
  const acted = await evalJs(`(() => {
    const btns = [...document.querySelectorAll('.gd-actions .gt-btn')]
    const hint = btns.find(b => b.innerText.includes('提示'))
    const play = btns.find(b => b.innerText.includes('出牌'))
    if (hint && !hint.disabled) { hint.click(); return 'hinted' }
    if (play && !play.disabled) { play.click(); return 'played' }
    return 'not-my-turn'
  })()`)
  console.log('  首个动作:', acted)
  if (acted === 'hinted') {
    await new Promise(r => setTimeout(r, 400))
    const played = await evalJs(`(() => {
      const play = [...document.querySelectorAll('.gd-actions .gt-btn')].find(b => b.innerText.includes('出牌'))
      if (play && !play.disabled) { play.click(); return true }
      return false
    })()`)
    console.log('  提示后出牌:', played)
  }
  // 等出牌记录出现（自己或 AI 走的）
  const playedOk = await waitUntil(`document.querySelectorAll('.gd-center-cards .gt-card').length > 0`, 15000)
  const gd2 = await evalJs(`JSON.stringify({
    centerCards: document.querySelectorAll('.gd-center-cards .gt-card').length,
    log: [...document.querySelectorAll('.gd-center-log span')].map(s => s.innerText).slice(0, 3),
    hand: document.querySelectorAll('.gd-hand .gt-card').length,
    centerText: (document.querySelector('.gd-center')?.innerText || '').slice(0, 120),
  })`)
  check('掼蛋有出牌发生（中央出牌区有牌）', playedOk, gd2)
  await shot('card_guandan_play.png')
  await backToList()

  /* ================= 四川麻将 ================= */
  console.log('\n== 4. 四川麻将（单人 · 3 AI） ==')
  await openGame('四川麻将', '单人')
  const mjOk = await waitFor('.gt-shell.mj', 10000)
  await settle()
  const dingque = await evalJs(`JSON.stringify({
    over: !!document.querySelector('.gt-over'),
    head: document.querySelector('.gt-over-card h3')?.innerText || '',
    btns: [...document.querySelectorAll('.gt-over .gt-actions .gt-btn')].map(b => b.innerText.trim()),
  })`)
  const dq = JSON.parse(dingque || '{}')
  check('麻将进入定缺阶段（面板出现）', mjOk && dq.over === true && dq.head.includes('定缺'), dingque)
  await shot('card_mahjong_dingque.png')

  const chosen = await evalJs(`(() => {
    const b = document.querySelector('.gt-over .gt-actions .gt-btn')
    if (!b) return 'NOT_FOUND'
    const label = b.innerText.trim(); b.click(); return label
  })()`)
  console.log('  选定缺门:', chosen)
  // 等定缺面板消失、进入 playing
  const playingOk = await waitUntil(`!document.querySelector('.gt-over')`, 8000)
  await new Promise(r => setTimeout(r, 800))
  const mj = await evalJs(`JSON.stringify({
    over: !!document.querySelector('.gt-over'),
    hand: document.querySelectorAll('.mj-hand .gt-tile').length,
    seats: document.querySelectorAll('.mj-seat').length,
    discards: document.querySelectorAll('.mj-discards .gt-tile').length,
    tingbar: !!document.querySelector('.mj-tingbar'),
    actions: [...document.querySelectorAll('.mj-actions .gt-btn')].map(b => b.innerText.trim()),
  })`)
  const m = JSON.parse(mj || '{}')
  check('麻将选缺后进入对局（定缺面板收起）', playingOk && m.over === false, mj)
  check('麻将手牌 13~14 张', m.hand >= 13 && m.hand <= 14, `hand=${m.hand}`)
  check('麻将听牌提示条渲染', m.tingbar === true, `tingbar=${m.tingbar}`)
  check('麻将操作区有「出牌」', Array.isArray(m.actions) && m.actions.some(t => t.includes('出牌')), JSON.stringify(m.actions))
  await shot('card_mahjong_play.png')

  // 尝试出牌：点一张手牌 → 出牌。
  // ⚠️ 点牌是同步的，但 Vue 把 selId 刷进 DOM 是微任务 —— 必须在两次 evaluate 之间留一拍，
  //    否则读到的 btn.disabled 还是「未选中」时的旧值，会误判成「出牌键不可用」。
  const mjPick = await evalJs(`(() => {
    const tiles = [...document.querySelectorAll('.mj-hand .gt-tile.pickable')]
    if (!tiles.length) return 'no-pickable'
    tiles[0].click(); return 'picked'
  })()`)
  await new Promise(r => setTimeout(r, 400))
  const mjAct = mjPick !== 'picked' ? mjPick : await evalJs(`(() => {
    const btn = [...document.querySelectorAll('.mj-actions .gt-btn')].find(b => b.innerText.includes('出牌'))
    if (!btn) return 'no-btn'
    if (btn.disabled) return 'btn-disabled'
    btn.click(); return 'discarded'
  })()`)
  console.log('  出牌动作:', mjAct)
  await new Promise(r => setTimeout(r, 1200))
  const mjAfter = await evalJs(`JSON.stringify({
    discards: document.querySelectorAll('.mj-discards .gt-tile').length,
    hand: document.querySelectorAll('.mj-hand .gt-tile').length,
  })`)
  console.log('  出牌后:', mjAfter)
  check('麻将出牌链路可用（点牌→出牌）', mjAct === 'discarded' || mjAct === 'no-pickable', `${mjAct} ${mjAfter}`)
  await shot('card_mahjong_after.png')
  await backToList()

  /* ================= 大富翁 ================= */
  console.log('\n== 5. 大富翁（2 人） ==')
  await openGame('大富翁', '2 人')
  const mpOk = await waitFor('.gt-shell.mp', 10000)
  await settle()
  const mp = await evalJs(`JSON.stringify({
    shell: !!document.querySelector('.gt-shell.mp'),
    cells: document.querySelectorAll('.mp-cell').length,
    players: document.querySelectorAll('.mp-players .mp-pcard').length,
    tokens: document.querySelectorAll('.mp-tok').length,
    ops: [...document.querySelectorAll('.mp-ops .gt-btn')].map(b => b.innerText.trim()),
  })`)
  const p = JSON.parse(mp || '{}')
  check('大富翁进入对局（棋盘渲染）', mpOk && p.shell === true, mp)
  check('大富翁 52 格棋盘', p.cells === 52, `cells=${p.cells}`)
  check('大富翁 2 人席位', p.players === 2, `players=${p.players}`)
  check('大富翁有「掷骰前进」键', Array.isArray(p.ops) && p.ops.some(t => t.includes('掷骰')), JSON.stringify(p.ops))
  await shot('card_monopoly_start.png', { width: 1100, height: 700 })

  const rolled = await evalJs(`(() => {
    const b = [...document.querySelectorAll('.mp-ops .gt-btn')].find(x => x.innerText.includes('掷骰'))
    if (!b) return 'no-btn'
    if (b.disabled) return 'disabled'
    b.click(); return 'rolled'
  })()`)
  console.log('  掷骰:', rolled)
  const movedOk = await waitUntil(`(() => {
    const logs = [...document.querySelectorAll('.mp-log-row')].map(e => e.innerText)
    return logs.length > 0 && logs.some(t => /掷|点|前进|买入|租金|经过起点/.test(t))
  })()`, 12000)
  const mpAfter = await evalJs(`JSON.stringify({
    dice: [...document.querySelectorAll('.mp-die')].map(d => d.innerText),
    log: [...document.querySelectorAll('.mp-log-row')].map(e => e.innerText).slice(-4),
  })`)
  check('大富翁掷骰后日志推进', movedOk, mpAfter)
  await shot('card_monopoly_roll.png', { width: 1100, height: 700 })
  await backToList()

  /* ================= 积分中心 ================= */
  console.log('\n== 6. 个人中心 · 积分中心 ==')
  await send('Page.navigate', { url: TARGET + '/profile' })
  await new Promise(r => setTimeout(r, 1500))
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`)
  await send('Page.reload')
  const gwOk = await waitFor('.gw', 20000)
  // 积分中心在「基本信息/界面偏好」之下，默认不在首屏 —— 截图前先滚到可见处
  await evalJs(`(() => { const el=document.querySelector('.gw'); if(el) el.scrollIntoView({block:'center'}); return true })()`)
  await new Promise(r => setTimeout(r, 1000))
  const gw = await evalJs(`JSON.stringify({
    card: !!document.querySelector('.gw-card'),
    head: document.querySelector('.gw-head h2')?.innerText || '',
    bals: [...document.querySelectorAll('.gw-bal b')].map(b => b.innerText),
    ops: [...document.querySelectorAll('.gw-ops .gw-btn')].map(b => b.innerText.trim().split('\\n')[0]),
  })`)
  const w = JSON.parse(gw || '{}')
  check('个人中心渲染「积分中心」面板', gwOk && w.card === true && w.head.includes('积分中心'), gw)
  check('积分中心显示积分与欢乐豆余额', Array.isArray(w.bals) && w.bals.length === 2, JSON.stringify(w.bals))
  check('积分中心有签到/兑换/赠送操作', Array.isArray(w.ops) && w.ops.length >= 3, JSON.stringify(w.ops))
  await shot('card_wallet.png')

  console.log('\n== 7. 控制台错误 ==')
  console.log(consoleErrors.length ? consoleErrors.slice(0, 20).join('\n') : '(none)')
  console.log('== 8. 失败请求 ==')
  console.log(failedRequests.length ? failedRequests.slice(0, 20).join('\n') : '(none)')

  const failed = results.filter(r => !r.pass)
  console.log(`\n===== 汇总：${results.length - failed.length}/${results.length} 通过 =====`)
  if (failed.length) failed.forEach(f => console.log('  FAIL:', f.name, '—', f.detail))

  ws.close(); if (server) server.close()
  process.exit(failed.length ? 1 : 0)
})().catch((e) => { console.error('[FAIL]', e.stack || e.message); process.exit(1) })
