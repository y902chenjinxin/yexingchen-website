#!/usr/bin/env node
/**
 * 手机端「全部模块」目录取证 + 桌面侧栏零回归取证。
 *
 * 覆盖：
 *  1. 桌面 1440×1100：侧栏分组/条目结构与改动前一致（读 DOM 文本），记账高亮落在「生活」分组
 *  2. 手机 390×844（触控仿真 + ?m=1 强制移动外壳）：底部三 Tab、模块页一级/二级结构、
 *     二级滑动条可横向滚动、滑到末尾渐隐消失、点二级卡片能进目标页
 *  3. 全程收集控制台错误；截图落 artifacts/
 *
 * 依赖：本地后端 127.0.0.1:8000 + **生产构建产物预览 4173** + 带 --remote-debugging-port=9222 的 Chrome
 *
 * 为什么不用 vite dev（5173）跑这份取证：
 *   dev server 下 `<transition mode="out-in">` + `<keep-alive>` 的路由切换会「leave 走完、enter 不进来」，
 *   切页后 router-view 直接空掉（线上生产构建同代码无此问题，已实测 yexingchen.cn 正常）。
 *   取证要对着**真正会部署的产物**做，故先 `npm run build` 再 `npx vite preview`（端口 4173）。
 *   SITE 可用环境变量覆盖。
 */
const WebSocket = require('websocket').w3cwebsocket;
const http = require('http');
const fs = require('fs');
const path = require('path');
/** 凭据读取：优先环境变量 YX_EMAIL / YX_PASSWORD，否则读 <repo>/../.secrets/local.env。
 *  ⚠️ 不要把生产账号密码写进脚本 —— 本仓库是**公开仓库**（见 docs/ISSUES.md V2441-005）。 */
function loadCreds() {
  let email = process.env.YX_EMAIL
  let password = process.env.YX_PASSWORD
  if (!email || !password) {
    try {
      const seg = fs.readFileSync(path.join(__dirname, '..', '..', '.secrets', 'local.env'), 'utf8')
        .split('#项目网站信息').pop()
      email = email || (seg.match(/账号：\s*(\S+)/) || [])[1]
      password = password || (seg.match(/密码：\s*(\S+)/) || [])[1]
    } catch { /* 读不到时交给调用方报错 */ }
  }
  return { email, password }
}


const SITE = process.env.SITE || 'http://localhost:4173';
const API = 'http://127.0.0.1:8000';
// 凭据不写进仓库（本仓库为公开仓库）
const { email: EMAIL, password: PASSWORD } = loadCreds();

const OUT = path.join(__dirname, '..', 'artifacts');

function httpJson(url, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const req = http.request(url, {
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
  setTimeout(() => { ws.removeEventListener('message', h); rej(new Error('timeout ' + m)); }, 60000);
});
const evalJs = async (e) => (await send('Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true })).result?.result?.value;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * 强制出一帧。
 *
 * 背景/最小化窗口里 `document.visibilityState === 'hidden'`，rAF 被浏览器节流到几乎不触发，
 * 而 Vue 的 `<transition mode="out-in">` 靠 rAF 推进（enter-from → enter-to → 清理），
 * 于是路由切换会**永久卡在 leave 阶段**：URL 变了，router-view 里还是旧页面。
 * 截图会驱动合成器产帧，从而让 rAF 恢复 —— 每轮轮询顺带截一帧即可解开。
 * 这是取证环境的限制，真机/前台浏览器不受影响。
 */
async function pumpFrame() {
  const p = send('Page.captureScreenshot', { format: 'jpeg', quality: 20 });
  p.catch(() => {});
  try {
    await Promise.race([p, sleep(6000).then(() => { throw new Error('frame-timeout') })]);
  } catch { /* 单帧失败不致命，下一轮再来 */ }
}

/** 轮询等待选择器出现（固定 sleep 在异步取数场景不可靠），每轮顺带出帧 */
async function waitFor(selector, timeout = 20000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    const ok = await evalJs(`!!document.querySelector(${JSON.stringify(selector)})`);
    if (ok) return true;
    await pumpFrame();
    await sleep(250);
  }
  return false;
}

/** 连出 n 帧，让 out-in 过渡走完（leave + enter 各需 rAF） */
async function settle(n = 6) {
  for (let i = 0; i < n; i++) { await pumpFrame(); await sleep(120); }
}

/** 交互前确保页面可见，否则过渡必卡（导航后 focus 仿真可能被重置，这里兜底重设一次） */
async function ensureVisible(tag = '') {
  const vis = await evalJs(`document.visibilityState`);
  if (vis === 'visible') return true;
  await send('Emulation.setFocusEmulationEnabled', { enabled: true });
  await sleep(500);
  const vis2 = await evalJs(`document.visibilityState`);
  console.log(`  [可见性${tag ? ' ' + tag : ''}] ${vis} → ${vis2}`);
  return vis2 === 'visible';
}

async function shot(name) {
  const r = await send('Page.captureScreenshot', { format: 'png' });
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, name), Buffer.from(r.result.data, 'base64'));
  console.log('  shot: artifacts/' + name);
}

let errs = [];
const READ_SIDEBAR = `(() => {
  const nav = document.querySelector('.dsb-nav');
  if (!nav) return 'NO_SIDEBAR';
  const out = []; let cur = null;
  for (const el of nav.children) {
    if (el.classList.contains('dsb-group-label')) { cur = { group: el.textContent.trim(), items: [] }; out.push(cur); }
    else if (el.classList.contains('dsb-item')) {
      const label = el.querySelector('.dsb-label')?.textContent.trim();
      if (!cur) { cur = { group: '(无分组)', items: [] }; out.push(cur); }
      cur.items.push(label + (el.classList.contains('active') ? ' ★active' : ''));
    }
  }
  return JSON.stringify(out);
})()`;

const READ_MODULES = `(() => {
  const page = document.querySelector('.mdl');
  if (!page) return 'NO_MODULES_PAGE';
  const groups = [...page.querySelectorAll('.mdl-group')].map((g) => {
    const strip = g.querySelector('.mdl-strip');
    return {
      name: g.querySelector('.mdl-group__name')?.textContent.trim(),
      count: g.querySelectorAll('.mdl-card').length,
      labels: [...g.querySelectorAll('.mdl-card__lab')].map((x) => x.textContent.trim()),
      overflow: strip ? (strip.scrollWidth - strip.clientWidth) : -1,
    };
  });
  return JSON.stringify({
    title: page.querySelector('.mdl-title')?.textContent.trim(),
    sub: page.querySelector('.mdl-sub')?.textContent.trim(),
    groups,
  });
})()`;

(async () => {
  const targets = await new Promise((res, rej) => {
    http.get('http://localhost:9222/json', (r) => { let b = ''; r.on('data', (c) => b += c); r.on('end', () => res(JSON.parse(b))); }).on('error', rej);
  });
  const page = targets.find((t) => t.type === 'page') || targets[0];
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') errs.push((m.params.args || []).map((a) => a.value || a.description || '').join(' '));
    if (m.method === 'Runtime.exceptionThrown') errs.push('EXC: ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
  };
  await send('Runtime.enable'); await send('Page.enable');

  /*
   * 让「被遮挡 / 最小化」的调试窗口对页面表现为「可见且聚焦」。
   *
   * 没有这一步，`document.visibilityState` 恒为 hidden，Chrome 会**完全停发 rAF**
   * （实测 1.2s 只跳 1 帧），Vue 的 `<transition mode="out-in">` 卡在 leave 阶段：
   * URL 变了、router-view 里还是旧页面 —— 看起来像「模块页没渲染」，其实是取证环境的坑。
   * 真机 / 前台浏览器不受影响。setFocusEmulationEnabled 实测能把 visibilityState 翻成
   * visible 并让 rAF 恢复到 ~180fps。
   */
  await send('Emulation.setFocusEmulationEnabled', { enabled: true });

  // 清掉上一轮遗留的 Service Worker 与缓存：预览站点同样注册 SW，
  // 不清会拿旧 index / 旧 chunk，看到的是上一次的产物
  await send('Page.navigate', { url: SITE + '/' });
  await sleep(1800);
  await evalJs(`(async () => {
    try {
      const rs = await navigator.serviceWorker.getRegistrations();
      await Promise.all(rs.map(r => r.unregister()));
      const ks = await caches.keys();
      await Promise.all(ks.map(k => caches.delete(k)));
    } catch {}
    return 1;
  })()`);

  console.log('=== 0. 登录 ===');
  const login = await httpJson(API + '/api/auth/login', { email: EMAIL, password: PASSWORD });
  if (login.code !== 0 || !login.data?.token) throw new Error('login failed: ' + JSON.stringify(login).slice(0, 200));
  const token = login.data.token;

  /* ---------------- 桌面端：侧栏零回归 ---------------- */
  console.log('\n=== 1. 桌面侧栏（1440×1100）===');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: SITE + '/login?m=0' });
  await sleep(3500);
  // 把 token 写进 localStorage 后等一拍再跳；写完后用 SPA 内部 push 而非 Page.navigate，
  // 这样 Vue 路由层仍在内存里，pinia 重读 localStorage 后守卫直接放行，不再重触发一次 onMounted 重置 store
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`);
  await sleep(300);
  await evalJs(`(() => { const a=document.getElementById('app-root').__vue_app__; a.config.globalProperties.$router.push('/workbench'); return 1; })()`);

  errs = [];
  await sleep(2500);
  const okNav = await waitFor('.dsb-nav', 20000);
  if (!okNav) {
    const probeRes = await send('Runtime.evaluate', { expression: `JSON.stringify({ dsb: (document.querySelector('.dsb-nav')||{}).children?.length || 0, mc: document.getElementById('main-content')?.className || '-', p: location.pathname, vis: document.visibilityState })`, returnByValue: true, awaitPromise: true });
    throw new Error('桌面侧栏未渲染 — probe=' + (probeRes?.result?.result?.value || JSON.stringify(probeRes?.error || probeRes)));
  }
  await sleep(1500);
  const sb = await evalJs(READ_SIDEBAR);
  if (sb === 'NO_SIDEBAR') throw new Error('桌面侧栏未渲染');
  JSON.parse(sb).forEach((x) => console.log(`  【${x.group}】 ${x.items.join(' / ')}`));
  await shot('modules_desktop_sidebar.png');

  console.log('\n=== 2. 桌面侧栏高亮（/finance/book）===');
  await evalJs(`window.__r = document.querySelector('#app').__vue_app__ ? 1 : 0`);
  await evalJs(`history.pushState({}, '', '/finance/book'); window.dispatchEvent(new PopStateEvent('popstate'))`);
  await sleep(2500);
  const sb2 = await evalJs(READ_SIDEBAR);
  if (sb2 !== 'NO_SIDEBAR') {
    const grp = JSON.parse(sb2);
    const hit = grp.find((x) => x.items.some((i) => i.includes('记账') && i.includes('★active')));
    console.log('  记账高亮落在分组:', hit ? hit.group : '(未高亮)');
    const life = grp.find((x) => x.group === '生活');
    console.log('  生活分组条目数:', life ? life.items.length : '(缺失)');
  }
  console.log('  控制台错误:', errs.length ? errs.slice(0, 3).join(' | ') : '(none)');

  /* ---------------- 手机端：模块目录 ---------------- */
  console.log('\n=== 3. 手机外壳（390×844 + 触控仿真）===');
  await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 3, mobile: true });
  await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });

  errs = [];
  await send('Page.navigate', { url: SITE + '/workbench?m=1' });
  await waitFor('.mt-tabbar');
  await ensureVisible('手机端');
  await settle(6);
  console.log('  移动外壳:', await evalJs(`document.getElementById('app').classList.contains('is-mobile')`));
  console.log('  底部 Tab:', await evalJs(`JSON.stringify([...document.querySelectorAll('.mt-tab .mt-lab')].map(e=>e.textContent.trim()))`));
  await shot('modules_mobile_home.png');

  console.log('\n=== 4. 模块目录页 ===');
  await ensureVisible('点 Tab 前');
  await evalJs(`[...document.querySelectorAll('.mt-tab')].find(b=>b.textContent.includes('模块'))?.click()`);
  const ok = await waitFor('.mdl-group');
  if (!ok) throw new Error('模块页未渲染');
  await settle(4);
  console.log('  路由:', await evalJs(`location.pathname`));

  const raw = await evalJs(READ_MODULES);
  if (raw === 'NO_MODULES_PAGE') throw new Error('模块页结构缺失');
  const data = JSON.parse(raw);
  console.log('  标题:', data.title, '|', data.sub);
  let total = 0;
  data.groups.forEach((g) => {
    total += g.count;
    console.log(`  【${g.name}】 ${g.count} 项 (溢出 ${g.overflow}px) → ${g.labels.join(' / ')}`);
  });
  console.log('  二级模块合计:', total);
  await shot('modules_mobile_directory.png');

  console.log('\n=== 5. 二级滑动条可横向滚动 ===');
  const swipe = await evalJs(`(() => {
    const g = [...document.querySelectorAll('.mdl-group')].find(x => x.querySelector('.mdl-group__name')?.textContent.trim() === '生活');
    const s = g.querySelector('.mdl-strip');
    const before = s.scrollLeft;
    const max = s.scrollWidth - s.clientWidth;
    s.scrollLeft = max;
    return JSON.stringify({ before, max, after: s.scrollLeft });
  })()`);
  console.log('  生活分组 scrollLeft:', swipe);
  await settle(4);
  const fade = await evalJs(`(() => {
    const g = [...document.querySelectorAll('.mdl-group')].find(x => x.querySelector('.mdl-group__name')?.textContent.trim() === '生活');
    const s = g.querySelector('.mdl-strip');
    const f = s.nextElementSibling;
    return JSON.stringify({ atEnd: s.classList.contains('at-end'), fadeOpacity: getComputedStyle(f).opacity });
  })()`);
  console.log('  滑到末尾后:', fade);
  await shot('modules_mobile_swiped.png');

  console.log('\n=== 6. 点二级卡片进目标页 ===');
  await ensureVisible('点卡片前');
  const nav = await evalJs(`(() => {
    const g = [...document.querySelectorAll('.mdl-group')].find(x => x.querySelector('.mdl-group__name')?.textContent.trim() === '内容');
    const card = [...g.querySelectorAll('.mdl-card')].find(c => c.textContent.trim() === '小说');
    if (!card) return 'NO_CARD';
    card.click();
    return 'clicked';
  })()`);
  console.log('  点击「小说」:', nav);
  // 路由切换同样受 out-in 过渡影响，出帧等待目标页接管
  const t0 = Date.now();
  while (Date.now() - t0 < 15000) {
    const st = await evalJs(`JSON.stringify({ p: location.pathname, mdl: !!document.querySelector('.mdl') })`);
    if (JSON.parse(st).p === '/novel' && !JSON.parse(st).mdl) break;
    await pumpFrame();
    await sleep(200);
  }
  console.log('  跳转到:', await evalJs(`location.pathname`));
  console.log('  控制台错误:', errs.length ? errs.slice(0, 5).join(' | ') : '(none)');

  ws.close();
  process.exit(0);
})().catch((e) => { console.error('[FAIL]', e.message); process.exit(1); });
