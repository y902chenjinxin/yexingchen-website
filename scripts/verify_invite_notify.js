#!/usr/bin/env node
/**
 * 对局邀请通知取证（v2.45）：真实浏览器 + 真实后端，验证
 *   ① 收到邀请后顶栏角标出现（不依赖一次性弹窗）
 *   ② 打开提醒中心能看到「对局邀请」段与就地接受/拒绝
 *   ③ 新到时有非阻塞 ElNotification 提示
 *   ④ 移动端（?m=1）悬浮邀请胶囊可用
 * 前置：本地后端 :8000、前端 dev :5173 均已启动，且本地库有 1/2 号取证账号。
 * 用法：node scripts/verify_invite_notify.js
 */
const WebSocket = require('websocket').w3cwebsocket;
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const SITE = process.env.YX_SITE || 'http://localhost:5173';
const API = process.env.YX_API || 'http://127.0.0.1:8000';
const OUT_DIR = path.join(__dirname, '..', 'artifacts');

const A = { email: 'admin@yexingchen.cn', password: 'Verify@12345678' };   // 房主（发邀请）
const B = { email: 'evtest@local.local', password: 'Verify@12345678' };    // 受邀方（收邀请）

let ws, msgId = 0;
const consoleErrors = [];
const failedRequests = [];
const results = [];

function ok(name, pass, detail = '') {
  results.push({ name, pass, detail });
  console.log(`  ${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? '  — ' + detail : ''}`);
}

function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++msgId;
    ws.send(JSON.stringify({ id, method, params }));
    const handler = (event) => {
      const r = JSON.parse(event.data);
      if (r.id === id) { ws.removeEventListener('message', handler); resolve(r); }
    };
    ws.addEventListener('message', handler);
    setTimeout(() => { ws.removeEventListener('message', handler); reject(new Error('timeout ' + method)); }, 30000);
  });
}

function reqJson(url, { method = 'GET', body, token } = {}) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : null;
    const u = new URL(url);
    const headers = {};
    if (data) { headers['Content-Type'] = 'application/json'; headers['Content-Length'] = Buffer.byteLength(data); }
    if (token) headers.Authorization = 'Bearer ' + token;
    const r = http.request({ hostname: u.hostname, port: u.port, path: u.pathname + u.search, method, headers }, (res) => {
      let b = '';
      res.on('data', (c) => b += c);
      res.on('end', () => { try { resolve(JSON.parse(b)); } catch (e) { reject(new Error('bad json: ' + b.slice(0, 200))); } });
    });
    r.on('error', reject);
    if (data) r.write(data);
    r.end();
  });
}

function chromeRunning() {
  return new Promise((resolve) => {
    const r = http.get('http://localhost:9222/json', () => resolve(true));
    r.on('error', () => resolve(false));
    r.setTimeout(2000, () => { r.destroy(); resolve(false); });
  });
}

async function launchChrome() {
  const paths = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  ];
  const exe = paths.find((p) => fs.existsSync(p));
  if (!exe) throw new Error('Chrome not found');
  const dir = path.join(process.env.TEMP || '/tmp', 'chrome-invite-' + Date.now());
  console.log('[browser] launching Chrome');
  spawn(exe, ['--remote-debugging-port=9222', '--no-first-run', '--no-default-browser-check', `--user-data-dir=${dir}`], { detached: true, stdio: 'ignore' }).unref();
  await new Promise((r) => setTimeout(r, 4000));
}

function getTargets() {
  return new Promise((resolve, reject) => {
    http.get('http://localhost:9222/json', (res) => {
      let b = ''; res.on('data', (c) => b += c); res.on('end', () => resolve(JSON.parse(b)));
    }).on('error', reject);
  });
}

async function connect() {
  const targets = await getTargets();
  const page = targets.find((t) => t.type === 'page') || targets[0];
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  ws.onmessage = (event) => {
    const m = JSON.parse(event.data);
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
      consoleErrors.push((m.params.args || []).map((a) => a.value || a.description || '').join(' '));
    }
    if (m.method === 'Runtime.exceptionThrown') {
      const d = m.params.exceptionDetails;
      consoleErrors.push('EXCEPTION: ' + (d.exception?.description || d.text));
    }
    if (m.method === 'Network.responseReceived') {
      const { url, status } = m.params.response;
      if (url.includes('/api/') && status >= 400) failedRequests.push(`${status} ${url}`);
    }
  };
  await send('Runtime.enable');
  await send('Page.enable');
  await send('Network.enable');
}

async function evalJs(expression) {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  return r.result?.result?.value;
}

async function waitFor(expr, timeout = 20000, step = 500) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    if (await evalJs(expr)) return true;
    await new Promise((r) => setTimeout(r, step));
  }
  return false;
}

async function shot(name) {
  const r = await send('Page.captureScreenshot', { format: 'png' });
  if (!r.result?.data) { console.log('  [warn] screenshot empty'); return null; }
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const p = path.join(OUT_DIR, name);
  fs.writeFileSync(p, Buffer.from(r.result.data, 'base64'));
  console.log('  [shot]', p);
  return p;
}

(async () => {
  console.log('== 1. 登录两个取证账号 ==');
  const la = await reqJson(`${API}/api/auth/login`, { method: 'POST', body: A });
  const lb = await reqJson(`${API}/api/auth/login`, { method: 'POST', body: B });
  if (la.code !== 0 || lb.code !== 0) throw new Error('login failed');
  const tokenA = la.data.token, tokenB = lb.data.token;
  console.log('  A =', la.data.user.email, '/ B =', lb.data.user.email);

  console.log('== 2. 清掉历史遗留房间，保证断言干净 ==');
  for (const t of [tokenA, tokenB]) {
    const mine = await reqJson(`${API}/api/games/rooms/mine`, { token: t });
    for (const r of (mine.data?.list || [])) {
      if (r.status === 'waiting' || r.status === 'playing') {
        await reqJson(`${API}/api/games/rooms/${r.id}/leave`, { method: 'POST', body: {}, token: t });
      }
    }
    const mt = await reqJson(`${API}/api/game/rooms/mine`, { token: t });
    for (const r of (mt.data?.list || [])) {
      if (r.status === 'waiting' || r.status === 'playing') {
        await reqJson(`${API}/api/game/rooms/${r.id}/dissolve`, { method: 'POST', body: {}, token: t });
      }
    }
  }

  console.log('== 3. A 向 B 发一条棋类邀请 + 一条牌桌邀请（真实接口） ==');
  const chess = await reqJson(`${API}/api/games/rooms`, {
    method: 'POST', token: tokenA,
    body: { game: 'gomoku', invitee_user_id: 2, first: 'me', base_stake: 100, ai_seats: 0 },
  });
  const table = await reqJson(`${API}/api/game/rooms`, {
    method: 'POST', token: tokenA,
    body: { game_key: 'guandan', invitee_user_ids: [2], base_stake: 100 },
  });
  ok('棋类邀请已创建', chess.code === 0, `room=${chess.data?.id} status=${chess.data?.status}`);
  ok('牌桌邀请已创建', table.code === 0, `room=${table.data?.id} status=${table.data?.status}`);

  const seen = await reqJson(`${API}/api/games/invites`, { token: tokenB });
  ok('受邀方 /games/invites 能查到棋类邀请', (seen.data?.list || []).length === 1);

  console.log('== 4. 浏览器：以 B 身份打开（注入 token） ==');
  if (!(await chromeRunning())) await launchChrome();
  await connect();
  await send('Page.navigate', { url: SITE + '/login' });
  await new Promise((r) => setTimeout(r, 4000));
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(tokenB)}); localStorage.removeItem('xuanhuang_force_mobile')`);

  consoleErrors.length = 0;
  failedRequests.length = 0;
  await send('Page.navigate', { url: SITE + '/workbench' });

  const gotBadge = await waitFor(`(() => { const d = document.querySelector('.tb-alert-dot'); return !!d && d.textContent.trim() === '2' })()`, 25000);
  ok('顶栏角标出现且计数 = 2（不靠弹窗）', gotBadge);

  const toast = await evalJs(`document.querySelector('.el-notification')?.innerText || ''`);
  ok('新到邀请有非阻塞提示（ElNotification）', /收到对局邀请/.test(toast), toast.replace(/\s+/g, ' ').slice(0, 60));

  const noModal = await evalJs(`!document.querySelector('.el-message-box')`);
  ok('不再出现居中确认弹窗', noModal);

  await shot('invite_topbar_badge.png');

  console.log('== 5. 打开提醒中心，检查「对局邀请」段 ==');
  await evalJs(`document.querySelector('.tb-alert-btn').click()`);
  await new Promise((r) => setTimeout(r, 1200));
  const panel = await evalJs(`(() => {
    const secs = [...document.querySelectorAll('.tb-alert-section')];
    const sec = secs.find(s => s.innerText.includes('对局邀请'));
    if (!sec) return JSON.stringify({ found: false });
    const rows = [...sec.querySelectorAll('.tb-alert-item.kind-invite')];
    return JSON.stringify({
      found: true,
      count: rows.length,
      text: sec.innerText.replace(/\\s+/g, ' ').trim(),
      buttons: rows.map(r => [...r.querySelectorAll('button')].map(b => b.textContent.trim())),
    });
  })()`);
  const p = JSON.parse(panel || '{}');
  ok('面板含「对局邀请」段', p.found === true);
  ok('段内两条待处理邀请', p.count === 2, `count=${p.count}`);
  ok('每行都有接受/拒绝按钮', JSON.stringify(p.buttons) === JSON.stringify([['接受', '拒绝'], ['接受', '拒绝']]), JSON.stringify(p.buttons));
  console.log('  段文本:', p.text);
  await shot('invite_panel.png');

  console.log('== 6. 就地「接受」棋类邀请 → 应跳进对局 ==');
  await evalJs(`(() => {
    const rows = [...document.querySelectorAll('.tb-alert-item.kind-invite')];
    const row = rows.find(r => r.innerText.includes('五子棋'));
    row.querySelector('button.accept').click();
  })()`);
  const jumped = await waitFor(`location.pathname.startsWith('/tool/games') && location.search.includes('room=${chess.data.id}')`, 15000);
  ok('接受后跳转到对局页', jumped, await evalJs('location.href'));
  await shot('invite_accept_jump.png');

  const afterBadge = await evalJs(`document.querySelector('.tb-alert-dot')?.textContent.trim() ?? '0'`);
  ok('接受后角标从 2 降到 1', afterBadge === '1', `badge=${afterBadge}`);

  console.log('== 7. 移动端（?m=1）悬浮邀请胶囊 ==');
  await send('Page.navigate', { url: SITE + '/workbench?m=1' });
  const gotDock = await waitFor(`!!document.querySelector('.mid-pill')`, 25000);
  ok('移动端出现邀请胶囊', gotDock);
  const dockN = await evalJs(`document.querySelector('.mid-pill__n')?.textContent.trim() || ''`);
  ok('胶囊计数 = 1（剩牌桌那条）', dockN === '1', `n=${dockN}`);
  await evalJs(`document.querySelector('.mid-pill').click()`);
  await new Promise((r) => setTimeout(r, 800));
  const card = await evalJs(`document.querySelector('.mid-card')?.innerText.replace(/\\s+/g,' ').trim() || ''`);
  ok('胶囊展开后有邀请详情与操作', /接受/.test(card) && /拒绝/.test(card), card.slice(0, 80));
  await shot('invite_mobile_dock.png');

  console.log('== 8. 控制台 / 网络 ==');
  ok('零控制台错误', consoleErrors.length === 0, consoleErrors.join(' | ').slice(0, 200));
  // 天气接口依赖外网 / 密钥，本地取证环境必然 503，与邀请链路无关，单独排除
  const realFail = failedRequests.filter((u) => !/\/api\/workbench\/dashboard\/weather/.test(u));
  ok('无意外失败请求', realFail.length === 0, realFail.join(' | ').slice(0, 200));

  const passed = results.filter((r) => r.pass).length;
  console.log(`\n== 结果 ${passed}/${results.length} ==`);
  results.filter((r) => !r.pass).forEach((r) => console.log('  FAIL:', r.name, r.detail));
  ws.close();
  process.exit(passed === results.length ? 0 : 1);
})().catch((e) => { console.error('[FAIL]', e.message); process.exit(1); });
