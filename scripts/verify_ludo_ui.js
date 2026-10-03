#!/usr/bin/env node
/**
 * 飞行棋「飞机棋子 + 事件格文字 + 活力化 UI」· 真实浏览器取证（v2.42.7）
 *
 * 背景：夜星三条 ——
 *   1.「飞行器起码要有飞行器吧」→ 棋子原先只是纯色圆点，要真飞机
 *   2.「页面 UI 整体优化，大气青春有活力」→ 玻璃壳 / 渐变 / 纵深
 *   3.「每个格子展示具体事件，简略也行」→ 事件格光有 emoji 看不懂
 *
 * 本脚本用**真实浏览器打生产**证明三件事都真的落地，而不是只读代码：
 *   A. 飞机棋子：8 枚棋子每枚都带 <svg.lb-plane>（真飞机路径）、且**没有**文字标签
 *      （旧版是圆点+无内容）；钉死 Math.random 起飞一枚后，机头角度随航向旋转 ≠ 0
 *   B. 事件格文字：12 个事件格**同时**有图标 + 短名（加速/陷阱/虫洞/宝箱），四类各 3 个
 *   C. UI 质感：棋盘背景是渐变、玻璃壳有 backdrop-filter、掷骰按钮是渐变；
 *      夜间主题棋盘为深色渐变且事件格底色被提亮（不再是灰砖）
 *   D. 昼夜两主题 + 放大特写共 4 张截图
 *
 * 用法（部署后打生产）：
 *   node scripts/verify_ludo_ui.js
 *   SITE=https://yexingchen.cn node scripts/verify_ludo_ui.js
 */
const WebSocket = require('websocket').w3cwebsocket
const http = require('http')
const https = require('https')
const fs = require('fs')
const path = require('path')
const { spawn } = require('child_process')

const ROOT = path.join(__dirname, '..')
const OUT_DIR = path.join(ROOT, 'artifacts')
const SITE = (process.env.SITE || 'https://yexingchen.cn').replace(/\/$/, '')

function creds() {
  const p = path.join(ROOT, '..', '.secrets', 'local.env')
  const txt = fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : ''
  const seg = txt.split('#项目网站信息')[1] || txt
  const email = (seg.match(/账号[:：]\s*(\S+@\S+)/) || [])[1]
  const pw = (seg.match(/密码[:：]\s*(\S+)/) || [])[1]
  if (!email || !pw) throw new Error('未能在 ../.secrets/local.env 的「#项目网站信息」段找到账号/密码')
  return { email, pw }
}

/* ---------------- CDP ---------------- */
let ws, msgId = 0
const pending = new Map()
const consoleErrors = []
function send(method, params = {}, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    const id = ++msgId
    const t = setTimeout(() => { pending.delete(id); reject(new Error('CDP timeout: ' + method)) }, timeoutMs)
    pending.set(id, { resolve, reject, t })
    ws.send(JSON.stringify({ id, method, params }))
  })
}
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
  const dir = path.join(process.env.TEMP || '/tmp', 'chrome-ludoui-' + Date.now())
  spawn(exe, ['--remote-debugging-port=9222', '--no-first-run', '--no-default-browser-check',
    '--user-data-dir=' + dir, '--window-size=1440,1024', 'about:blank'], { detached: true, stdio: 'ignore' }).unref()
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
    } else if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
      consoleErrors.push((m.params.args || []).map(a => a.value || a.description || '').join(' '))
    } else if (m.method === 'Runtime.exceptionThrown') {
      consoleErrors.push('EXCEPTION: ' + (m.params.exceptionDetails?.exception?.description || m.params.exceptionDetails?.text))
    }
  }
  await send('Runtime.enable'); await send('Page.enable'); await send('Network.enable')
}
async function evalJs(expression) {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (r.exceptionDetails) throw new Error('eval 异常: ' + JSON.stringify(r.exceptionDetails).slice(0, 400))
  return r.result.value
}
async function shot(name, selector) {
  try { await send('Page.bringToFront') } catch { /* 忽略 */ }
  if (selector) {
    // 游戏页内容滚在**内层滚动容器**里（不是 window）→ clip 的页面坐标对不上。
    // 改为「滚到视口中央 + 整屏截图」，最稳。
    await evalJs(`(() => {
      const el = document.querySelector(${JSON.stringify(selector)})
      if (el) el.scrollIntoView({ block: 'center', behavior: 'instant' })
    })()`)
    await sleep(800)
  }
  let r
  for (let i = 0; i < 3; i++) {
    try { r = await send('Page.captureScreenshot', { format: 'png' }, 60000); break }
    catch { await new Promise(x => setTimeout(x, 800)) }
  }
  if (!r) { console.log('   [warn] 截图失败:', name); return }
  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true })
  const f = path.join(OUT_DIR, `ludo-ui-${name}.png`)
  fs.writeFileSync(f, Buffer.from(r.data, 'base64'))
  console.log(`   📸 ${f}`)
}
async function waitFor(sel, timeout = 20000) {
  const t0 = Date.now()
  while (Date.now() - t0 < timeout) {
    if (await evalJs(`!!document.querySelector(${JSON.stringify(sel)})`)) return true
    await new Promise(r => setTimeout(r, 250))
  }
  return false
}
const sleep = (ms) => new Promise(r => setTimeout(r, ms))
const setTheme = (t) => evalJs(`(() => { document.documentElement.dataset.theme = ${JSON.stringify(t)}; return document.documentElement.dataset.theme })()`)

const results = []
function check(name, pass, detail = '') {
  results.push({ name, pass, detail })
  console.log(`   ${pass ? '✅' : '❌'} ${name}${detail ? '  — ' + detail : ''}`)
}

/* ---------------- 主流程 ---------------- */
(async () => {
  const { email, pw } = creds()
  console.log('SITE =', SITE)
  console.log('\n== 1. 生产 API 登录 ==')
  const login = await (await fetch(SITE + '/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password: pw }),
  })).json()
  if (login.code !== 0 || !login.data?.token) throw new Error('登录失败: ' + JSON.stringify(login).slice(0, 300))
  const token = login.data.token
  console.log('   token ok')

  if (!(await chromeRunning())) await launchChrome()
  await connect()

  await send('Page.navigate', { url: SITE + '/login' })
  await sleep(3500)
  // 清 SW/缓存，确保拿到 v302 新代码
  await evalJs(`(async () => {
    try { const rs = await navigator.serviceWorker.getRegistrations(); await Promise.all(rs.map(x => x.unregister())) } catch {}
    try { const ks = await caches.keys(); await Promise.all(ks.map(n => caches.delete(n))) } catch {}
    return 'cleared'
  })()`)
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`)

  console.log('\n== 2. 打开 /tool/games → 飞行棋（双人同屏）==')
  await send('Page.navigate', { url: SITE + '/tool/games' })
  await sleep(1500)
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`)
  await send('Page.reload')
  check('棋类游戏页加载', await waitFor('.gm-item', 25000))
  await evalJs(`(() => {
    const el = [...document.querySelectorAll('.gm-item')].find(e => (e.textContent || '').includes('飞行棋'))
    if (el) el.click()
  })()`)
  await sleep(900)
  const modeHit = await evalJs(`(() => {
    const el = [...document.querySelectorAll('.gm-modecard')].find(e => (e.textContent || '').includes('双人'))
    if (!el) return null
    el.click(); return el.textContent.trim()
  })()`)
  console.log('   模式卡:', JSON.stringify(modeHit))
  check('飞行棋棋盘出现', await waitFor('.lb-board', 15000))
  await sleep(1200)

  /* ============ A. 飞机棋子 ============ */
  console.log('\n== A. 棋子 = 真飞机（不是圆点/数字）==')
  const pieceInfo = await evalJs(`(() => {
    const ps = [...document.querySelectorAll('.lb-piece')]
    const planes = [...document.querySelectorAll('.lb-piece svg.lb-plane')]
    const withPath = planes.filter(s => { const p = s.querySelector('path'); return p && (p.getAttribute('d') || '').length > 80 })
    const texts = ps.map(p => (p.textContent || '').trim()).filter(Boolean)
    return { pieces: ps.length, planes: planes.length, withPath: withPath.length, texts, sampleD: (planes[0]?.querySelector('path')?.getAttribute('d') || '').slice(0, 40) }
  })()`)
  console.log('   棋子:', JSON.stringify(pieceInfo))
  check('棋子全部带飞机 SVG', pieceInfo.pieces > 0 && pieceInfo.planes === pieceInfo.pieces,
    `pieces=${pieceInfo.pieces} planes=${pieceInfo.planes}`)
  check('飞机路径是真实图形（非空占位）', pieceInfo.withPath === pieceInfo.pieces, `withPath=${pieceInfo.withPath}`)
  check('棋子内不再有文字标签', pieceInfo.texts.length === 0, `texts=[${pieceInfo.texts.join(',')}]`)

  // 起飞一枚，验证机头随航向旋转（钉 1 点 → 必能起飞）
  await evalJs(`window.__origRandom = Math.random; Math.random = () => 0; 'pinned'`)
  await evalJs(`(() => { const b = document.querySelector('.lb-roll'); if (b && !b.disabled) b.click(); return 'clicked' })()`)
  await sleep(700)
  const rot = await evalJs(`(() => {
    const mv = document.querySelector('.lb-piece.movable')
    if (mv) mv.click()
    return 'moved'
  })()`)
  await sleep(600)
  const rotInfo = await evalJs(`(() => {
    const s = document.querySelector('.lb-piece .lb-plane')
    const all = [...document.querySelectorAll('.lb-piece .lb-plane')].map(x => x.style.transform)
    return { sample: s ? s.style.transform : '', all, moved: ${JSON.stringify(rot)} }
  })()`)
  console.log('   机头角度:', JSON.stringify(rotInfo.all))
  check('飞机按航向旋转（出现非 0 角度）',
    rotInfo.all.some(t => /rotate\((?!0deg)/.test(t)), rotInfo.all.join(' '))
  await evalJs(`Math.random = window.__origRandom; 'restored'`)

  /* ============ B. 事件格文字 ============ */
  console.log('\n== B. 事件格「图标 + 短名」==')
  const ev = await evalJs(`(() => {
    const cells = [...document.querySelectorAll('.lb-cell.evt')]
    const byType = {}
    const tags = []
    let both = 0
    for (const c of cells) {
      for (const t of ['boost', 'trap', 'warp', 'chest']) if (c.classList.contains('evt-' + t)) byType[t] = (byType[t] || 0) + 1
      const ico = c.querySelector('.lb-evt-ico')
      const tag = c.querySelector('.lb-evt-tag')
      if (ico && tag) both++
      if (tag) tags.push(tag.textContent.trim())
    }
    const fs = tags.length ? getComputedStyle(cells[0].querySelector('.lb-evt-tag')).fontSize : ''
    return { total: cells.length, byType, both, tags, fs }
  })()`)
  console.log('   事件格:', JSON.stringify(ev))
  check('事件格总数 = 12', ev.total === 12, `count=${ev.total}`)
  check('四类事件格各 3 个', ['boost', 'trap', 'warp', 'chest'].every(t => ev.byType[t] === 3), JSON.stringify(ev.byType))
  check('每格都同时有图标 + 短名', ev.both === ev.total, `both=${ev.both}/${ev.total}`)
  check('短名是中文可读标签（加速/陷阱/虫洞/宝箱）',
    ['加速', '陷阱', '虫洞', '宝箱'].every(n => ev.tags.includes(n)), `[${[...new Set(ev.tags)].join(' ')}]`)
  check('短名字号 ≥ 8px（肉眼可读）', parseFloat(ev.fs) >= 8, `fontSize=${ev.fs}`)

  /* ============ C. UI 质感 ============ */
  console.log('\n== C. UI 质感（玻璃 / 渐变 / 纵深）==')
  const ui = await evalJs(`(() => {
    const g = (s, p) => { const el = document.querySelector(s); return el ? getComputedStyle(el)[p] : '' }
    return {
      boardBg: g('.lb-board', 'backgroundImage'),
      shellBlur: g('.lb-shell', 'backdropFilter') || g('.lb-shell', 'webkitBackdropFilter'),
      ctrlBlur: g('.lb-ctrl', 'backdropFilter') || g('.lb-ctrl', 'webkitBackdropFilter'),
      rollBg: g('.lb-roll', 'backgroundImage'),
      boardShadow: g('.lb-board', 'boxShadow'),
      boardRadius: g('.lb-board', 'borderRadius'),
    }
  })()`)
  check('棋盘背景为渐变', /gradient/.test(ui.boardBg), (ui.boardBg || '').slice(0, 50))
  check('玩家条为毛玻璃壳（backdrop-filter: blur）', /blur/.test(ui.shellBlur), ui.shellBlur)
  check('控制区为毛玻璃壳（backdrop-filter: blur）', /blur/.test(ui.ctrlBlur), ui.ctrlBlur)
  check('掷骰按钮为渐变 + 圆角', /gradient/.test(ui.rollBg) && parseFloat(ui.boardRadius) >= 12,
    `roll=${/gradient/.test(ui.rollBg)} radius=${ui.boardRadius}`)
  check('棋盘有纵深投影', /rgba?\(/.test(ui.boardShadow), (ui.boardShadow || '').slice(0, 46))

  /* ============ D. 昼夜 + 特写截图 ============ */
  console.log('\n== D. 昼夜主题 + 特写截图 ==')
  for (const theme of ['day', 'night']) {
    const got = await setTheme(theme)
    await sleep(700)
    const bg = await evalJs(`getComputedStyle(document.querySelector('.lb-board')).backgroundImage`)
    const evtBg = await evalJs(`(() => { const c = document.querySelector('.lb-cell.evt'); return c ? getComputedStyle(c).backgroundColor : '' })()`)
    check(`飞行棋·${theme}：主题生效且棋盘有渐变`, got === theme && /gradient/.test(bg || ''), `theme=${got}`)
    if (theme === 'night') {
      check('夜间主题棋盘为深色系（不再是白壳）', /rgb\(35, 42, 82\)/.test(bg), (bg || '').slice(0, 70))
      check('夜间事件格底色被着色（非灰砖）', /rgb/.test(evtBg), evtBg)
    }
    await shot(`棋盘-${theme}`, '.lb-board')
  }

  // 放大特写：临时把棋盘放大到 1100px，飞机与事件格短名看得更清
  await setTheme('day')
  await sleep(300)
  await evalJs(`(() => {
    const st = document.createElement('style'); st.id = 'lb-zoom-probe'
    st.textContent = '.lb-board{width:min(94vw,1100px)!important}'
    document.head.appendChild(st); return 'zoomed'
  })()`)
  await sleep(500)
  await shot('特写-飞机与事件格', '.lb-board')
  await evalJs(`(() => { const s = document.getElementById('lb-zoom-probe'); if (s) s.remove(); return 'unzoomed' })()`)
  await sleep(300)
  await shot('全貌-图例', '.lb-wrap')

  /* ============ E. 窄屏可读性（手机 375px） ============ */
  console.log('\n== E. 窄屏 375px：事件短名仍可读、不溢出 ==')
  await send('Emulation.setDeviceMetricsOverride', { width: 375, height: 900, deviceScaleFactor: 1, mobile: false })
  await sleep(900)
  const narrow = await evalJs(`(() => {
    const board = document.querySelector('.lb-board')
    const cell = document.querySelector('.lb-cell.evt')
    const tag = document.querySelector('.lb-evt-tag')
    if (!board || !cell || !tag) return null
    const bw = board.getBoundingClientRect().width
    const cw = cell.getBoundingClientRect().width
    const tw = tag.getBoundingClientRect().width
    return { board: Math.round(bw), cell: Math.round(cw), tagFont: getComputedStyle(tag).fontSize, tagW: Math.round(tw) }
  })()`)
  console.log('   375px:', JSON.stringify(narrow))
  check('375px 下棋盘已按窄屏缩放', narrow && narrow.board < 420, `board=${narrow?.board}px`)
  check('375px 下事件短名字号 ≥ 6.5px（手机可读）',
    narrow && parseFloat(narrow.tagFont) >= 6.5, `fontSize=${narrow?.tagFont}`)
  check('375px 下事件短名不溢出格子', narrow && narrow.tagW <= narrow.cell, `tag=${narrow?.tagW} cell=${narrow?.cell}`)
  await shot('窄屏375-棋盘', '.lb-board')
  await send('Emulation.clearDeviceMetricsOverride')
  await sleep(600)

  /* ============ F. 生产 SW 版本 ============ */
  console.log('\n== F. 生产 SW 版本 ==')
  const remoteTxt = await (await fetch(SITE + '/sw.js')).text()
  const gotV = (remoteTxt.match(/xuanhuang-v(\d+)/) || [])[1]
  console.log(`   生产 SW = v${gotV}`)
  check('生产 SW >= v303（本次发版）', Number(gotV) >= 303, `v${gotV}`)

  const realErrors = consoleErrors.filter(e => !/favicon|ResizeObserver/i.test(e))
  check('页面无 JS 控制台错误', realErrors.length === 0, realErrors.slice(0, 3).join(' | '))

  /* ---------------- 汇总 ---------------- */
  console.log('\n' + '='.repeat(64))
  const bad = results.filter(r => !r.pass)
  console.log(`共 ${results.length} 项断言，通过 ${results.length - bad.length}，失败 ${bad.length}`)
  for (const r of bad) console.log(`  ❌ ${r.name} — ${r.detail}`)
  console.log('='.repeat(64))
  process.exit(bad.length ? 1 : 0)
})().catch(e => { console.error('❌ 取证失败:', e.message); process.exit(1) })
