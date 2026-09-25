#!/usr/bin/env node
/**
 * 家人共享 · 人员标签 + 汇总数据 实测取证。
 * 覆盖：/finance/book（记账）人员标签→筛选联动、/life（体重·三餐）人员标签→筛选联动 + 汇总表。
 * 产出截图到 artifacts/，并打印 DOM 取证结果。
 */
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
  setTimeout(() => { ws.removeEventListener('message', h); reject(new Error('timeout ' + method)); }, 40000);
});
const evalJs = async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result?.result?.value;

let errors = [], failed = [];
const OUT = path.join(__dirname, '..', 'artifacts');

async function shot(name) {
  const r = await send('Page.captureScreenshot', { format: 'png' });
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, name), Buffer.from(r.result.data, 'base64'));
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function goto(route, wait = 9000) {
  errors = []; failed = [];
  await send('Page.navigate', { url: 'https://yexingchen.cn' + route });
  await sleep(wait);
}

/** 轮询等待选择器出现（首屏加载时长不稳，盲等固定秒数会拿到空页面） */
async function waitFor(sel, maxMs = 25000) {
  const t0 = Date.now();
  while (Date.now() - t0 < maxMs) {
    if (await evalJs(`!!document.querySelector('${sel}')`)) return true;
    await sleep(500);
  }
  return false;
}

/** 等路由淡入动画收尾，避免截到半透明中间帧 */
async function settle() {
  for (let i = 0; i < 20; i++) {
    if (!(await evalJs(`!!document.querySelector('[class*="route-fade-enter-active"], [class*="route-fade-leave-active"]')`))) break;
    await sleep(400);
  }
  await sleep(800);
}

/** 抓页面上家人标签 + 汇总表的文本，用于判"有没有真渲染" */
const PROBE_FIN = `JSON.stringify({
  path: location.pathname,
  tags: [...document.querySelectorAll('.fin-mtag')].map(e => e.innerText.replace(/\\n/g,' | ').trim()),
  sumRows: [...document.querySelectorAll('.fin-mtable tbody tr')].map(e => e.innerText.replace(/\\n/g,' | ').trim()),
  chip: document.querySelector('.fin-filter-chip')?.innerText.replace(/\\n/g,' ').trim() || null,
  rowMembers: [...document.querySelectorAll('.fin-row-member')].map(e => e.innerText.trim()).slice(0, 6),
  listRows: document.querySelectorAll('.fin-list .fin-row, .fin-tx-row').length
})`;

const PROBE_LIFE = `JSON.stringify({
  path: location.pathname,
  tags: [...document.querySelectorAll('.life-mtag')].map(e => e.innerText.replace(/\\n/g,' | ').trim()),
  weightSum: [...document.querySelectorAll('.life-sum-card')][0]
    ? [...document.querySelectorAll('.life-sum-card')][0].innerText.replace(/\\n/g,' | ').trim() : null,
  mealSum: [...document.querySelectorAll('.life-sum-card')][1]
    ? [...document.querySelectorAll('.life-sum-card')][1].innerText.replace(/\\n/g,' | ').trim() : null,
  weightRows: [...document.querySelectorAll('.wt-row-title')].map(e => e.innerText.trim()).slice(0, 8),
  mealNames: [...document.querySelectorAll('.meal-name')].map(e => e.innerText.trim()).slice(0, 8)
})`;

/** 把家人区滚进视口，保证截图里能看到标签+汇总表 */
const scrollTo = (sel) => `(() => {
  const el = document.querySelector('${sel}');
  if (!el) return 'NO_EL';
  el.scrollIntoView({ block: 'start' });
  window.scrollBy(0, -20);
  return 'ok';
})()`;

/** 点击第 n 个 .fin-mtag / .life-mtag */
const clickTag = (sel, idx) => `(() => {
  const els = [...document.querySelectorAll('${sel}')];
  if (!els[${idx}]) return 'NO_TAG';
  els[${idx}].click();
  return els[${idx}].innerText.replace(/\\n/g,' | ').trim();
})()`;

(async () => {
  const targets = await new Promise((res, rej) => {
    http.get('http://localhost:9222/json', (r) => { let b = ''; r.on('data', (c) => b += c); r.on('end', () => res(JSON.parse(b))); }).on('error', rej);
  });
  const page = targets.find((t) => t.type === 'page' && t.url.includes('yexingchen.cn')) || targets.find((t) => t.type === 'page');
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') errors.push((m.params.args || []).map((a) => a.value || a.description || '').join(' '));
    if (m.method === 'Runtime.exceptionThrown') errors.push('EXC: ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
    if (m.method === 'Network.responseReceived') { const { url, status } = m.params.response; if (url.includes('/api/') && status >= 400) failed.push(`${status} ${url}`); }
  };
  await send('Runtime.enable'); await send('Page.enable'); await send('Network.enable');
  // 后台标签页 rAF 被节流 → Vue route-fade 卡在 enter-from 半透明态，截图会发暗。
  // 必须先置前，否则拿到的是"看起来页面坏了"的假象。
  await send('Page.bringToFront');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });

  // --- 注入登录态（新 profile 无 token，不注入会跳 /login，DOM 根本不存在）---
  await goto('/login', 4000);
  const tok = await evalJs(`(async () => {
    const r = await fetch('/api/auth/login', { method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ email:'admin@yexingchen.cn', password:'Chen@12345678' }) });
    const j = await r.json();
    localStorage.setItem('token', j.data.token);
    return j.data.token.slice(0, 12);
  })()`);
  console.log('login token injected:', tok);

  // 清 SW + Cache Storage，否则会测到上一版资源（SW 缓存旧 assets 是常见假阴性来源）
  const cleared = await evalJs(`(async () => {
    const rs = await navigator.serviceWorker.getRegistrations();
    for (const r of rs) await r.unregister();
    const ks = await caches.keys();
    for (const k of ks) await caches.delete(k);
    return JSON.stringify({ sw: rs.length, caches: ks.length });
  })()`);
  console.log('sw/cache cleared:', cleared);
  await send('Network.setCacheDisabled', { cacheDisabled: true });

  // ================= /finance/book 记账 =================
  console.log('\n=== /finance/book 记账 · 家人账目 ===');
  await goto('/finance/book', 4000);
  console.log('  fin-mtag 出现:', await waitFor('.fin-mtag'));
  await settle();
  console.log('  [默认/全部家人]', await evalJs(PROBE_FIN));
  console.log('  scroll:', await evalJs(scrollTo('.fin-members')));
  await sleep(900);
  await shot('fam_fin_book_all.png');

  const clickedFin = await evalJs(clickTag('.fin-mtag', 1));
  await sleep(2500);
  console.log('  [点击标签]', clickedFin);
  console.log('  [筛选后]', await evalJs(PROBE_FIN));
  console.log('  errors:', errors.length ? errors.slice(0, 3).join(' | ') : '(none)');
  console.log('  failed api:', failed.length ? failed.slice(0, 5).join(' | ') : '(none)');
  await shot('fam_fin_book_filtered.png');

  // ================= /life 体重·三餐 =================
  console.log('\n=== /life 生活岛 · 体重/三餐家人汇总 ===');
  await goto('/life', 4000);
  console.log('  life-mtag 出现:', await waitFor('.life-mtag'));
  await settle();
  console.log('  [默认/全部家人]', await evalJs(PROBE_LIFE));
  console.log('  scroll:', await evalJs(scrollTo('.life-members')));
  await sleep(900);
  await shot('fam_life_all.png');

  const clickedLife = await evalJs(clickTag('.life-mtag', 1));
  await sleep(2500);
  console.log('  [点击标签]', clickedLife);
  console.log('  [筛选后]', await evalJs(PROBE_LIFE));
  console.log('  errors:', errors.length ? errors.slice(0, 3).join(' | ') : '(none)');
  console.log('  failed api:', failed.length ? failed.slice(0, 5).join(' | ') : '(none)');
  await evalJs(scrollTo('.life-members'));
  await sleep(700);
  await shot('fam_life_filtered.png');

  // ================= 移动端 375px =================
  console.log('\n=== mobile 375px ===');
  await send('Emulation.setDeviceMetricsOverride', { width: 375, height: 812, deviceScaleFactor: 2, mobile: true });
  for (const [route, img] of [['/finance/book', 'fam_m_fin.png'], ['/life', 'fam_m_life.png']]) {
    errors = []; failed = [];
    await goto(route, 9000);
    const m = JSON.parse(await evalJs(`JSON.stringify({ sw: document.documentElement.scrollWidth, tags: document.querySelectorAll('.fin-mtag, .life-mtag').length })`));
    console.log(`  ${route}  scrollWidth=${m.sw} ${m.sw <= 395 ? 'OK(no overflow)' : 'OVERFLOW!'}  tags=${m.tags}  errors=${errors.length}  apiFail=${failed.length}`);
    await shot(img);
  }
  await send('Emulation.clearDeviceMetricsOverride');

  ws.close();
  process.exit(0);
})().catch((e) => { console.error('[FAIL]', e.message); process.exit(1); });