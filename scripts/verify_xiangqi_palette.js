#!/usr/bin/env node
/**
 * 象棋棋盘配色 · 真实浏览器取证（v2.42.5）
 *
 * 背景：夜星反馈「象棋的棋子与棋盘也不搭」。棋子是冷调水晶（蓝灰），
 * 而两个棋盘当时还停在「青玉绿 + 鎏金线」→ 冷暖相冲，与 v2.42.3 五子棋
 * 那次是同一类问题（五子棋盘已改成冷调石板）。
 *
 * 本脚本用**真实浏览器**证明配色真的变了、且是冷调，而不是只读代码：
 *   A. 明棋盘：日/夜两主题各截一张图 + 断言盘面渐变每一档 blue >= green
 *   B. 翻棋盘：同上，另断言牌背 .xf-back 也是冷调（原先玉绿）
 *   C. 网格线 / 「楚河 漢界」：stroke / fill 也必须是冷调
 *      （旧值 rgba(146,114,52) 是暖褐 → green 远大于 blue）
 *
 * 判据说明：新盘面取 #eef3fa/#dbe4f0/#c2d0e2（日）与 #66788f/#4c5a70/#38434f（夜），
 * 每一档都是 b >= g；旧盘面 #e9f1ea/#223130 则是 g > b。所以「每档 b >= g」
 * 能干净地把新旧区分开，不是靠人眼看图。
 *
 * 用法（部署后打生产）：
 *   SITE=https://yexingchen.cn node scripts/verify_xiangqi_palette.js
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
  const dir = path.join(process.env.TEMP || '/tmp', 'chrome-xqpal-' + Date.now())
  spawn(exe, ['--remote-debugging-port=9222', '--no-first-run', '--no-default-browser-check',
    '--user-data-dir=' + dir, '--window-size=1440,960', 'about:blank'], { detached: true, stdio: 'ignore' }).unref()
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
/** 按元素裁图（clip 是页面坐标，需叠加滚动量）。找不到元素就整屏截。 */
async function shot(name, selector) {
  try { await send('Page.bringToFront') } catch { /* 忽略 */ }
  let clip
  if (selector) {
    const box = await evalJs(`(() => {
      const el = document.querySelector(${JSON.stringify(selector)})
      if (!el) return null
      const r = el.getBoundingClientRect()
      return { x: r.left + window.scrollX, y: r.top + window.scrollY, w: r.width, h: r.height }
    })()`)
    if (box && box.w > 0 && box.h > 0) {
      const pad = 26
      clip = { x: Math.max(0, box.x - pad), y: Math.max(0, box.y - pad), width: box.w + pad * 2, height: box.h + pad * 2, scale: 1 }
    }
  }
  let r
  for (let i = 0; i < 3; i++) {
    try { r = await send('Page.captureScreenshot', clip ? { format: 'png', clip } : { format: 'png' }, 60000); break }
    catch { await new Promise(x => setTimeout(x, 800)) }
  }
  if (!r) return
  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true })
  const f = path.join(OUT_DIR, `xiangqi-palette-${name}.png`)
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
const setTheme = (t) => evalJs(`(() => { document.documentElement.dataset.theme = ${JSON.stringify(t)}; return document.documentElement.dataset.theme })()`)

const results = []
function check(name, pass, detail = '') {
  results.push({ name, pass, detail })
  console.log(`   ${pass ? '✅' : '❌'} ${name}${detail ? '  — ' + detail : ''}`)
}

/** 取出 backgroundImage 里所有 rgb() 三元组 */
const RGB_RE = /rgba?\((\d+),\s*(\d+),\s*(\d+)/g
function rgbList(cssText) {
  const out = []
  let m
  RGB_RE.lastIndex = 0
  while ((m = RGB_RE.exec(cssText || '')) !== null) out.push([+m[1], +m[2], +m[3]])
  return out
}
/** 冷调判据：blue >= green（暖褐/青玉都是 green > blue） */
function coolReport(cssText) {
  const list = rgbList(cssText)
  const warm = list.filter(([, g, b]) => b < g)
  return { total: list.length, warm: warm.length, sample: list.slice(0, 6) }
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
  await new Promise(r => setTimeout(r, 3500))
  await evalJs(`(async () => {
    try { const rs = await navigator.serviceWorker.getRegistrations(); await Promise.all(rs.map(x => x.unregister())) } catch {}
    try { const ks = await caches.keys(); await Promise.all(ks.map(n => caches.delete(n))) } catch {}
    return 'cleared'
  })()`)
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`)

  console.log('\n== 2. 打开 /tool/games ==')
  await send('Page.navigate', { url: SITE + '/tool/games' })
  await new Promise(r => setTimeout(r, 1500))
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`)
  await send('Page.reload')
  check('棋类游戏页加载', await waitFor('.gm-item', 25000))

  const enterGame = async (want, modeText) => {
    await evalJs(`(() => {
      const t = ${JSON.stringify(want)}
      const el = [...document.querySelectorAll('.gm-item')].find(e => {
        const s = (e.textContent || '').replace(/\\s+/g, '')
        return t === '翻棋' ? s.includes('象棋翻棋') : (s.startsWith('象棋') && !s.includes('翻棋'))
      })
      if (el) el.click()
    })()`)
    await new Promise(r => setTimeout(r, 900))
    if (modeText) {
      const hit = await evalJs(`(() => {
        const el = [...document.querySelectorAll('.gm-modecard')].find(e => (e.textContent || '').includes(${JSON.stringify(modeText)}))
        if (!el) return null
        el.click(); return el.textContent.trim()
      })()`)
      console.log('   模式卡:', JSON.stringify(hit))
      await new Promise(r => setTimeout(r, 900))
    } else {
      await evalJs(`document.querySelectorAll('.gm-modecard')[0]?.click()`)
      await new Promise(r => setTimeout(r, 900))
    }
  }
  const backToList = async () => {
    await evalJs(`(() => {
      const b = [...document.querySelectorAll('.gm-back,.gm-backbtn,.gm-resume')].find(e => /返回|列表/.test(e.textContent))
      if (b) b.click()
    })()`)
    await new Promise(r => setTimeout(r, 900))
  }

  /* ============ A. 明棋盘 ============ */
  console.log('\n== A. 象棋（明棋）棋盘配色 ==')
  await enterGame('明棋', '单机')
  check('明棋棋盘出现', await waitFor('.xq-board', 15000))
  await new Promise(r => setTimeout(r, 1600))

  for (const theme of ['day', 'night']) {
    const got = await setTheme(theme)
    await new Promise(r => setTimeout(r, 700))
    const info = await evalJs(`(() => {
      const b = document.querySelector('.xq-board')
      const line = document.querySelector('.xq-svg line')
      const river = document.querySelector('.xq-svg text.xq-river')
      return {
        theme: document.documentElement.dataset.theme,
        board: getComputedStyle(b).backgroundImage,
        line: line ? getComputedStyle(line).stroke : '',
        river: river ? getComputedStyle(river).fill : '',
      }
    })()`)
    const brd = coolReport(info.board)
    const ln = coolReport(info.line)
    const rv = coolReport(info.river)
    console.log(`   [${theme}] 盘面 ${brd.total} 档，暖调 ${brd.warm}；线 ${JSON.stringify(ln.sample[0])}；河界 ${JSON.stringify(rv.sample[0])}`)
    check(`明棋·${theme}：主题已生效`, info.theme === theme, `dataset.theme=${info.theme}`)
    check(`明棋·${theme}：盘面每档 blue>=green（冷调）`, brd.total >= 3 && brd.warm === 0, `共 ${brd.total} 档，暖调 ${brd.warm}`)
    check(`明棋·${theme}：网格线冷调`, ln.total >= 1 && ln.warm === 0, `stroke=${info.line}`)
    check(`明棋·${theme}：「楚河 漢界」冷调`, rv.total >= 1 && rv.warm === 0, `fill=${info.river}`)
    await shot(`明棋-${theme}`, '.xq-board')
  }

  /* ============ B. 翻棋盘 ============ */
  console.log('\n== B. 象棋翻棋棋盘配色 ==')
  await backToList()
  await enterGame('翻棋', null)          // 模式卡[0] = 双人同屏
  check('翻棋棋盘出现', await waitFor('.xf-board', 15000))
  await new Promise(r => setTimeout(r, 1600))

  for (const theme of ['day', 'night']) {
    const got = await setTheme(theme)
    await new Promise(r => setTimeout(r, 700))
    const info = await evalJs(`(() => {
      const b = document.querySelector('.xf-board')
      const line = document.querySelector('.xf-svg line')
      const river = document.querySelector('.xf-svg text.xf-river')
      const back = document.querySelector('.xf-back')
      return {
        theme: document.documentElement.dataset.theme,
        board: getComputedStyle(b).backgroundImage,
        line: line ? getComputedStyle(line).stroke : '',
        river: river ? getComputedStyle(river).fill : '',
        back: back ? getComputedStyle(back).backgroundImage : '',
        backs: document.querySelectorAll('.xf-back').length,
      }
    })()`)
    const brd = coolReport(info.board)
    const ln = coolReport(info.line)
    const rv = coolReport(info.river)
    const bk = coolReport(info.back)
    console.log(`   [${theme}] 盘面 ${brd.total} 档，暖调 ${brd.warm}；线 ${JSON.stringify(ln.sample[0])}；河界 ${JSON.stringify(rv.sample[0])}；牌背 ${bk.total} 档，暖调 ${bk.warm}（${info.backs} 张）`)
    check(`翻棋·${theme}：主题已生效`, info.theme === theme, `dataset.theme=${info.theme}`)
    check(`翻棋·${theme}：盘面每档 blue>=green（冷调）`, brd.total >= 3 && brd.warm === 0, `共 ${brd.total} 档，暖调 ${brd.warm}`)
    check(`翻棋·${theme}：网格线冷调`, ln.total >= 1 && ln.warm === 0, `stroke=${info.line}`)
    check(`翻棋·${theme}：「楚河 漢界」冷调`, rv.total >= 1 && rv.warm === 0, `fill=${info.river}`)
    check(`翻棋·${theme}：牌背冷调（非玉绿）`, info.backs > 0 && bk.total >= 3 && bk.warm === 0, `牌背 ${info.backs} 张，暖调 ${bk.warm}`)
    await shot(`翻棋-${theme}`, '.xf-board')
  }

  /* ============ C. 生产 SW 版本 == */
  console.log('\n== C. 生产 SW 版本 ==')
  const remoteTxt = await (await fetch(SITE + '/sw.js')).text()
  const gotV = (remoteTxt.match(/xuanhuang-v(\d+)/) || [])[1]
  console.log(`   生产 SW = v${gotV}`)
  check('生产 SW >= v300（本次发版）', Number(gotV) >= 300, `v${gotV}`)

  /* ---------------- 汇总 ---------------- */
  console.log('\n' + '='.repeat(64))
  const bad = results.filter(r => !r.pass)
  console.log(`共 ${results.length} 项断言，通过 ${results.length - bad.length}，失败 ${bad.length}`)
  for (const r of bad) console.log(`  ❌ ${r.name} — ${r.detail}`)
  console.log('='.repeat(64))
  process.exit(bad.length ? 1 : 0)
})().catch(e => { console.error('❌ 取证失败:', e.message); process.exit(1) })
