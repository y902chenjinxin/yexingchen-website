#!/usr/bin/env node
/**
 * v2.42 公私账端到端取证（生产环境）。
 *
 * 两层，缺一层不算证明：
 *   ① API 契约层：/finance/funds 口径、/finance/transfer 写入→余额变化→删除→余额回滚、
 *      非法调拨被拒；写入的探针流水最后必须删干净（软删除，funds 口径天然排除）。
 *   ② 可见层：真实登录 → /finance/book，池子卡/Tab/调拨表单/流水徽标是否真的渲染出来，
 *      池子卡数字与 API 是否一致，手机端 375px 是否横向溢出。
 *
 * 用法：node scripts/verify_funds.js
 * 前置：Chrome 可用（脚本会自行拉起 9222）；生产站点可达。
 */
const WebSocket = require('websocket').w3cwebsocket;
const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const SITE = 'https://yexingchen.cn';
/** 凭据读取：优先环境变量 YX_EMAIL / YX_PASSWORD，否则读 <repo>/../.secrets/local.env。
 *  ⚠️ 不要把生产账号密码写进脚本 —— 本仓库是公开仓库（见 docs/ISSUES.md V2441-005）。 */
function loadCreds() {
  let email = process.env.YX_EMAIL;
  let password = process.env.YX_PASSWORD;
  if (!email || !password) {
    try {
      const seg = fs.readFileSync(path.join(__dirname, '..', '..', '.secrets', 'local.env'), 'utf8')
        .split('#项目网站信息').pop();
      email = email || (seg.match(/账号：\s*(\S+)/) || [])[1];
      password = password || (seg.match(/密码：\s*(\S+)/) || [])[1];
    } catch { /* 读不到时交给调用方报错 */ }
  }
  return { email, password };
}
const OUT_DIR = path.join(__dirname, '..', 'artifacts');
const PROBE_NOTE = '__verify_funds_probe__';

let ws, msgId = 0;
const consoleErrors = [];
const failedRequests = [];
const results = [];

function check(name, ok, detail) {
  results.push({ name, ok, detail });
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++msgId;
    ws.send(JSON.stringify({ id, method, params }));
    const h = (e) => { const r = JSON.parse(e.data); if (r.id === id) { ws.removeEventListener('message', h); resolve(r); } };
    ws.addEventListener('message', h);
    setTimeout(() => { ws.removeEventListener('message', h); reject(new Error('timeout ' + method)); }, 30000);
  });
}

const evalJs = async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result?.result?.value;

function req(method, url, body, token) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : null;
    const headers = {};
    if (data) { headers['Content-Type'] = 'application/json'; headers['Content-Length'] = Buffer.byteLength(data); }
    if (token) headers.Authorization = 'Bearer ' + token;
    const r = https.request(url, { method, headers }, (res) => {
      let b = '';
      res.on('data', (c) => b += c);
      res.on('end', () => {
        let json = null;
        try { json = JSON.parse(b); } catch {}
        resolve({ status: res.statusCode, json, raw: b.slice(0, 300) });
      });
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
  const exe = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  ].find((p) => fs.existsSync(p));
  if (!exe) throw new Error('Chrome not found');
  const dir = path.join(process.env.TEMP || '/tmp', 'chrome-verify-' + Date.now());
  console.log('[browser] launching Chrome');
  spawn(exe, ['--remote-debugging-port=9222', '--no-first-run', '--no-default-browser-check', `--user-data-dir=${dir}`], { detached: true, stdio: 'ignore' }).unref();
  await new Promise((r) => setTimeout(r, 4500));
}

async function connect() {
  const targets = await new Promise((resolve, reject) => {
    http.get('http://localhost:9222/json', (res) => {
      let b = ''; res.on('data', (c) => b += c); res.on('end', () => resolve(JSON.parse(b)));
    }).on('error', reject);
  });
  const page = targets.find((t) => t.type === 'page') || targets[0];
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
      consoleErrors.push((m.params.args || []).map((a) => a.value || a.description || '').join(' '));
    }
    if (m.method === 'Runtime.exceptionThrown') {
      consoleErrors.push('EXC: ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
    }
    if (m.method === 'Network.responseReceived') {
      const { url, status } = m.params.response;
      if (url.includes('/api/') && status >= 400) failedRequests.push(`${status} ${url}`);
    }
  };
  await send('Runtime.enable'); await send('Page.enable'); await send('Network.enable');
}

async function shot(name) {
  const r = await send('Page.captureScreenshot', { format: 'png' });
  if (!r.result?.data) return;
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(path.join(OUT_DIR, name), Buffer.from(r.result.data, 'base64'));
}

/** 轮询等待条件成立（固定 sleep 在 CDP 下不可靠） */
async function waitFor(expr, timeout = 20000, label = expr) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    const v = await evalJs(`(() => { try { return !!(${expr}) } catch { return false } })()`);
    if (v) return true;
    await new Promise((r) => setTimeout(r, 400));
  }
  console.log(`  [waitFor timeout] ${label}`);
  return false;
}

const poolMap = (funds) => Object.fromEntries((funds.pools || []).map((p) => [p.fund, p]));

(async () => {
  // ============ ① API 契约层 ============
  console.log('\n== ① API 契约（生产）==');
  const { email: EMAIL, password: PASSWORD } = loadCreds();
  if (!EMAIL || !PASSWORD) throw new Error('缺少凭据：请设置 YX_EMAIL / YX_PASSWORD，或提供 ../.secrets/local.env');
  const login = await req('POST', SITE + '/api/auth/login', { email: EMAIL, password: PASSWORD });
  const token = login.json?.data?.token;
  if (!token) throw new Error('login failed: ' + login.raw);
  console.log('  token ok');

  const f0 = (await req('GET', SITE + '/api/finance/funds', null, token)).json?.data;
  check('GET /finance/funds 返回三个池子', (f0?.pools || []).length === 3, (f0?.pools || []).map((p) => p.fund).join(','));
  check('funds.since 为 2026-10（历史流水不参与）', f0?.since === '2026-10', 'since=' + f0?.since);
  const p0 = poolMap(f0);

  // 非法调拨：同池 / 含 none，必须被拒
  const bad1 = await req('POST', SITE + '/api/finance/transfer', { from_fund: 'public', to_fund: 'public', amount: 1 }, token);
  check('同池调拨被拒（code != 0）', bad1.json?.code !== 0, `code=${bad1.json?.code} msg=${bad1.json?.msg || ''}`);
  const bad2 = await req('POST', SITE + '/api/finance/transfer', { from_fund: 'none', to_fund: 'public', amount: 1 }, token);
  check('含 none 的调拨被拒', bad2.json?.code !== 0, `code=${bad2.json?.code} msg=${bad2.json?.msg || ''}`);

  // 真实写入一笔 0.01 元探针调拨：个人零花 → 公款
  const created = await req('POST', SITE + '/api/finance/transfer', {
    from_fund: 'personal', to_fund: 'public', amount: 0.01, note: PROBE_NOTE,
  }, token);
  const probeId = created.json?.data?.id;
  check('POST /finance/transfer 写入成功', created.json?.code === 0 && !!probeId, `id=${probeId} msg=${created.json?.msg || ''}`);

  const f1 = poolMap((await req('GET', SITE + '/api/finance/funds', null, token)).json?.data);
  const dPub = +(f1.public.inflow - p0.public.inflow).toFixed(2);
  const dPer = +(f1.personal.outflow - p0.personal.outflow).toFixed(2);
  check('公款流入 +0.01（转入端记账）', dPub === 0.01, `Δinflow=${dPub}`);
  check('个人零花流出 +0.01（转出端记账）', dPer === 0.01, `Δoutflow=${dPer}`);
  check('余额同步位移（公款 +0.01 / 零花 −0.01）',
    +(f1.public.balance - p0.public.balance).toFixed(2) === 0.01 &&
    +(f1.personal.balance - p0.personal.balance).toFixed(2) === -0.01,
    `pub=${+(f1.public.balance - p0.public.balance).toFixed(2)} per=${+(f1.personal.balance - p0.personal.balance).toFixed(2)}`);

  // 流水列表能查到这笔调拨，且带 fund/fund_to 语义
  const tl = (await req('GET', SITE + '/api/finance/transactions?type=transfer&size=5&page=1', null, token)).json?.data;
  const probeRow = (tl?.list || []).find((r) => r.note === PROBE_NOTE);
  check('流水列表含该调拨且 fund/fund_to 正确',
    !!probeRow && probeRow.fund === 'personal' && probeRow.fund_to === 'public',
    probeRow ? `${probeRow.fund}→${probeRow.fund_to} ${probeRow.fund_label}→${probeRow.fund_to_label}` : 'not found');

  // 删除探针 → 余额回滚
  const del = await req('DELETE', SITE + `/api/finance/transactions/${probeId}`, null, token);
  check('删除探针调拨成功', del.json?.code === 0, `code=${del.json?.code}`);
  const f2 = poolMap((await req('GET', SITE + '/api/finance/funds', null, token)).json?.data);
  check('删除后余额回滚到基线（探针已清理）',
    f2.public.balance === p0.public.balance && f2.personal.balance === p0.personal.balance,
    `pub=${f2.public.balance} per=${f2.personal.balance}`);

  // summary 不应把调拨计进笔数（写入一笔再核对）
  const c0 = (await req('GET', SITE + '/api/finance/summary', null, token)).json?.data;
  const probe2 = await req('POST', SITE + '/api/finance/transfer', { from_fund: 'personal', to_fund: 'public', amount: 0.02, note: PROBE_NOTE }, token);
  const c1 = (await req('GET', SITE + '/api/finance/summary', null, token)).json?.data;
  check('summary 笔数不含调拨', c0?.count === c1?.count, `before=${c0?.count} after=${c1?.count}`);
  await req('DELETE', SITE + `/api/finance/transactions/${probe2.json?.data?.id}`, null, token);

  // ============ ② 可见层 ============
  console.log('\n== ② 真实渲染（浏览器）==');
  if (!(await chromeRunning())) await launchChrome();
  await connect();
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });

  await send('Page.navigate', { url: SITE + '/login' });
  await waitFor(`document.readyState === 'complete'`, 15000, 'login page');
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`);

  consoleErrors.length = 0; failedRequests.length = 0;
  await send('Page.navigate', { url: SITE + '/finance/book' });
  const poolsOk = await waitFor(`document.querySelectorAll('.fin-pool').length === 3`, 25000, '.fin-pool ×3');
  check('记账页渲染出 3 张资金池卡', poolsOk);

  // 池子卡在 funds 回填前会以 0 兜底渲染，必须先等数字与 API 对齐再读数，
  // 否则量到的是加载态（曾误报「卡片 0.00 / 单池看板 -51.90」自相矛盾）。
  const apiPools = poolMap(f0);
  const expectArr = ['savings', 'public', 'personal'].map((f) => apiPools[f].balance.toFixed(2));
  await waitFor(
    `(() => { const e = ${JSON.stringify(expectArr)}; return ['savings','public','personal']
      .every((f, i) => (document.querySelector('.fin-pool.' + f + ' .fin-pool-val')?.innerText || '').includes(e[i])) })()`,
    12000, 'pool cards filled');

  const ui = JSON.parse(await evalJs(`JSON.stringify({
    pools: [...document.querySelectorAll('.fin-pool')].map(b => ({
      cls: b.className, name: b.querySelector('.fin-pool-name')?.innerText.trim(),
      val: b.querySelector('.fin-pool-val')?.innerText.trim(),
      sub: b.querySelector('.fin-pool-sub')?.innerText.trim()
    })),
    tabs: [...document.querySelectorAll('.fin-tabs .fin-tab-item')].map(b => b.innerText.trim()),
    title: document.querySelector('.fin-title')?.innerText.trim()
  })`) || '{}');
  console.log('  pools:', JSON.stringify(ui.pools));
  console.log('  tabs :', JSON.stringify(ui.tabs));

  check('池子卡名称 = 存款/公款/个人零花',
    ui.pools.map((p) => p.name).join(',') === '存款,公款,个人零花', ui.pools.map((p) => p.name).join(','));
  const valOf = (name) => {
    const map = { 存款: 'savings', 公款: 'public', 个人零花: 'personal' };
    return ui.pools.find((p) => p.name === name)?.val;
  };
  const num = (s) => Number((s || '').replace(/[^\d.\-]/g, ''));
  check('池子卡数字与 API 余额一致',
    ['存款', '公款', '个人零花'].every((n) => {
      const f = { 存款: 'savings', 公款: 'public', 个人零花: 'personal' }[n];
      return Math.abs(num(valOf(n)) - (apiPools[f]?.balance ?? NaN)) < 0.005;
    }),
    ui.pools.map((p) => `${p.name}=${p.val}`).join(' '));
  check('Tab 五项齐全（总览/存款/公款/个人/流水）',
    ui.tabs.join(',') === '总览,存款,公款,个人,流水', ui.tabs.join(','));
  await shot('funds_overview.png');

  // 公款 Tab → 单池看板
  await evalJs(`[...document.querySelectorAll('.fin-tabs .fin-tab-item')].find(b => b.innerText.trim() === '公款')?.click()`);
  const heroOk = await waitFor(`document.querySelector('.fin-pool-hero')`, 6000, '.fin-pool-hero');
  const hero = JSON.parse(await evalJs(`JSON.stringify({
    title: document.querySelector('.fin-pool-hero .fin-panel-title')?.innerText.trim(),
    val: document.querySelector('.fin-pool-hero-val')?.innerText.trim(),
    table: !!document.querySelector('.fin-mtable'),
    placeholder: document.querySelector('.fin-chart-empty')?.innerText.trim() || '',
    chart: !!document.querySelector('.fin-chart')
  })`) || '{}');
  check('点「公款」出现单池看板且标题/余额正确',
    heroOk && hero.title === '公款' && Math.abs(num(hero.val) - (apiPools.public?.balance ?? NaN)) < 0.005,
    JSON.stringify(hero));
  // 矩阵只统计「转入」（income→池 / transfer→池）；若 API 该池确无转入行，
  // 页面显示空态才是正确行为（公款余额可能纯由支出形成），不能要求有表。
  const hasInflowRows = (f0.monthly_by_member || []).some((r) => r.fund === 'public');
  check('单池看板「各人各月转入」与 API 一致（有转入→出表，无转入→空态）',
    hasInflowRows ? hero.table : hero.placeholder === '还没有转入记录',
    `apiInflowRows=${hasInflowRows} table=${hero.table} placeholder="${hero.placeholder}"`);
  await shot('funds_public.png');

  // 流水 Tab → 徽标 + 筛选
  await evalJs(`[...document.querySelectorAll('.fin-tabs .fin-tab-item')].find(b => b.innerText.trim() === '流水')?.click()`);
  await waitFor(`document.querySelector('.fin-ledger')`, 6000, '.fin-ledger');
  await waitFor(`document.querySelectorAll('.fin-row').length > 0`, 10000, '.fin-row');
  const led = JSON.parse(await evalJs(`JSON.stringify({
    rows: document.querySelectorAll('.fin-row').length,
    badges: [...document.querySelectorAll('.fin-fund-badge')].slice(0, 6).map(b => b.innerText.trim()),
    checks: document.querySelectorAll('.fin-row-check input').length,
    ops: document.querySelectorAll('.fin-row-ops .fin-op').length
  })`) || '{}');
  check('流水行带资金池徽标', led.badges.length > 0, JSON.stringify(led.badges));
  check('流水行可勾选（批量改归属入口）', led.checks > 0, `checks=${led.checks}`);
  check('流水行保留编辑/删除按钮', led.ops >= 2, `ops=${led.ops}`);
  await shot('funds_ledger.png');

  // 批量改归属条：勾一行后出现
  await evalJs(`document.querySelector('.fin-row-check input')?.click()`);
  const batchOk = await waitFor(`document.querySelector('.fin-batch')`, 5000, '.fin-batch');
  const batchText = await evalJs(`document.querySelector('.fin-batch')?.innerText.replace(/\\s+/g,' ').trim()`);
  check('勾选后出现批量改归属条', batchOk, batchText);
  await shot('funds_batch.png');
  await evalJs(`document.querySelector('.fin-batch-clear')?.click()`);

  // 记一笔 → 调拨表单 + 快捷标签
  await evalJs(`[...document.querySelectorAll('.fin-btn.primary')].find(b => b.innerText.includes('记一笔'))?.click()`);
  await waitFor(`document.querySelector('.fin-form')`, 6000, '.fin-form');
  const typeTabs = await evalJs(`JSON.stringify([...document.querySelectorAll('.fin-f-type .fin-tab')].map(b => b.innerText.trim()))`);
  check('记一笔含 支出/收入/调拨 三态', JSON.parse(typeTabs || '[]').join(',') === '支出,收入,调拨', typeTabs);
  await evalJs(`[...document.querySelectorAll('.fin-f-type .fin-tab')].find(b => b.innerText.trim() === '调拨')?.click()`);
  const transferOk = await waitFor(`document.querySelector('.fin-transfer-row')`, 5000, '.fin-transfer-row');
  const tags = JSON.parse(await evalJs(`JSON.stringify([...document.querySelectorAll('.fin-quick-tag')].map(b => b.innerText.trim()))`) || '[]');
  check('调拨态出现「转出 → 转入」双向选择', transferOk && (await evalJs(`document.querySelectorAll('.fin-transfer-sel').length`)) === 2);
  check('调拨快捷理由标签 4 个', tags.join(',') === '公款补充,月末归集,临时周转,个人退款', tags.join(','));
  await evalJs(`document.querySelector('.fin-quick-tag')?.click()`);
  const tagOn = await evalJs(`!!document.querySelector('.fin-quick-tag.on')`);
  check('点快捷标签可选中（写入备注）', tagOn);
  await shot('funds_transfer_form.png');
  // 关闭表单，绝不留脏数据
  await evalJs(`document.querySelector('.fin-form-close')?.click()`);

  // 手机端 375px 回归
  console.log('\n== ③ 手机端 375px ==');
  // 注意：v2.40.30 起移动端外壳**只认 APK 的 XuanHuangApp UA**，手机浏览器一律走桌面版，
  // 所以「窄屏 + 触控模拟」在桌面 Chrome 里判定必然为 false —— 这不是 bug。
  // 要验移动端样式，必须走应用自带的逃生口 `?m=1`（写入 localStorage 强制移动端）。
  await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  await send('Emulation.setDeviceMetricsOverride', { width: 375, height: 812, deviceScaleFactor: 2, mobile: true });
  await send('Page.navigate', { url: SITE + '/finance/book?m=1' });
  await waitFor(`document.querySelectorAll('.fin-pool').length === 3`, 25000, 'mobile .fin-pool ×3');
  const mob = JSON.parse(await evalJs(`JSON.stringify({
    isMobile: document.querySelector('#app')?.classList.contains('is-mobile'),
    scrollW: document.documentElement.scrollWidth,
    clientW: document.documentElement.clientWidth,
    poolsScroll: (() => { const el = document.querySelector('.fin-pools'); return el ? el.scrollWidth > el.clientWidth : null })(),
    poolValVisible: !!document.querySelector('.fin-pool-val')?.getBoundingClientRect().width
  })`) || '{}');
  check('?m=1 下走移动端外壳', mob.isMobile === true, 'is-mobile=' + mob.isMobile);
  check('375px 无横向溢出', mob.scrollW <= mob.clientW + 1, `scrollW=${mob.scrollW} clientW=${mob.clientW}`);
  check('手机端池子卡为可横滑一行', mob.poolsScroll === true, 'scrollable=' + mob.poolsScroll);
  await shot('funds_mobile.png');
  await send('Emulation.clearDeviceMetricsOverride');
  await evalJs(`localStorage.removeItem('xuanhuang_force_mobile')`);

  console.log('\n== 控制台错误 ==');
  console.log(consoleErrors.length ? consoleErrors.slice(0, 5).join('\n') : '(none)');
  console.log('== 4xx/5xx 接口 ==');
  console.log(failedRequests.length ? failedRequests.slice(0, 5).join('\n') : '(none)');

  const bad = results.filter((r) => !r.ok);
  console.log(`\n===== ${results.length - bad.length}/${results.length} 通过 =====`);
  if (bad.length) { console.log('未通过：'); bad.forEach((b) => console.log('  - ' + b.name + ' — ' + (b.detail || ''))); }

  ws.close();
  process.exit(bad.length ? 1 : 0);
})().catch((e) => { console.error('[FAIL]', e.message); process.exit(1); });
