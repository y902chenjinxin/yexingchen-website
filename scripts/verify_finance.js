#!/usr/bin/env node
/** 财经模块路由实测：/finance/* 四页 + 旧路由重定向，抓接口状态/控制台错误/截图。 */
const WebSocket = require('websocket').w3cwebsocket;
const http = require('http');
const fs = require('fs');
const path = require('path');

let ws, msgId = 0;
const send = (method, params = {}) => new Promise((resolve, reject) => {
  const id = ++msgId;
  ws.send(JSON.stringify({ id, method, params }));
  const h = (e) => { const r = JSON.parse(e.data); if (r.id === id) { ws.removeEventListener('message', h); resolve(r); } };
  ws.addEventListener('message', h);
  setTimeout(() => { ws.removeEventListener('message', h); reject(new Error('timeout ' + method)); }, 30000);
});
const evalJs = async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result?.result?.value;

let errors = [], failed = [];
const OUT = path.join(__dirname, '..', 'artifacts');

async function shot(name) {
  const r = await send('Page.captureScreenshot', { format: 'png' });
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, name), Buffer.from(r.result.data, 'base64'));
}

(async () => {
  const targets = await new Promise((res, rej) => {
    http.get('http://localhost:9222/json', (r) => { let b = ''; r.on('data', (c) => b += c); r.on('end', () => res(JSON.parse(b))); }).on('error', rej);
  });
  const page = targets.find((t) => t.type === 'page' && t.url.includes('yexingchen.cn')) || targets[0];
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') errors.push((m.params.args || []).map((a) => a.value || a.description || '').join(' '));
    if (m.method === 'Runtime.exceptionThrown') errors.push('EXC: ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
    if (m.method === 'Network.responseReceived') { const { url, status } = m.params.response; if (url.includes('/api/') && status >= 400) failed.push(`${status} ${url}`); }
  };
  await send('Runtime.enable'); await send('Page.enable'); await send('Network.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

  const routes = [
    ['/finance/overview', 'fin_overview.png'],
    ['/finance/market', 'fin_market.png'],
    ['/finance/news', 'fin_news.png'],
    ['/finance/book', 'fin_book.png'],
    ['/stocks', 'fin_old_stocks.png'],
    ['/feeds', 'fin_old_feeds.png'],
  ];

  for (const [route, img] of routes) {
    errors = []; failed = [];
    await send('Page.navigate', { url: 'https://yexingchen.cn' + route });
    await new Promise((r) => setTimeout(r, 9000));
    const info = await evalJs(`JSON.stringify({ url: location.pathname, len: document.body.innerText.length, head: document.body.innerText.slice(0, 160) })`);
    console.log(`\n### ${route}`);
    console.log('  landed:', info);
    console.log('  errors:', errors.length ? errors.slice(0, 3).join(' | ') : '(none)');
    console.log('  failed api:', failed.length ? failed.slice(0, 5).join(' | ') : '(none)');
    await shot(img);
  }

  console.log('\n=== mobile 375px regression ===');
  await send('Emulation.setDeviceMetricsOverride', { width: 375, height: 812, deviceScaleFactor: 2, mobile: true });
  for (const [route] of routes.slice(0, 4)) {
    errors = []; failed = [];
    await send('Page.navigate', { url: 'https://yexingchen.cn' + route });
    await new Promise((r) => setTimeout(r, 7000));
    const m = await evalJs(`JSON.stringify({ sw: document.documentElement.scrollWidth, len: document.body.innerText.length })`);
    const o = JSON.parse(m);
    console.log(`  ${route}  scrollWidth=${o.sw} ${o.sw <= 395 ? 'OK(no overflow)' : 'OVERFLOW!'}  textLen=${o.len}  errors=${errors.length}  apiFail=${failed.length}`);
  }
  await send('Emulation.clearDeviceMetricsOverride');

  ws.close();
  process.exit(0);
})().catch((e) => { console.error('[FAIL]', e.message); process.exit(1); });