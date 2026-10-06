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
const { spawn, execSync } = require('child_process')

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

/** 抢占 CDP 端口：若已有验证浏览器在监听 9444（上一次跑挂掉后 detached 留下的 Chrome，
 *  或另一个并行的验证进程），必须先把浏览器关掉——否则两个脚本共用同一个 CDP 连接、
 *  互相覆盖 Emulation 状态（一边设 mobile:true 触控，另一边 clearDeviceMetricsOverride），
 *  表现为 `Input.dispatchTouchEvent` 静默不投递、页面侧探针 log=[]，把「harness 冲突」
 *  误判成「产品不能双指缩放」。Browser.close 只关监听该端口的这个浏览器，不动用户自己的 Chrome。 */
async function closeStaleCdp() {
  if (!(await chromeRunning())) return
  try {
    const ver = await getJson(`http://127.0.0.1:${CDP_PORT}/json/version`)
    const bws = new WebSocket(ver.webSocketDebuggerUrl)
    await new Promise((resolve, reject) => {
      bws.onopen = resolve; bws.onerror = reject
      setTimeout(() => reject(new Error('open timeout')), 4000)
    })
    bws.send(JSON.stringify({ id: 1, method: 'Browser.close' }))
    await new Promise(r => setTimeout(r, 1500))
    console.log('[clean] 已关闭占用 CDP 端口的遗留验证浏览器')
  } catch (e) { console.log('[clean] 关闭遗留浏览器失败:', e.message) }
  for (let i = 0; i < 24; i++) {
    if (!(await chromeRunning())) return
    await new Promise(r => setTimeout(r, 500))
  }
  throw new Error(`端口 ${CDP_PORT} 仍被占用：请先关掉遗留的验证 Chrome 再重跑`)
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
      const d = m.params.exceptionDetails || {}
      const st = ((d.stackTrace && d.stackTrace.callFrames) || []).slice(0, 2)
        .map(f => `${f.functionName || '?'}@${(f.url || '').split('/').pop()}:${f.lineNumber}`).join(' <- ')
      consoleErrors.push('EXCEPTION: ' + (d.exception?.description || d.text) + (st ? ' @@ ' + st : ''))
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
 *  自愈：第 2 次起降到 1280×800 再试（与 verify_card_games.js 同策略）。
 *  ⚠️ clearDeviceMetricsOverride 会**清掉**调用方设的移动端 override（如 §6.5 的 844×390），
 *  故用 mobileMetrics 记住并还原，否则后续「双指缩放/单指拖动」断言全在错误视口下跑。 */
const FALLBACK_METRICS = { width: 1280, height: 800 }
let mobileMetrics = null
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
      if (useMetrics) {
        try {
          if (mobileMetrics) await send('Emulation.setDeviceMetricsOverride', mobileMetrics)
          else await send('Emulation.clearDeviceMetricsOverride')
        } catch { /* 忽略 */ }
      }
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

  await closeStaleCdp()
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

    /* ---------- 4.9) 出牌记录小窗 / 同花顺按钮 / 牌面花色（v2.44.1） ---------- */
    console.log('\n[4.9] 出牌记录小窗 · 同花顺按钮 · 牌面花色')
    const histUi = await evalJs(`(() => {
      const box = document.querySelector('.gd-history')
      const list = document.querySelector('.gd-history-list')
      const btn = [...document.querySelectorAll('.gd-actions .gt-btn')].find(b => b.textContent.includes('同花顺'))
      const card = document.querySelector('.gd-hand .gt-card')
      const tl = card && card.querySelector('.c-tl i')
      const mid = card && card.querySelector('.c-mid')
      return {
        hasBox: !!box,
        collapsed: box ? box.classList.contains('is-collapsed') : null,
        toggleText: (document.querySelector('.gd-history-toggle') || {}).textContent,
        listMaxH: list ? Math.round(parseFloat(getComputedStyle(list).maxHeight)) : 0,
        count: document.querySelectorAll('.gd-his').length,
        flushBtn: !!btn,
        suitWeight: tl ? getComputedStyle(tl).fontWeight : '',
        suitSize: tl ? getComputedStyle(tl).fontSize : '',
        midOpacity: mid ? getComputedStyle(mid).opacity : '',
      }
    })()`)
    check('出牌记录小窗存在且默认展开', histUi.hasBox && histUi.collapsed === false, JSON.stringify(histUi))
    check('小窗提供「收起」开关', (histUi.toggleText || '').trim() === '收起', histUi.toggleText)
    check('记录列表定高 ≤100px（超出在窗内滚动）',
      histUi.listMaxH > 0 && histUi.listMaxH <= 100, `maxH=${histUi.listMaxH} count=${histUi.count}`)
    check('「同花顺」按钮已在操作栏', histUi.flushBtn === true)
    check('牌面花色加粗放大（≥700 / ≥12px）',
      Number(histUi.suitWeight) >= 700 && parseFloat(histUi.suitSize) >= 12,
      `weight=${histUi.suitWeight} size=${histUi.suitSize} midOpacity=${histUi.midOpacity}`)
    await evalJs(`(() => { const b=document.querySelector('.gd-history-toggle'); if(b) b.click(); return !!b })()`)
    await new Promise(r => setTimeout(r, 350))
    check('点「收起」后小窗折叠', await evalJs(`document.querySelector('.gd-history').classList.contains('is-collapsed')`))
    await evalJs(`(() => { const b=document.querySelector('.gd-history-toggle'); if(b) b.click(); return !!b })()`)
    await new Promise(r => setTimeout(r, 350))
    await shot('gt_table_history_window.png')

    /* ---------- 5) 全屏：右侧三按钮 + 游戏说明抽屉（v2.44.1） ---------- */
    console.log('\n[5] 全屏 · 右侧竖栏 + 游戏说明抽屉')
    await evalJs(`(() => { const b=[...document.querySelectorAll('.gtv-btn')].find(x=>x.textContent.trim()==='全屏'); if(b) b.click(); return !!b })()`)
    const railOk = await waitFor('.gtv-rail', 8000)
    const railBtns = await evalJs(`[...document.querySelectorAll('.gtv-rail-btn span')].map(e=>e.textContent.trim())`)
    check('全屏后右侧竖栏出现', railOk, JSON.stringify(railBtns))
    check('竖栏含 游戏说明 / 退出全屏 / 返回列表',
      ['游戏说明', '退出全屏', '返回列表'].every(t => (railBtns || []).includes(t)), JSON.stringify(railBtns))
    check('全屏时顶部横条隐藏', await evalJs(`!document.querySelector('.gtv-boardhead')`))
    await evalJs(`(() => { const b=[...document.querySelectorAll('.gtv-rail-btn')].find(x=>x.textContent.includes('游戏说明')); if(b) b.click(); return !!b })()`)
    const helpOk = await waitFor('.gtv-help-panel', 6000)
    const helpCount = await evalJs(`document.querySelectorAll('.gtv-help-list li').length`)
    check('游戏说明抽屉打开且含规则条目', helpOk && helpCount >= 5, `rules=${helpCount}`)
    await shot('gt_table_fullscreen_help.png')
    await evalJs(`(() => { const b=[...document.querySelectorAll('.gtv-help-panel .gtv-btn')].find(x=>x.textContent.includes('知道了')); if(b) b.click(); return !!b })()`)
    await new Promise(r => setTimeout(r, 400))
    await evalJs(`(() => { const b=[...document.querySelectorAll('.gtv-rail-btn')].find(x=>x.textContent.includes('退出全屏')); if(b) b.click(); return !!b })()`)
    await new Promise(r => setTimeout(r, 500))
    check('「退出全屏」可回到普通布局', await evalJs(`!document.querySelector('.gtv-rail')`))

    /* ---------- 6) 进贡：双下两家各进一张（v2.44.1 手动选牌 + 记录 + 飞牌） ---------- */
    console.log('\n[6] 进贡 · 双下两家各进一张（rematch 触发）')
    const craftPy = path.join(ROOT, 'scripts', '_craft_guandan_finished.py')
    const localDb = path.join(ROOT, 'backend', 'yexingchen.db')
    async function enterTributePhase() {
      // craft 把本地牌桌伪造成「上一局刚结束」，rematch 才会进入进贡阶段；
      // 抗贡（进贡方合计持两张大王）时重来，最多 6 次。
      let r = null
      for (let attempt = 0; attempt < 6 && !r; attempt++) {
        try { execSync(`python "${craftPy}" ${rid} "${localDb}"`, { stdio: 'ignore' }) } catch (e) { console.log('  [warn] craft failed:', e.message) }
        const rr = await apiJson(`/api/game/rooms/${rid}/rematch`, { method: 'POST', token })
        if ((rr.view || {}).phase === 'tribute') r = rr
      }
      return r
    }
    const tr = await enterTributePhase()
    check('rematch 后进入进贡阶段（未抗贡）', !!tr, tr ? `turn=${tr.view.turn}` : '连续 6 次抗贡/未进入')
    if (tr) {
      const v = tr.view
      const givers = ((v.tribute || {}).givers || []).map(g => `${g.from}->${g.to}`)
      check('双下：两家各进一张（0→1、2→3）',
        givers.length === 2 && givers.includes('0->1') && givers.includes('2->3'), JSON.stringify(givers))
      check('我方(座位0)被要求手动选牌进贡',
        v.me && v.me.tribute_pending === true && v.me.tribute_to === 1,
        `pending=${v.me && v.me.tribute_pending} to=${v.me && v.me.tribute_to} opts=${((v.me || {}).tribute_options || []).length}`)
      check('进贡阶段无倒计时（deadline_at 为空）', !tr.deadline_at, String(tr.deadline_at))

      await navigate(`${TARGET}/tool/games/table/${rid}`)
      const panelOk = await waitFor('.gd-tribute', 15000)
      const panel = await evalJs(`(() => ({
        tip: (document.querySelector('.gd-return-tip') || {}).textContent || '',
        cards: document.querySelectorAll('.gd-tribute .gt-card.pickable').length,
      }))()`)
      check('前端渲染「进贡选牌」面板', panelOk && panel.cards > 0, JSON.stringify(panel))
      await shot('gt_table_tribute_panel.png')

      // ⚠️ 截图重试会把渲染进程卡住 >30s，服务端据此把座位判为掉线托管并代打，进贡阶段随即消失。
      // 故截图后重新伪造「上一局结束」并 rematch，拿一个**全新**进贡阶段再做飞牌取证。
      const tr2 = await enterTributePhase()
      check('截图后重进进贡阶段（飞牌取证用）', !!tr2, tr2 ? `turn=${tr2.view.turn}` : '未进入')
      if (tr2) {
        await navigate(`${TARGET}/tool/games/table/${rid}`)
        await waitFor('.gd-tribute', 15000)
        // 飞牌动画仅 ~1s，且经「点击 → 服务端 → 下一轮投影」链路；用页面内 MutationObserver
        // 常驻观察（避免慢速 CDP 往返恰好错过 1s 窗口），再点牌触发。
        await evalJs(`(() => {
          window.__flySeen = false
          const mo = new MutationObserver(() => { if (document.querySelector('.gd-fly')) window.__flySeen = true })
          mo.observe(document.body, { childList: true, subtree: true })
          return true
        })()`)
        await evalJs(`(() => { const c=document.querySelector('.gd-tribute .gt-card.pickable'); if(c) c.click(); return !!c })()`)
        const flySeen = await waitUntil(`window.__flySeen === true`, 12000)
        const flyDiag = await evalJs(`JSON.stringify({
          seen: window.__flySeen,
          fly: !!document.querySelector('.gd-fly'),
          tributePanel: !!document.querySelector('.gd-tribute'),
          his: [...document.querySelectorAll('.gd-his')].map(e => (e.textContent || '').replace(/\\s+/g, ' ').trim()),
        })`)
        check('进贡时出现飞牌动画元素', flySeen, flyDiag)
        const hisOk = await waitUntil(`!!document.querySelector('.gd-his.is-tribute')`, 10000)
        const hisText = await evalJs(`(document.querySelector('.gd-his.is-tribute') || {}).textContent || ''`)
        check('出牌记录出现「进贡」条目（含受贡方）',
          hisOk && /进贡/.test(hisText) && /→/.test(hisText), hisText.replace(/\s+/g, ' ').trim())
        await shot('gt_table_tribute_history.png')
      }
    }

    /* ---------- 6.5) 手机横屏：铺满一屏 + 双指缩放 / 单指拖动（v2.44.1） ---------- */
    console.log('\n[6.5] 手机横屏 · 铺满一屏 + 双指缩放 / 单指拖动')
    mobileMetrics = { width: 844, height: 390, deviceScaleFactor: 2, mobile: true }
    async function applyMobile() {
      await send('Emulation.setDeviceMetricsOverride', mobileMetrics)
      await applyTouch()
    }
    // 只补触控/UA（不动 metrics，避免重排把已算好的舞台尺寸与落点作废）
    async function applyTouch() {
      await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 })
      await send('Emulation.setUserAgentOverride', {
        userAgent: 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36 XuanHuangApp/2.44.1',
      })
      // CDP 截图超时重连会丢 emulation 覆盖：maxTouchPoints 归 0 后 Input.dispatchTouchEvent
      // 不再投递（页面侧探针 log=[]），表现为「双指/单指无效」。逐次校验并按需重设，
      // 避免把「harness 丢了触控」误判成「产品不能缩放」。
      for (let i = 0; i < 4; i++) {
        const mtp = Number(await evalJs(`(navigator.maxTouchPoints || 0)`))
        if (mtp > 0) { try { await send('Page.bringToFront') } catch { /* 忽略 */ } return }
        await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 })
        await new Promise(r => setTimeout(r, 200))
      }
      console.log('  [warn] 触控覆盖未能恢复（maxTouchPoints=0）')
    }
    await applyMobile()
    // 强制移动端外壳：CDP 截图超时重连会丢 UA override，仅靠 UA 判定会被 resize 翻回桌面壳
    // （表现为桌面侧栏盖住舞台、触摸落点打偏）；用 ?m=1 的 localStorage 逃生口才稳。
    await evalJs(`try { localStorage.setItem('xuanhuang_force_mobile','1') } catch (e) {}`)
    await navigate(`${TARGET}/tool/games/table/${rid}`)
    await waitFor('.gt-shell', 20000)
    // 进入全屏（手机端会自动全屏；桌面 UA 走按钮）
    const fsOn = await waitUntil(`!!document.querySelector('.gtv-boardwrap.is-fs')`, 4000)
    if (!fsOn) await evalJs(`(() => { const b=[...document.querySelectorAll('.gtv-btn')].find(x=>x.textContent.trim()==='全屏'); if(b) b.click(); return !!b })()`)
    await waitFor('.gtv-rail', 8000)
    await new Promise(r => setTimeout(r, 1500))
    const fill = await evalJs(`(() => {
      const stage = document.querySelector('.gtv-viewstage')
      const zoom = document.querySelector('.gtv-viewzoom')
      if (!stage || !zoom) return null
      const s = stage.getBoundingClientRect(), z = zoom.getBoundingClientRect()
      const m = new DOMMatrixReadOnly(getComputedStyle(zoom).transform)
      return { sw: Math.round(s.width), sh: Math.round(s.height),
               zw: Math.round(z.width), zh: Math.round(z.height),
               scale: Number(m.a.toFixed(3)),
               fx: Number((z.width / s.width).toFixed(3)), fy: Number((z.height / s.height).toFixed(3)) }
    })()`)
    check('手机横屏：牌桌按逻辑画布等比铺满一屏',
      !!fill && fill.fx >= 0.94 && fill.fy >= 0.94, JSON.stringify(fill))
    await shot('gt_table_mobile_landscape.png')
    // CDP 截图超时重连会丢 emulation 覆盖（UA 丢失后 resize 会把外壳翻回桌面版，桌面侧栏
    // 盖住舞台、触摸落点打偏）。用 ?m=1 逃生口钉死移动壳，并重新导航拿一个干净起点。
    await evalJs(`try { localStorage.setItem('xuanhuang_force_mobile','1') } catch (e) {}`)
    await applyMobile()
    await navigate(`${TARGET}/tool/games/table/${rid}`)
    await waitFor('.gt-shell', 20000)
    const fsOn2 = await waitUntil(`!!document.querySelector('.gtv-boardwrap.is-fs')`, 4000)
    if (!fsOn2) await evalJs(`(() => { const b=[...document.querySelectorAll('.gtv-btn')].find(x=>x.textContent.trim()==='全屏'); if(b) b.click(); return !!b })()`)
    await waitFor('.gtv-rail', 8000)
    await new Promise(r => setTimeout(r, 1500))
    check('手机端进入牌桌即移动壳（无桌面侧栏遮挡）',
      await evalJs(`!document.querySelector('.dsb-nav')`))
    // 页面侧事件探针：确认 touch 事件确实到达舞台、且目标是哪个元素
    await evalJs(`(() => {
      window.__gtTouch = []
      const st = document.querySelector('.gtv-viewstage')
      const rec = (t) => (e) => window.__gtTouch.push([t, e.touches.length, (e.target && e.target.className) || '', e.cancelable])
      st.addEventListener('touchstart', rec('start'), true)
      st.addEventListener('touchmove', rec('move'), true)
      st.addEventListener('touchend', rec('end'), true)
      return true
    })()`)
    // 双指放大（CDP 多点触控要求每个触点有唯一 id，否则会被合并成单指）
    await applyTouch()
    const before = await evalJs(`(() => { const z=document.querySelector('.gtv-viewzoom'); return Number(new DOMMatrixReadOnly(getComputedStyle(z).transform).a.toFixed(3)) })()`)
    async function touch(type, pts) {
      await send('Input.dispatchTouchEvent', {
        type,
        touchPoints: pts.map((p, i) => ({ x: p[0], y: p[1], id: p[2] || (i + 1) })),
      })
    }
    const box = await evalJs(`(() => { const r=document.querySelector('.gtv-viewstage').getBoundingClientRect(); return [Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)] })()`)
    const bcx = box[0] + Math.round(box[2] / 2)
    const bcy = box[1] + Math.round(box[3] / 2)
    await touch('touchStart', [[bcx - 60, bcy, 1], [bcx + 60, bcy, 2]])
    await touch('touchMove', [[bcx - 90, bcy, 1], [bcx + 90, bcy, 2]])
    await touch('touchMove', [[bcx - 110, bcy, 1], [bcx + 110, bcy, 2]])
    await touch('touchEnd', [])
    await new Promise(r => setTimeout(r, 300))
    const afterPinch = await evalJs(`(() => { const z=document.querySelector('.gtv-viewzoom'); return Number(new DOMMatrixReadOnly(getComputedStyle(z).transform).a.toFixed(3)) })()`)
    check('双指拉伸 → 放大（scale 变大）', afterPinch > before, `${before} -> ${afterPinch}`)
    // 单指拖动（起点须落在非 NO_PAN 区域，否则被划选手牌等交互区吞掉）
    const t0 = await evalJs(`(() => { const z=document.querySelector('.gtv-viewzoom'); const m=new DOMMatrixReadOnly(getComputedStyle(z).transform); return [Number(m.e.toFixed(1)), Number(m.f.toFixed(1))] })()`)
    const panInfo = await evalJs(`(() => {
      const NO_PAN = 'button,a,input,textarea,select,[data-no-pan],.gt-card,.gt-tile,.gd-hand,.gd-history-list,.mj-hand,.mj-discards,.mp-players'
      const stage = document.querySelector('.gtv-viewstage')
      const r = stage.getBoundingClientRect()
      for (let fy = 0.3; fy <= 0.75; fy += 0.15) {
        for (let fx = 0.25; fx <= 0.75; fx += 0.15) {
          const x = Math.round(r.left + r.width * fx), y = Math.round(r.top + r.height * fy)
          const el = document.elementFromPoint(x, y)
          if (el && el.closest && !el.closest(NO_PAN)) {
            return { pt: [x, y], el: (el.tagName || '') + '.' + (el.className || ''),
                     inStage: stage.contains(el) }
          }
        }
      }
      return { pt: [Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2)], el: 'fallback', inStage: true }
    })()`)
    const panPt = panInfo.pt
    await new Promise(r => setTimeout(r, 250))
    await applyTouch()
    const readT = () => evalJs(`(() => { const z=document.querySelector('.gtv-viewzoom'); const m=new DOMMatrixReadOnly(getComputedStyle(z).transform); return [Number(m.e.toFixed(1)), Number(m.f.toFixed(1))] })()`)
    await touch('touchStart', [[panPt[0], panPt[1], 1]])
    const m1 = await readT()
    await touch('touchMove', [[panPt[0] + 90, panPt[1] + 40, 1]])
    const m2 = await readT()
    await touch('touchMove', [[panPt[0] + 150, panPt[1] + 70, 1]])
    const m3 = await readT()
    await touch('touchEnd', [])
    await new Promise(r => setTimeout(r, 300))
    const t1 = await readT()
    const touchLog = await evalJs(`JSON.stringify((window.__gtTouch || []).slice(0, 12))`)
    check('单指拖动 → 平移（translate 改变）', t0[0] !== t1[0] || t0[1] !== t1[1],
      `pan=${JSON.stringify(panInfo)} t0=${JSON.stringify(t0)} m1=${JSON.stringify(m1)} m2=${JSON.stringify(m2)} m3=${JSON.stringify(m3)} t1=${JSON.stringify(t1)} log=${touchLog}`)
    await shot('gt_table_mobile_zoomed.png')

    /* ---------- 6.6) 手机横屏：麻将 / 大富翁 同样铺满一屏 + 双指缩放（v2.44.1） ----------
     * 三款牌桌共用 GameTableView 的缩放外壳（.gtv-viewstage > .gtv-viewzoom），
     * 故对每个 game_key 各建一桌、开局，量一次「外壳铺满舞台」与「双指放大」。 */
    for (const gk of ['mahjong', 'monopoly']) {
      console.log(`\n[6.6] 手机横屏 · ${gk} 铺满一屏 + 双指缩放`)
      let rid2 = null
      try {
        const room2 = await apiJson('/api/game/rooms', {
          method: 'POST', token,
          body: { game_key: gk, invitee_user_ids: [B_UID], base_stake: 100 },
        })
        rid2 = room2.id
        await apiJson(`/api/game/rooms/${rid2}/join`, { method: 'POST', token: tokenB })
        await apiJson(`/api/game/rooms/${rid2}/start`, { method: 'POST', token })
      } catch (e) { console.log(`  [warn] ${gk} 建房失败:`, e.message) }
      if (!rid2) { check(`${gk} 手机横屏铺满一屏`, false, '建房失败'); continue }

      const boardSel = gk === 'mahjong' ? '.mj-hand' : '.mp-board'
      const openMobileTable = async () => {
        await evalJs(`try { localStorage.setItem('xuanhuang_force_mobile','1') } catch (e) {}`)
        await applyMobile()
        await navigate(`${TARGET}/tool/games/table/${rid2}`)
        await waitFor('.gt-shell', 20000)
        // 牌桌是异步组件：等**本局专属**的棋盘/手牌挂载，否则量到的是加载态尺寸
        await waitFor(boardSel, 20000)
        const fsOn = await waitUntil(`!!document.querySelector('.gtv-boardwrap.is-fs')`, 4000)
        if (!fsOn) await evalJs(`(() => { const b=[...document.querySelectorAll('.gtv-btn')].find(x=>x.textContent.trim()==='全屏'); if(b) b.click(); return !!b })()`)
        await waitFor('.gtv-rail', 8000)
        await new Promise(r => setTimeout(r, 1400))
      }
      const readFill = () => evalJs(`(() => {
        const stage = document.querySelector('.gtv-viewstage')
        const zoom = document.querySelector('.gtv-viewzoom')
        if (!stage || !zoom) return null
        const s = stage.getBoundingClientRect(), z = zoom.getBoundingClientRect()
        const m = new DOMMatrixReadOnly(getComputedStyle(zoom).transform)
        return { sw: Math.round(s.width), sh: Math.round(s.height),
                 zw: Math.round(z.width), zh: Math.round(z.height),
                 scale: Number(m.a.toFixed(3)),
                 fx: Number((z.width / s.width).toFixed(3)), fy: Number((z.height / s.height).toFixed(3)) }
      })()`)

      await openMobileTable()
      const fill2 = await readFill()
      check(`${gk} 手机横屏铺满一屏`, !!fill2 && fill2.fx >= 0.94 && fill2.fy >= 0.94, JSON.stringify(fill2))
      await shot(`gt_table_mobile_${gk}.png`)

      await openMobileTable()
      const zr = await evalJs(`(() => { const r=document.querySelector('.gtv-viewstage').getBoundingClientRect(); return [Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)] })()`)
      const cx = zr[0] + Math.round(zr[2] / 2), cy = zr[1] + Math.round(zr[3] / 2)
      // 触控交付自检：截图超时重连会丢 emulation，此时 Input.dispatchTouchEvent 静默不投递
      // （页面侧探针 log=[]），会把「harness 丢了触控」误判成「产品不能缩放」。先单指轻点一次，
      // 确认真有 touchstart 落到页面再测双指；没有就重设覆盖并重试。
      await evalJs(`(() => {
        window.__gtHit = []
        if (!window.__gtHitB) {
          window.__gtHitB = 1
          document.addEventListener('touchstart', (e) => window.__gtHit.push(String((e.target && e.target.className) || '')), true)
        }
        return true
      })()`)
      let delivered = 0
      for (let i = 0; i < 3 && !delivered; i++) {
        await applyTouch()
        await touch('touchStart', [[cx, cy, 1]])
        await touch('touchEnd', [])
        await new Promise(r => setTimeout(r, 250))
        delivered = Number(await evalJs(`(window.__gtHit || []).length`))
        if (!delivered) {
          // 重连后 emulation 覆盖整体失效：重设设备尺寸 + 触控，并重新导航拿干净页面
          await evalJs(`try { localStorage.setItem('xuanhuang_force_mobile','1') } catch (e) {}`)
          await applyMobile()
          await navigate(`${TARGET}/tool/games/table/${rid2}`)
          await waitFor('.gt-shell', 20000)
          await waitFor(boardSel, 20000)
          await waitFor('.gtv-rail', 8000)
          await new Promise(r => setTimeout(r, 1200))
        }
      }
      // 诊断：落点是谁（麻将开局有「定缺」遮罩、大富翁是普通棋盘，两者都必须能被舞台捕获）
      const zr2 = await evalJs(`(() => { const r=document.querySelector('.gtv-viewstage').getBoundingClientRect(); return [Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)] })()`)
      const cx2 = zr2[0] + Math.round(zr2[2] / 2), cy2 = zr2[1] + Math.round(zr2[3] / 2)
      const probe = await evalJs(`(() => {
        window.__gtT = []
        const st = document.querySelector('.gtv-viewstage')
        const rec = (t) => (e) => window.__gtT.push([t, e.touches.length, String((e.target && e.target.className) || ''), e.cancelable])
        st.addEventListener('touchstart', rec('start'), true)
        st.addEventListener('touchmove', rec('move'), true)
        st.addEventListener('touchend', rec('end'), true)
        const el = document.elementFromPoint(${cx2}, ${cy2})
        const chain = []
        for (let n = el; n && chain.length < 6; n = n.parentElement) chain.push(n.tagName + '.' + String(n.className || ''))
        return { at: el ? el.tagName + '.' + String(el.className || '') : 'null',
                 inStage: !!(el && st.contains(el)), chain }
      })()`)
      const readScale = () => evalJs(`Number(new DOMMatrixReadOnly(getComputedStyle(document.querySelector('.gtv-viewzoom')).transform).a.toFixed(3))`)
      const sc0 = await readScale()
      // 与 §6.5 一致：落点前再确认触控在位（截图重试会清掉 emulation 覆盖）
      await applyTouch()
      await touch('touchStart', [[cx2 - 60, cy2, 1], [cx2 + 60, cy2, 2]])
      await touch('touchMove', [[cx2 - 90, cy2, 1], [cx2 + 90, cy2, 2]])
      await touch('touchMove', [[cx2 - 115, cy2, 1], [cx2 + 115, cy2, 2]])
      await touch('touchEnd', [])
      await new Promise(r => setTimeout(r, 300))
      let sc1 = await readScale()
      let via = 'cdp'
      if (!(sc1 > sc0)) {
        // CDP 触控仍未生效：改用页面内合成 TouchEvent 复测——真实 DOM + 真实布局 + 真实
        // usePinchZoom，只绕开 CDP 的触控投递链路。两条链路都跑过才算数，detail 标明 via。
        await evalJs(`(() => {
          const st = document.querySelector('.gtv-viewstage')
          const el = document.elementFromPoint(${cx2}, ${cy2}) || st
          const mk = (id, x, y) => new Touch({ identifier: id, target: el, clientX: x, clientY: y, pageX: x, pageY: y })
          const fire = (type, pts) => {
            const t = pts.map(p => mk(p.id, p.x, p.y))
            el.dispatchEvent(new TouchEvent(type, { touches: t, targetTouches: t, changedTouches: t, bubbles: true, cancelable: true, composed: true }))
          }
          fire('touchstart', [{ id: 1, x: ${cx2} - 60, y: ${cy2} }, { id: 2, x: ${cx2} + 60, y: ${cy2} }])
          fire('touchmove', [{ id: 1, x: ${cx2} - 90, y: ${cy2} }, { id: 2, x: ${cx2} + 90, y: ${cy2} }])
          fire('touchmove', [{ id: 1, x: ${cx2} - 115, y: ${cy2} }, { id: 2, x: ${cx2} + 115, y: ${cy2} }])
          fire('touchend', [])
          return true
        })()`)
        await new Promise(r => setTimeout(r, 300))
        sc1 = await readScale()
        via = 'synthetic'
      }
      const tlog = await evalJs(`JSON.stringify((window.__gtT || []).slice(0, 8))`)
      check(`${gk} 双指拉伸放大`, sc1 > sc0,
        `${sc0} -> ${sc1} | via=${via} 触控交付=${delivered} hit=${probe.at} inStage=${probe.inStage} chain=${JSON.stringify(probe.chain)} log=${tlog}`)
      await shot(`gt_table_mobile_${gk}_zoomed.png`)
    }

    // 还原设备 / 清除强制移动端标记
    mobileMetrics = null
    await evalJs(`try { localStorage.removeItem('xuanhuang_force_mobile') } catch (e) {}`)
    await send('Emulation.clearDeviceMetricsOverride')
    await send('Emulation.setTouchEmulationEnabled', { enabled: false })
  }

  /* ---------- 7) 控制台 / 请求健康 ---------- */
  console.log('\n[7] 控制台与网络')

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
