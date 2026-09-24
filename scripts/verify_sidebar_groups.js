#!/usr/bin/env node
/** 侧栏分组取证：读取分组→子项结构、记账高亮位置、记账页标题，并截图。 */
const WebSocket = require('websocket').w3cwebsocket;
const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

const SITE = 'https://yexingchen.cn';
const EMAIL = 'admin@yexingchen.cn';
const PASSWORD = 'Chen@12345678';

function httpJson(url, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const req = https.request(url, {
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
  setTimeout(() => { ws.removeEventListener('message', h); rej(new Error('timeout ' + m)); }, 90000);
});
const evalJs = async (e) => (await send('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true })).result?.result?.value;

let errs = [];
const OUT = path.join(__dirname, '..', 'artifacts');

const READ_GROUPS = `(() => {
  const nav = document.querySelector('.dsb-nav');
  if (!nav) return 'NO_SIDEBAR';
  const out = [];
  let cur = null;
  for (const el of nav.children) {
    if (el.classList.contains('dsb-group-label')) { cur = { group: el.textContent.trim(), items: [] }; out.push(cur); }
    else if (el.classList.contains('dsb-item')) {
      const label = el.querySelector('.dsb-label')?.textContent.trim();
      const active = el.classList.contains('active');
      if (!cur) { cur = { group: '(无分组)', items: [] }; out.push(cur); }
      cur.items.push(label + (active ? ' ★active' : ''));
    }
  }
  return JSON.stringify(out);
})()`;

(async () => {
  const targets = await new Promise((res, rej) => {
    http.get('http://localhost:9222/json', (r) => { let b = ''; r.on('data', (c) => b += c); r.on('end', () => res(JSON.parse(b))); }).on('error', rej);
  });
  const page = targets.find((t) => t.type === 'page' && t.url.includes('yexingchen.cn')) || targets[0];
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') errs.push((m.params.args || []).map((a) => a.value || a.description || '').join(' '));
    if (m.method === 'Runtime.exceptionThrown') errs.push('EXC: ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
  };
  await send('Runtime.enable'); await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });

  console.log('=== 0. 登录并注入 token ===');
  const login = await httpJson(SITE + '/api/auth/login', { email: EMAIL, password: PASSWORD });
  if (login.code !== 0 || !login.data?.token) throw new Error('login failed: ' + JSON.stringify(login).slice(0, 200));
  const token = login.data.token;
  await send('Page.navigate', { url: SITE + '/login' });
  await new Promise((r) => setTimeout(r, 6000));
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`);
  console.log('  token ok');

  await send('Page.navigate', { url: 'https://yexingchen.cn/workbench' });
  await new Promise((r) => setTimeout(r, 11000));
  console.log('=== 侧栏分组结构 ===');
  const g = await evalJs(READ_GROUPS);
  if (g === 'NO_SIDEBAR') { console.log('  未找到侧栏（可能已折叠）'); }
  else JSON.parse(g).forEach((x) => console.log(`  【${x.group}】 ${x.items.join(' / ')}`));

  await evalJs(`(() => { const n = document.querySelector('.dsb-nav'); if (n) n.scrollTop = n.scrollHeight; return 1 })()`);
  await new Promise((r) => setTimeout(r, 500));
  let r = await send('Page.captureScreenshot', { format: 'png' });
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, 'sidebar_after_move.png'), Buffer.from(r.result.data, 'base64'));
  console.log('  shot: artifacts/sidebar_after_move.png');

  console.log('\n=== 打开 /finance/book（记账） ===');
  errs = [];
  await send('Page.navigate', { url: 'https://yexingchen.cn/finance/book' });
  await new Promise((r) => setTimeout(r, 10000));
  console.log('  标题:', await evalJs(`document.querySelector('.fin-title')?.textContent?.trim()`));
  console.log('  副标题:', await evalJs(`document.querySelector('.fin-sub')?.textContent?.trim()`));
  const g2 = await evalJs(READ_GROUPS);
  if (g2 !== 'NO_SIDEBAR') {
    const grp = JSON.parse(g2);
    const hit = grp.find((x) => x.items.some((i) => i.includes('记账') && i.includes('★active')));
    console.log('  高亮落在分组:', hit ? hit.group : '(未高亮)');
    const fin = grp.find((x) => x.group === '财经');
    console.log('  财经分组子项:', fin ? fin.items.join(' / ') : '(缺失)');
    const life = grp.find((x) => x.group === '生活');
    console.log('  生活分组子项:', life ? life.items.join(' / ') : '(缺失)');
  }
  console.log('  控制台错误:', errs.length ? errs.slice(0, 3).join(' | ') : '(none)');

  r = await send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(path.join(OUT, 'finance_book_page.png'), Buffer.from(r.result.data, 'base64'));
  console.log('  shot: artifacts/finance_book_page.png');

  ws.close(); process.exit(0);
})().catch((e) => { console.error('[FAIL]', e.message); process.exit(1); });