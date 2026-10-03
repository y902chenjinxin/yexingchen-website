#!/usr/bin/env node
/**
 * 飞行棋「事件格大乱斗 + 加速规则」· 真实浏览器取证（v2.42.6）
 *
 * 背景：夜星反馈「飞行棋玩法太单调」。网上找的变体整理成四类供选择，
 * 最终选定「事件格大乱斗 + 加速一点 + 起飞放宽」。
 *
 * 本脚本用**真实浏览器打生产**证明新玩法真的生效，而不是只读代码：
 *   A. 事件格：棋盘上 12 个事件格（4 类各 3 个）都渲染出来，且带图标
 *   B. 图例 / 提示：4 类事件图例齐全，规则文案已更新（起飞 1/6、超出直接归航）
 *   C. 起飞放宽：把 Math.random 钉成 0（必出 1 点）→ 四架全在基地时
 *      「有子可走」（旧规则掷 1 只能干瞪眼，日志会是「无子可走」）
 *   D. 事件真的会触发：反复掷骰走子，收集战报日志，至少命中一类事件格
 *   E. 昼夜两主题各截一张棋盘图；命中事件时再截一张战报图
 *
 * 用法（部署后打生产）：
 *   node scripts/verify_ludo_events.js
 *   SITE=https://yexingchen.cn node scripts/verify_ludo_events.js
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
  const dir = path.join(process.env.TEMP || '/tmp', 'chrome-ludo-' + Date.now())
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
    // 游戏页内容滚在**内层滚动容器**里（不是 window）→ clip 的页面坐标对不上，
    // 裁图会拿到错位/全黑区域。改为「滚到视口中央 + 整屏截图」，最稳。
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
  const f = path.join(OUT_DIR, `ludo-${name}.png`)
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
  // 清 SW/缓存，确保拿到 v301 新代码
  await evalJs(`(async () => {
    try { const rs = await navigator.serviceWorker.getRegistrations(); await Promise.all(rs.map(x => x.unregister())) } catch {}
    try { const ks = await caches.keys(); await Promise.all(ks.map(n => caches.delete(n))) } catch {}
    return 'cleared'
  })()`)
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`)

  console.log('\n== 2. 打开 /tool/games ==')
  await send('Page.navigate', { url: SITE + '/tool/games' })
  await sleep(1500)
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`)
  await send('Page.reload')
  check('棋类游戏页加载', await waitFor('.gm-item', 25000))

  console.log('\n== 3. 进入飞行棋（双人同屏）==')
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

  /* ============ A. 事件格渲染 ============ */
  console.log('\n== A. 事件格渲染 ==')
  const ev = await evalJs(`(() => {
    const cells = [...document.querySelectorAll('.lb-cell.evt')]
    const byType = {}
    for (const c of cells) {
      for (const t of ['boost', 'trap', 'warp', 'chest']) if (c.classList.contains('evt-' + t)) byType[t] = (byType[t] || 0) + 1
    }
    const icos = [...document.querySelectorAll('.lb-cell.evt .lb-evt-ico')].map(e => e.textContent.trim())
    return { total: cells.length, byType, icoCount: icos.length, icos }
  })()`)
  console.log('   事件格:', JSON.stringify(ev))
  check('事件格总数 = 12', ev.total === 12, `count=${ev.total}`)
  check('四类事件格各 3 个', ['boost', 'trap', 'warp', 'chest'].every(t => ev.byType[t] === 3),
    JSON.stringify(ev.byType))
  check('事件格图标全部渲染', ev.icoCount === 12, `icons=${ev.icoCount} → ${ev.icos.join('')}`)
  const icoSet = new Set(ev.icos)
  check('图标含 ⚡🕳🌀🎁 四种', ['⚡', '🕳', '🌀', '🎁'].every(i => icoSet.has(i)), `[${[...icoSet].join(' ')}]`)

  /* ============ B. 图例 / 提示文案 ============ */
  console.log('\n== B. 图例 / 规则文案 ==')
  const legend = await evalJs(`(() => {
    const lgs = [...document.querySelectorAll('.lb-lg')].map(e => e.textContent.replace(/\\s+/g, ' ').trim())
    const hint = (document.querySelector('.lb-hint') || {}).textContent || ''
    return { count: lgs.length, lgs, hint: hint.replace(/\\s+/g, ' ').trim() }
  })()`)
  console.log('   图例:', JSON.stringify(legend.lgs))
  console.log('   提示:', legend.hint)
  check('图例 4 条', legend.count === 4, `count=${legend.count}`)
  check('图例含四类名称', ['加速带', '陷阱', '虫洞', '宝箱'].every(n => legend.lgs.some(t => t.includes(n))), legend.lgs.join(' | '))
  check('提示已更新：掷 1 或 6 均可起飞', legend.hint.includes('掷 1 或 6 均可起飞'))
  check('提示已更新：超出终点直接归航', legend.hint.includes('超出终点直接归航'))

  /* ============ C. 起飞放宽：钉 1 点仍可走 ============ */
  console.log('\n== C. 起飞放宽（必出 1 点，基地四子应可起飞）==')
  await evalJs(`window.__origRandom = Math.random; Math.random = () => 0; 'pinned'`)
  const beforeProg = await evalJs(`document.querySelectorAll('.lb-piece.movable').length`)
  await evalJs(`(() => { const b = document.querySelector('.lb-roll'); if (b && !b.disabled) b.click(); return 'clicked' })()`)
  await sleep(600)
  const takeoff = await evalJs(`(() => {
    const logs = [...document.querySelectorAll('.lb-log li')].map(e => e.textContent.trim())
    return {
      dice: document.querySelectorAll('.lb-dice i.on').length,
      movable: document.querySelectorAll('.lb-piece.movable').length,
      lastLogs: logs.slice(-2),
    }
  })()`)
  console.log('   掷骰后:', JSON.stringify(takeoff))
  check('掷出 1 点后未出现「无子可走」', !takeoff.lastLogs.some(l => l.includes('无子可走')), takeoff.lastLogs.join(' / '))
  check('掷出 1 点后基地棋子可走（起飞放宽生效）', takeoff.movable > 0, `movable=${takeoff.movable}`)
  // 走一步，把 red 送到起点，恢复随机
  await evalJs(`(() => { const p = document.querySelector('.lb-piece.movable'); if (p) p.click(); return 'moved' })()`)
  await sleep(400)
  await evalJs(`Math.random = window.__origRandom; 'restored'`)

  /* ============ D. 事件真的会触发 ============ */
  console.log('\n== D. 反复对局，验证事件格会触发 ==')
  const EVT_NAMES = { '加速带': 'boost', '陷阱': 'trap', '虫洞': 'warp', '宝箱': 'chest' }
  const seenLogs = new Set()
  const firedTypes = new Set()
  let eventShot = false
  for (let k = 0; k < 160; k++) {
    const st = await evalJs(`(() => {
      if (document.querySelector('.lb-result')) return 'OVER'
      const roll = document.querySelector('.lb-roll')
      if (roll && !roll.disabled) { roll.click(); return 'ROLL' }
      const p = document.querySelector('.lb-piece.movable')
      if (p) { p.click(); return 'MOVE' }
      return 'WAIT'
    })()`)
    const last = await evalJs(`(document.querySelector('.lb-log li:last-child') || {}).textContent || ''`)
    if (last) seenLogs.add(last.trim())
    for (const [name, key] of Object.entries(EVT_NAMES)) {
      if (last.includes(name)) {
        firedTypes.add(key)
        if (!eventShot) { eventShot = true; await shot('事件触发-战报', '.lb-ctrl') }
      }
    }
    if (st === 'OVER') {
      await evalJs(`(() => { const b = [...document.querySelectorAll('.lb-btn')].find(e => /重开一局/.test(e.textContent)); if (b) b.click() })()`)
      await sleep(300)
    }
    if (Object.keys(EVT_NAMES).length === firedTypes.size) break
    await sleep(160)
  }
  console.log('   命中事件类型:', JSON.stringify([...firedTypes]))
  console.log('   战报样本:')
  ;[...seenLogs].slice(-8).forEach(l => console.log('     · ' + l))
  check('至少触发 1 类事件格', firedTypes.size >= 1, `types=[${[...firedTypes].join(',')}]`)
  const hasEvtLog = [...seenLogs].some(l => Object.keys(EVT_NAMES).some(n => l.includes(n)))
  check('战报中出现事件格提示文案', hasEvtLog, `logs=${seenLogs.size}`)

  /* ============ E. 昼夜两主题截图 ============ */
  console.log('\n== E. 昼夜主题截图 ==')
  for (const theme of ['day', 'night']) {
    const got = await setTheme(theme)
    await sleep(600)
    const bg = await evalJs(`getComputedStyle(document.querySelector('.lb-board')).backgroundImage`)
    check(`飞行棋·${theme}：主题生效`, got === theme, `dataset.theme=${got}`)
    check(`飞行棋·${theme}：棋盘有底色渐变`, /gradient/.test(bg || ''), (bg || '').slice(0, 60))
    await shot(`棋盘-${theme}`, '.lb-board')
  }
  await shot('全貌-图例', '.lb-wrap')

  /* ============ F. 生产 SW 版本 ============ */
  console.log('\n== F. 生产 SW 版本 ==')
  const remoteTxt = await (await fetch(SITE + '/sw.js')).text()
  const gotV = (remoteTxt.match(/xuanhuang-v(\d+)/) || [])[1]
  console.log(`   生产 SW = v${gotV}`)
  check('生产 SW >= v301（本次发版）', Number(gotV) >= 301, `v${gotV}`)

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
