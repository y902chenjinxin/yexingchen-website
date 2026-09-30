#!/usr/bin/env node
/**
 * 顶栏瘦身 + ⌘K/AI 高级工具迁入「智能」分组 — 取证
 *
 * 覆盖：
 *  A. 桌面 1440×1100：
 *    1) 顶栏右侧只剩「倒计时徽章」「提醒中心」「账号」三个区域
 *    2) 账号下拉含「个人中心 / 背景音乐 / 下载手机软件 / 退出账号」
 *    3) 侧栏「智能」分组含「AI 对话 / 命令面板 / AI 高级工具」三条
 *    4) 点「命令面板」打开命令面板（路径外）；点「AI 高级工具」打开 AI 抽屉
 *  B. 手机 390×844（?m=1）：模块目录「智能」分组含「AI 对话 / 命令面板 / AI 高级工具」
 *
 *  对生产构建产物（4173）取证；与 verify_mobile_modules.js 同套原则：
 *  - dev server 下 transition 行为异常，必须对生产构建做
 *  - Emulation.setFocusEmulationEnabled 拉起 visibility
 */
const WebSocket = require('websocket').w3cwebsocket;
const http = require('http');
const fs = require('fs');
const path = require('path');

const SITE = process.env.SITE || 'http://localhost:4173';
const API = process.env.API || 'http://127.0.0.1:8000';
const EMAIL = 'admin@yexingchen.cn';
const PASSWORD = 'Chen@12345678';

const OUT = path.join(__dirname, '..', 'artifacts');

function httpJson(url, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    // 支持 https（对线上取证时 API = https://yexingchen.cn）
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
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function pumpFrame() {
  const p = send('Page.captureScreenshot', { format: 'jpeg', quality: 20 });
  p.catch(() => {});
  try { await Promise.race([p, sleep(6000).then(() => { throw new Error('frame-timeout') })]); } catch { /* 单帧失败不致命 */ }
}
async function waitFor(selector, timeout = 20000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    const ok = await evalJs(`!!document.querySelector(${JSON.stringify(selector)})`);
    if (ok) return true;
    await pumpFrame(); await sleep(250);
  }
  return false;
}
async function settle(n = 6) {
  for (let i = 0; i < n; i++) { await pumpFrame(); await sleep(120); }
}

async function shot(name) {
  try {
    const r = await Promise.race([
      send('Page.captureScreenshot', { format: 'png' }),
      sleep(8000).then(() => ({ result: { data: '' } })),
    ]);
    if (!r?.result?.data) { console.log('  shot(' + name + '): 跳过（超时/无帧）'); return; }
    fs.mkdirSync(OUT, { recursive: true });
    fs.writeFileSync(path.join(OUT, name), Buffer.from(r.result.data, 'base64'));
    console.log('  shot: artifacts/' + name);
  } catch (e) {
    console.log('  shot(' + name + '): 跳过（' + String(e.message).slice(0, 60) + ')');
  }
}

const READ_TOPBAR = `(() => {
  const tb = document.querySelector('.lj-topbar');
  if (!tb) return 'NO_TOPBAR';
  // 收集所有具备 aria-label 的按钮 + 用户区标题
  const buttons = [...tb.querySelectorAll('.tb-icon-btn[aria-label]')].map(b => b.getAttribute('aria-label'));
  const userHas = !!tb.querySelector('.tb-user');
  const kbd = [...tb.querySelectorAll('.tb-cmd-kbd')].map(e => e.textContent.trim());
  return JSON.stringify({ iconBtns: buttons, userHas, kbdHints: kbd });
})()`;

const READ_USER_PANEL = `(() => {
  // el-dropdown 渲染面板到 body 末尾，但这里我们要找的是 GlobalTopBar 内的下拉面板
  // el-dropdown 用 Popper 弹出，挂在 document.body 末尾，class 是 .el-popper
  // 我们的自定义面板挂在 .tb-user-panel —— 必须从所有 .el-popper 里翻
  const poppers = [...document.querySelectorAll('.el-popper')];
  const out = [];
  for (const p of poppers) {
    if (p.querySelector('.tb-user-panel')) {
      const list = [...p.querySelectorAll('.tb-user-item')].map(li => {
        const label = li.querySelector('span:not(.tb-user-side)')?.textContent.trim();
        return label;
      });
      out.push(list);
    }
  }
  return JSON.stringify(out);
})()`;

const READ_SMART_GROUP = `(() => {
  // 桌面侧栏智能组：找 dsb-group-label 文字为「智能」的下一个 siblings 直到下一组
  const nav = document.querySelector('.dsb-nav');
  if (!nav) return 'NO_SIDEBAR';
  const out = [];
  for (const child of nav.children) {
    if (child.classList.contains('dsb-group-label') && child.textContent.trim() === '智能') {
      let n = child.nextElementSibling;
      while (n && !n.classList.contains('dsb-group-label') && !n.classList.contains('dsb-divider')) {
        const label = n.querySelector('.dsb-label')?.textContent.trim();
        const isAction = n.classList.contains('dsb-action');
        // 快捷键不再行内显示（侧栏 139px 放不下 Shift+Ctrl+A），改从 title 提示里读。
        // 注意：这段是模板字符串，正则里的 \( \) 会被转义吃掉，这里用 indexOf 切片避免踩坑
        const t = n.getAttribute('title') || '';
        const kbd = t.includes('(') ? t.slice(t.indexOf('(') + 1, t.lastIndexOf(')')) : null;
        // 顺带实测字体一致性：链接项与按钮项必须同字族同字号，且标签不被截断
        const lab = n.querySelector('.dsb-label');
        const cs = lab ? getComputedStyle(lab) : null;
        const font = cs ? (cs.fontFamily.split(',')[0] + '/' + cs.fontSize) : null;
        const clipped = lab ? lab.scrollWidth > lab.clientWidth + 1 : false;
        if (label) out.push({ label, kind: isAction ? 'action' : 'route', kbd, font, clipped });
        n = n.nextElementSibling;
      }
      break;
    }
  }
  return JSON.stringify(out);
})()`;

const READ_SMART_GROUP_MOBILE = `(() => {
  const groups = [...document.querySelectorAll('.mdl-group')];
  const g = groups.find(x => x.querySelector('.mdl-group__name')?.textContent.trim() === '智能');
  if (!g) return 'NO_SMART_GROUP';
  const cards = [...g.querySelectorAll('.mdl-card')].map(c => ({
    title: c.querySelector('.mdl-card__lab')?.textContent.trim(),
    action: c.classList.contains('mdl-action'),
    kbd: c.querySelector('.mdl-card__kbd')?.textContent.trim() || null,
  }));
  return JSON.stringify(cards);
})()`;

/* 桌面兜底页 /modules：分组网格里的卡片（含 action 按钮） */
const READ_FALLBACK_SMART = `(() => {
  const groups = [...document.querySelectorAll('.mdld-group')];
  const g = groups.find(x => x.querySelector('.mdld-group__name')?.textContent.trim() === '智能');
  if (!g) return 'NO_SMART_GROUP';
  return JSON.stringify([...g.querySelectorAll('.mdld-card')].map(c => ({
    title: c.querySelector('.mdld-card__lab')?.textContent.trim(),
    action: c.classList.contains('mdld-action'),
    kbd: c.querySelector('.mdld-card__kbd')?.textContent.trim() || null,
  })));
})()`;

(async () => {
  const targets = await new Promise((res, rej) => {
    http.get('http://localhost:9222/json', (r) => { let b = ''; r.on('data', (c) => b += c); r.on('end', () => res(JSON.parse(b))); }).on('error', rej);
  });
  const page = targets.find((t) => t.type === 'page') || targets[0];
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  await send('Runtime.enable'); await send('Page.enable');
  await send('Emulation.setFocusEmulationEnabled', { enabled: true });

  // 清掉旧 SW & cache
  await send('Page.navigate', { url: SITE + '/' });
  await sleep(1800);
  await evalJs(`(async () => { const rs = await navigator.serviceWorker.getRegistrations(); for (const r of rs) await r.unregister(); const ks = await caches.keys(); for (const k of ks) await caches.delete(k); })();`);

  console.log('=== 0. 登录 ===');
  const login = await httpJson(API + '/api/auth/login', { email: EMAIL, password: PASSWORD });
  if (login.code !== 0 || !login.data?.token) throw new Error('login failed');
  const token = login.data.token;

  /* ------------ 桌面段 ------------ */
  console.log('\n=== 1. 桌面顶栏（1440×1100）===');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: SITE + '/login?m=0' });
  await sleep(3500);
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)})`);
  await sleep(300);
  // 必须整页导航：SPA 内 router.push 时 auth store 已在「无 token」状态下启动过，
  // 路由守卫会立刻把 /workbench 打回 /login（表现为 probe 里 p=/login、无侧栏）。
  // 整页跳转让应用带着 localStorage 里的 token 冷启动。
  await send('Page.navigate', { url: SITE + '/workbench?m=0' });
  await sleep(6000);

  const probe = await evalJs(`JSON.stringify({ p: location.pathname, tb: !!document.querySelector('.lj-topbar'), sb: !!document.querySelector('.dsb-nav'), vis: document.visibilityState })`);
  console.log('  probe:', probe);
  await waitFor('.lj-topbar', 15000);
  await settle(4);
  const topbar = JSON.parse(await evalJs(READ_TOPBAR));
  console.log('  顶栏图标按钮:', topbar.iconBtns.join(' / ') || '(none)');
  console.log('  用户区存在  :', topbar.userHas);
  console.log('  ⌘K 提示残留 :', topbar.kbdHints.length ? topbar.kbdHints.join(' / ') : '(none — 已删除)');
  if (topbar.iconBtns.length !== 1 || topbar.iconBtns[0] !== '提醒中心') {
    throw new Error('顶栏瘦身未到位：期望只剩「提醒中心」一个 icon-btn，实际 ' + JSON.stringify(topbar.iconBtns));
  }
  if (topbar.kbdHints.length > 0) throw new Error('顶栏还残留 ⌘K 提示');
  if (!topbar.userHas) throw new Error('顶栏缺用户区');
  await shot('topbar_slim.png');

  console.log('\n=== 2. 账号下拉 ===');
  // 点击 .tb-user
  await evalJs(`document.querySelector('.tb-user').click()`);
  await sleep(800);
  await settle(3);
  const userPanel = JSON.parse(await evalJs(READ_USER_PANEL));
  console.log('  账号下拉条目:', JSON.stringify(userPanel[0] || userPanel));
  await shot('topbar_user_panel.png');

  console.log('\n=== 3. 桌面侧栏「智能」分组 ===');
  const smart = JSON.parse(await evalJs(READ_SMART_GROUP));
  console.log('  智能分组条目:');
  smart.forEach((it) => console.log('   -', it.label.padEnd(12, ' '), (it.kind === 'action' ? `[action kbd=${it.kbd}]` : '[route]').padEnd(22, ' '), it.font, it.clipped ? '❌截断' : '✅完整'));
  const expectSmart = ['AI 对话', '命令面板', 'AI 高级工具'];
  if (JSON.stringify(smart.map(s => s.label)) !== JSON.stringify(expectSmart)) {
    throw new Error('智能分组内容不符：期望 ' + JSON.stringify(expectSmart) + ' 实际 ' + JSON.stringify(smart.map(s => s.label)));
  }
  const actions = smart.filter(s => s.kind === 'action');
  if (actions.length !== 2) throw new Error('智能分组 action 项数应 = 2，实际 ' + actions.length);
  // 字体必须全组一致：RouterLink 项与 <button> 项的 font-family / font-size 不能分叉
  const fonts = [...new Set(smart.map(s => s.font))];
  if (fonts.length !== 1) throw new Error('同组字体不一致：' + JSON.stringify(smart.map(s => s.label + '=' + s.font)));
  // 标签不能被快捷键标签挤到截断
  const clipped = smart.filter(s => s.clipped).map(s => s.label);
  if (clipped.length) throw new Error('侧栏标签被截断：' + JSON.stringify(clipped));
  // 快捷键仍可从 title 提示读到，且内容正确
  if (actions.some(a => !a.kbd)) throw new Error('action 项缺 title 快捷键提示');
  if (actions.map(a => a.kbd).join('/') !== 'Ctrl+K/Shift+Ctrl+A') {
    throw new Error('title 快捷键提示不符：' + JSON.stringify(actions.map(a => a.kbd)));
  }

  console.log('\n=== 4. 侧栏点「命令面板」触发面板 ===');
  // 关掉账号下拉避免干扰
  await evalJs(`document.body.click()`);
  await sleep(400);
  await evalJs(`(() => { const btn = [...document.querySelectorAll('.dsb-action')].find(b => b.textContent.includes('命令面板')); if (btn) btn.click(); return !!btn; })()`);
  await sleep(1200);
  const cmdOpen = await evalJs(`(document.querySelector('.cp-panel') ? 'ok-panel' : '(no panel)')`);
  console.log('  命令面板出现 :', cmdOpen.slice(0, 80));
  if (cmdOpen === '(no panel)') throw new Error('侧栏点「命令面板」未打开面板');
  await shot('topbar_smart_cmd.png');
  // 关掉命令面板（按 Esc）
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
  await sleep(400);

  console.log('\n=== 5. 侧栏点「AI 高级工具」触发抽屉 ===');
  await evalJs(`(() => { const btn = [...document.querySelectorAll('.dsb-action')].find(b => b.textContent.includes('AI 高级工具')); if (btn) btn.click(); return !!btn; })()`);
  await sleep(1200);
  const aiOpen = await evalJs(`(document.querySelector('.aid-mask') ? 'ok-ai' : '(no drawer)')`);
  console.log('  AI 抽屉出现  :', aiOpen.slice(0, 80));
  if (aiOpen === '(no drawer)') throw new Error('侧栏点「AI 高级工具」未打开抽屉');
  await shot('topbar_smart_ai.png');
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
  await sleep(400);

  /* ------------ 手机段 ------------ */
  console.log('\n=== 6. 手机外壳（390×844 + 触控仿真）===');
  await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 3, mobile: true });
  await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  await send('Page.navigate', { url: SITE + '/workbench?m=1' });
  await sleep(3500);
  await waitFor('.mt-tabbar');
  await settle(4);
  console.log('  is-mobile :', await evalJs(`document.getElementById('app').classList.contains('is-mobile')`));

  console.log('\n=== 7. 手机模块页「智能」分组 ===');
  await evalJs(`[...document.querySelectorAll('.mt-tab')].find(b => b.textContent.includes('模块'))?.click()`);
  await waitFor('.mdl-group');
  await settle(4);
  const smartM = JSON.parse(await evalJs(READ_SMART_GROUP_MOBILE));
  console.log('  智能分组卡片:', JSON.stringify(smartM));
  // 手机端没有命令面板 / AI 抽屉（App.vue 里 v-if="!isMobile"），动作项应被过滤掉，
  // 否则就是「点一下什么也不发生」的空卡片
  if (smartM.length !== 1 || smartM[0].title !== 'AI 对话') {
    throw new Error('手机智能分组应只剩「AI 对话」，实际 ' + JSON.stringify(smartM.map(c => c.title)));
  }
  if (smartM.some(c => c.action)) throw new Error('手机智能分组不应出现 action 卡片');
  await shot('topbar_smart_mobile.png');

  console.log('\n=== 8. 桌面 /modules 兜底页「智能」分组 ===');
  // ⚠️ 必须整页跳转并带 ?m=0：第 6 步的 ?m=1 会写入 localStorage 强制标记，
  //    且 useIsMobile 只在挂载/ resize 时重算 —— SPA 内 push 路由不会重算，会一直停在手机分支
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });
  await send('Emulation.setTouchEmulationEnabled', { enabled: false });
  await send('Page.navigate', { url: SITE + '/modules?m=0' });
  await sleep(3500);
  const fallbackOk = await waitFor('.mdld-grid', 15000);
  if (!fallbackOk) throw new Error('桌面 /modules 未渲染兜底网格（.mdld-grid 未出现）');
  await settle(4);
  const smartF = JSON.parse(await evalJs(READ_FALLBACK_SMART));
  console.log('  兜底页智能分组:', JSON.stringify(smartF));
  const expectF = ['AI 对话', '命令面板', 'AI 高级工具'];
  if (JSON.stringify(smartF.map(c => c.title)) !== JSON.stringify(expectF)) {
    throw new Error('兜底页智能分组内容不符：' + JSON.stringify(smartF.map(c => c.title)));
  }
  if (smartF.filter(c => c.action).length !== 2) throw new Error('兜底页 action 卡片应 = 2');
  if (smartF.filter(c => c.action).some(c => !c.kbd)) throw new Error('兜底页 action 卡片缺快捷键标签');
  console.log('  快捷键标签  :', smartF.filter(c => c.action).map(c => c.kbd).join(' / '));
  await shot('topbar_fallback_modules.png');

  console.log('\n=== 9. 兜底页点「命令面板」/「AI 高级工具」 ===');
  await evalJs(`(() => { const btn = [...document.querySelectorAll('.mdld-action')].find(b => b.textContent.includes('命令面板')); if (btn) btn.click(); return !!btn; })()`);
  await sleep(1200);
  const cmdOpenF = await evalJs(`(document.querySelector('.cp-panel') ? 'ok-panel-f' : '(no panel)')`);
  console.log('  命令面板出现 :', cmdOpenF);
  if (cmdOpenF === '(no panel)') throw new Error('兜底页点「命令面板」未打开面板');
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
  await sleep(500);
  await evalJs(`(() => { const btn = [...document.querySelectorAll('.mdld-action')].find(b => b.textContent.includes('AI 高级工具')); if (btn) btn.click(); return !!btn; })()`);
  await sleep(1200);
  const aiOpenF = await evalJs(`(document.querySelector('.aid-mask') ? 'ok-ai-f' : '(no drawer)')`);
  console.log('  AI 抽屉出现  :', aiOpenF);
  if (aiOpenF === '(no drawer)') throw new Error('兜底页点「AI 高级工具」未打开抽屉');
  await shot('topbar_fallback_ai.png');

  ws.close();
  process.exit(0);
})().catch((e) => { console.error('[FAIL]', e.message); process.exit(1); });