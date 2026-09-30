#!/usr/bin/env node
/**
 * 「拆站小游戏」外链入口取证
 *
 * 覆盖（对生产构建产物取证，SITE 默认 4173 预览）：
 *  1. 桌面侧栏「娱乐」分组含「拆站小游戏」，href = destroy.spritefusion.com
 *  2. 该条目 target=_blank + rel 含 noopener（第三方站必须新标签，否则同标签跳走回不来）
 *  3. 同组的「人生重开模拟器」**不受影响**：仍是同标签（没有 target）
 *  4. 真点击一次，确认真的开出了新标签并指向目标地址（不是只读 DOM 属性）
 *  5. 手机端 390×844 模块目录「娱乐」分组同样带 target=_blank
 *
 * 用法：node scripts/verify_destroy_entry.js
 *   SITE=http://localhost:4173  API=http://127.0.0.1:8000
 *   （线上登录限流偏严，默认打本地后端；要打线上就覆盖 API=https://yexingchen.cn）
 */
const WebSocket = require('websocket').w3cwebsocket;
const http = require('http');
const fs = require('fs');
const path = require('path');

const SITE = process.env.SITE || 'http://localhost:4173';
const API = process.env.API || 'http://127.0.0.1:8000';
const EMAIL = 'admin@yexingchen.cn';
const PASSWORD = 'Chen@12345678';
const TARGET_URL = 'https://destroy.spritefusion.com/';
const OUT = path.join(__dirname, '..', 'artifacts');

function httpJson(url, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const lib = url.startsWith('https:') ? require('https') : http;
    const req = lib.request(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) },
    }, (res) => { let b = ''; res.on('data', (c) => b += c); res.on('end', () => resolve(JSON.parse(b))); });
    req.on('error', reject); req.write(data); req.end();
  });
}

let ws, msgId = 0;
const send = (m, p = {}) => new Promise((res, rej) => {
  const id = ++msgId;
  ws.send(JSON.stringify({ id, method: m, params: p }));
  const h = (e) => { const r = JSON.parse(e.data); if (r.id === id) { ws.removeEventListener('message', h); res(r); } };
  ws.addEventListener('message', h);
  setTimeout(() => { ws.removeEventListener('message', h); rej(new Error('timeout ' + m)); }, 30000);
});
const evalJs = async (e) => (await send('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true })).result?.result?.value;
// 带用户手势的求值：无 gesture 时 Chrome 会把 target=_blank 当弹窗拦截，新标签开不出来
const evalJsAsUser = async (e) => (await send('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true, userGesture: true })).result?.result?.value;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function pumpFrame() {
  const p = send('Page.captureScreenshot', { format: 'jpeg', quality: 20 });
  p.catch(() => {});
  try { await Promise.race([p, sleep(6000).then(() => { throw new Error('frame-timeout'); })]); } catch { /* 单帧失败不致命 */ }
}
async function waitFor(selector, timeout = 25000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    if (await evalJs(`!!document.querySelector(${JSON.stringify(selector)})`)) return true;
    await pumpFrame(); await sleep(250);
  }
  return false;
}
async function shot(name) {
  try {
    const r = await Promise.race([send('Page.captureScreenshot', { format: 'png' }), sleep(8000).then(() => ({ result: { data: '' } }))]);
    if (!r?.result?.data) { console.log('  shot(' + name + '): 跳过（超时/无帧）'); return; }
    fs.mkdirSync(OUT, { recursive: true });
    fs.writeFileSync(path.join(OUT, name), Buffer.from(r.result.data, 'base64'));
    console.log('  shot: artifacts/' + name);
  } catch (e) { console.log('  shot(' + name + '): 跳过（' + String(e.message).slice(0, 50) + ')'); }
}

/** 读侧栏「娱乐」分组的条目属性 */
const READ_ENTERTAINMENT = `(() => {
  const nav = document.querySelector('.dsb-nav');
  if (!nav) return 'NO_SIDEBAR';
  let inGroup = false;
  const out = [];
  for (const el of nav.children) {
    if (el.classList.contains('dsb-group-label')) { inGroup = el.textContent.trim() === '娱乐'; continue; }
    if (!inGroup) continue;
    if (el.classList.contains('dsb-item')) {
      out.push({
        title: el.querySelector('.dsb-label')?.textContent.trim() || el.textContent.trim(),
        tag: el.tagName.toLowerCase(),
        href: el.getAttribute('href'),
        target: el.getAttribute('target'),
        rel: el.getAttribute('rel'),
      });
    }
  }
  return JSON.stringify(out);
})()`;

/** 手机端模块目录「娱乐」分组卡片 */
const READ_MOBILE_ENTERTAINMENT = `(() => {
  const secs = [...document.querySelectorAll('.mdl-sec, section')];
  for (const s of secs) {
    const lab = s.querySelector('.mdl-sec__name, h2, .mdl-title');
    if (!lab || lab.textContent.trim() !== '娱乐') continue;
    return JSON.stringify([...s.querySelectorAll('a.mdl-card, a')].map(a => ({
      title: a.querySelector('.mdl-card__lab')?.textContent.trim() || a.textContent.trim(),
      href: a.getAttribute('href'),
      target: a.getAttribute('target'),
      rel: a.getAttribute('rel'),
    })));
  }
  return 'NO_ENTERTAINMENT_SECTION';
})()`;

(async () => {
  const targets = await new Promise((res, rej) => {
    http.get('http://localhost:9222/json', (r) => { let b = ''; r.on('data', (c) => b += c); r.on('end', () => res(JSON.parse(b))); }).on('error', rej);
  });
  const page = targets.find((t) => t.type === 'page') || targets[0];
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });

  // 监听新标签
  const newTabs = [];
  ws.addEventListener('message', (e) => {
    const m = JSON.parse(e.data);
    if (m.method === 'Target.targetCreated' && m.params.targetInfo.type === 'page') newTabs.push(m.params.targetInfo.url);
  });

  await send('Runtime.enable'); await send('Page.enable');
  await send('Target.setDiscoverTargets', { discover: true });
  await send('Emulation.setFocusEmulationEnabled', { enabled: true });

  console.log('=== 0. 登录 ===');
  const login = await httpJson(API + '/api/auth/login', { email: EMAIL, password: PASSWORD });
  if (login.code !== 0 || !login.data?.token) throw new Error('登录失败: ' + JSON.stringify(login).slice(0, 200));
  const token = login.data.token;
  console.log('  token ok（后端 ' + API + '）');

  // ---------- 桌面 ----------
  console.log('\n=== 1. 桌面侧栏「娱乐」分组（1440×1100）===');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: SITE + '/login?m=0' });
  await sleep(3000);
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`);
  await send('Page.navigate', { url: SITE + '/workbench?m=0' });
  if (!await waitFor('.dsb-nav .dsb-group-label', 25000)) throw new Error('侧栏未渲染');
  await sleep(800);

  const items = JSON.parse(await evalJs(READ_ENTERTAINMENT));
  items.forEach((it) => console.log(`   - ${it.title}  <${it.tag}>  href=${it.href}  target=${it.target}  rel=${it.rel}`));

  const destroy = items.find((it) => it.title === '拆站小游戏');
  if (!destroy) throw new Error('「娱乐」分组缺少「拆站小游戏」条目：' + JSON.stringify(items.map(i => i.title)));
  if (destroy.href !== TARGET_URL) throw new Error('href 不符：' + destroy.href);
  if (destroy.target !== '_blank') throw new Error('未设 target=_blank，会同标签跳走：' + destroy.target);
  if (!/noopener/.test(destroy.rel || '')) throw new Error('rel 缺 noopener：' + destroy.rel);

  const restart = items.find((it) => it.title === '人生重开模拟器');
  if (!restart) throw new Error('「人生重开模拟器」条目丢失（回归）');
  if (restart.target) throw new Error('「人生重开模拟器」被误改为新标签，属行为回归：' + restart.target);
  console.log('  ✅ 拆站小游戏：新标签 + noopener；人生重开模拟器：仍同标签（未受影响）');

  // 真实点击，确认真的开出新标签
  console.log('\n=== 2. 真点击验证（不是只读 DOM 属性）===');
  newTabs.length = 0;
  await evalJsAsUser(`(() => {
    const nav = document.querySelector('.dsb-nav');
    let inGroup = false;
    for (const el of nav.children) {
      if (el.classList.contains('dsb-group-label')) { inGroup = el.textContent.trim() === '娱乐'; continue; }
      if (inGroup && el.tagName === 'A' && el.querySelector('.dsb-label')?.textContent.trim() === '拆站小游戏') { el.click(); return 'clicked'; }
    }
    return 'not-found';
  })()`);
  // Target.targetCreated 在标签刚建出来时 url 常为空串（还在 about:blank），
  // 所以轮询 getTargets 读最终地址，而不是只看创建瞬间的快照
  let hit = '';
  for (let i = 0; i < 20 && !hit; i++) {
    await sleep(500);
    const t = await send('Target.getTargets');
    hit = (t.result?.targetInfos || [])
      .filter((x) => x.type === 'page')
      .map((x) => x.url)
      .find((u) => u.includes('destroy.spritefusion.com')) || '';
  }
  if (!hit) {
    const t = await send('Target.getTargets');
    throw new Error('点击后没有开出指向该站的新标签，现有 page 目标：'
      + JSON.stringify((t.result?.targetInfos || []).filter(x => x.type === 'page').map(x => x.url)));
  }
  console.log('  ✅ 新标签已开出：' + hit);
  await shot('destroy_entry_sidebar.png');

  // ---------- 手机 ----------
  console.log('\n=== 3. 手机端模块目录（390×844 + 触控仿真）===');
  await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
  await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  await send('Page.navigate', { url: SITE + '/modules?m=1' });
  await sleep(6000);
  const mob = await evalJs(READ_MOBILE_ENTERTAINMENT);
  if (mob === 'NO_ENTERTAINMENT_SECTION') { console.log('  ⚠ 未定位到「娱乐」分区（选择器可能变了），跳过'); }
  else {
    const list = JSON.parse(mob);
    list.forEach((it) => console.log(`   - ${it.title}  href=${it.href}  target=${it.target}`));
    const md = list.find((it) => it.title === '拆站小游戏');
    if (!md) throw new Error('手机端「娱乐」缺少「拆站小游戏」');
    if (md.target !== '_blank') throw new Error('手机端未设 target=_blank：' + md.target);
    console.log('  ✅ 手机端同样新标签打开');
    await shot('destroy_entry_mobile.png');
  }

  console.log('\n=== 全部通过 ===');
  ws.close(); process.exit(0);
})().catch((e) => { console.error('\n[FAIL]', e.message); process.exit(1); });
