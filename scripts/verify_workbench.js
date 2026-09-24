#!/usr/bin/env node
/**
 * 工作台端到端取证：真实登录 → 打开 /workbench → 抓控制台错误 / 接口状态 → 截图。
 * 用法：node scripts/verify_workbench.js
 */
const WebSocket = require('websocket').w3cwebsocket;
const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const SITE = 'https://yexingchen.cn';
const EMAIL = 'admin@yexingchen.cn';
const PASSWORD = 'Chen@12345678';
const OUT_DIR = path.join(__dirname, '..', 'artifacts');

let ws, msgId = 0;
const consoleErrors = [];
const failedRequests = [];
const apiResponses = {};

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

function httpJson(url, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const req = https.request(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) },
    }, (res) => {
      let b = '';
      res.on('data', (c) => b += c);
      res.on('end', () => { try { resolve(JSON.parse(b)); } catch (e) { reject(new Error('bad json: ' + b.slice(0, 200))); } });
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

function chromeRunning() {
  return new Promise((resolve) => {
    const req = http.get('http://localhost:9222/json', () => resolve(true));
    req.on('error', () => resolve(false));
    req.setTimeout(2000, () => { req.destroy(); resolve(false); });
  });
}

async function launchChrome() {
  const paths = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  ];
  const exe = paths.find((p) => fs.existsSync(p));
  if (!exe) throw new Error('Chrome not found');
  const dir = path.join(process.env.TEMP || '/tmp', 'chrome-verify-' + Date.now());
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
      if (url.includes('/api/')) {
        if (status >= 400) failedRequests.push(`${status} ${url}`);
        apiResponses[url] = status;
      }
    }
    if (m.method === 'Network.loadingFailed') {
      failedRequests.push('LOADFAIL ' + (m.params.errorText || '') + ' ' + (m.params.requestId || ''));
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
  console.log('== 1. login via API ==');
  const login = await httpJson(SITE + '/api/auth/login', { email: EMAIL, password: PASSWORD });
  if (login.code !== 0 || !login.data?.token) throw new Error('login failed: ' + JSON.stringify(login).slice(0, 300));
  const token = login.data.token;
  console.log('  token ok, len =', token.length);

  if (!(await chromeRunning())) await launchChrome();
  await connect();

  console.log('== 2. open site & inject token ==');
  await send('Page.navigate', { url: SITE + '/login' });
  await new Promise((r) => setTimeout(r, 5000));
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`);

  console.log('== 3. navigate to /workbench ==');
  consoleErrors.length = 0;
  failedRequests.length = 0;
  await send('Page.navigate', { url: SITE + '/workbench' });
  await new Promise((r) => setTimeout(r, 12000));

  const state = await evalJs(`JSON.stringify({
    url: location.href,
    hasWorkbench: !!document.querySelector('.workbench-page, .workbench-view, [class*="workbench"]'),
    bodyLen: document.body.innerText.length,
    text: document.body.innerText.slice(0, 600)
  })`);
  console.log('== 4. page state ==');
  console.log(state);

  const summary = await evalJs(`(async () => {
    const t = localStorage.getItem('token');
    const r = await fetch('/api/workbench/summary', { headers: { Authorization: 'Bearer ' + t } });
    const txt = await r.text();
    return r.status + ' | ' + txt.slice(0, 500);
  })()`);
  console.log('== 5. /api/workbench/summary ==');
  console.log(summary);

  await shot('workbench.png');

  console.log('== 6. console errors ==');
  console.log(consoleErrors.length ? consoleErrors.join('\n') : '(none)');
  console.log('== 7. failed requests ==');
  console.log(failedRequests.length ? failedRequests.join('\n') : '(none)');

  ws.close();
  process.exit(0);
})().catch((e) => { console.error('[FAIL]', e.message); process.exit(1); });