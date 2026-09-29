#!/usr/bin/env node
/**
 * 生活模块拆菜单实测（v2.41）：/life → 重定向；体重记录 / 美食记忆两页渲染、
 * 侧栏高亮、卡片三键、大图预览灯箱、移动端 375px 无横向溢出。
 *
 * 前置：Chrome 以 --remote-debugging-port=9222 启动（headless 亦可）。
 * 截图落在 artifacts/life_*.png
 */
const WebSocket = require('websocket').w3cwebsocket;
const http = require('http');
const https = require('https');
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

const results = [];
function check(name, ok, detail = '') {
  results.push([name, ok, detail]);
  console.log(`  [${ok ? 'PASS' : 'FAIL'}] ${name}${detail ? ' — ' + detail : ''}`);
}

function loginApi() {
  const { email, password } = loadCreds()
  if (!email || !password) throw new Error('缺少凭据：请设置 YX_EMAIL / YX_PASSWORD，或提供 ../.secrets/local.env');
  const body = JSON.stringify({ email, password });
  return new Promise((res, rej) => {
    const req = https.request({
      hostname: 'yexingchen.cn', path: '/api/auth/login', method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) },
    }, (r) => { let b = ''; r.on('data', (c) => b += c); r.on('end', () => { try { res(JSON.parse(b).data.token); } catch (e) { rej(e); } }); });
    req.on('error', rej); req.write(body); req.end();
  });
}

/** 轮询等元素出现：固定 sleep 等异步取数不可靠 */
async function waitFor(sel, timeout = 15000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    if (await evalJs(`!!document.querySelector(${JSON.stringify(sel)})`)) return true;
    await new Promise((r) => setTimeout(r, 400));
  }
  return false;
}

async function goto(route, sel, waitMs = 1800) {
  errors = []; failed = [];
  await send('Page.navigate', { url: 'https://yexingchen.cn' + route });
  await new Promise((r) => setTimeout(r, 1200));
  await waitFor(sel, 18000);
  await new Promise((r) => setTimeout(r, waitMs));
}

const bodyText = () => evalJs('document.body.innerText');
const activeNav = () => evalJs(`(() => { const a = document.querySelector('.dsb-item.active .dsb-label'); return a ? a.textContent.trim() : '' })()`);
const overflowX = () => evalJs('document.documentElement.scrollWidth - document.documentElement.clientWidth');

(async () => {
  const targets = await new Promise((res, rej) => {
    http.get('http://localhost:9222/json', (r) => { let b = ''; r.on('data', (c) => b += c); r.on('end', () => res(JSON.parse(b))); }).on('error', rej);
  });
  const page = targets.find((t) => t.type === 'page');
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

  const token = await loginApi();
  await send('Page.navigate', { url: 'https://yexingchen.cn/login' });
  await new Promise((r) => setTimeout(r, 2500));
  await evalJs(`localStorage.setItem('token', ${JSON.stringify(token)}); 'ok'`);

  // ---------- 1. /life 重定向 ----------
  console.log('\n== 1. /life 旧路由重定向 ==');
  await goto('/life', '.life-members-head', 1200);
  const url1 = await evalJs('location.pathname');
  check('跳转到 /life/weight', url1 === '/life/weight', `实际 ${url1}`);
  check('页面含「体重记录」', (await bodyText()).includes('体重记录'));
  check('侧栏高亮落在「体重记录」', (await activeNav()) === '体重记录', `实际「${await activeNav()}」`);
  check('无控制台错误', errors.length === 0, errors.slice(0, 2).join(' | '));
  check('无接口 4xx/5xx', failed.length === 0, failed.slice(0, 2).join(' | '));
  await shot('life_weight.png');

  // ---------- 2. 体重记录页 ----------
  console.log('\n== 2. /life/weight 体重记录 ==');
  await goto('/life/weight', '.life-members-head', 1500);
  const t2 = await bodyText();
  check('含体重汇总表', t2.includes('体重汇总'));
  check('含体重趋势/明细', t2.includes('体重趋势') && t2.includes('体重明细'));
  check('工具栏是「＋ 记体重」', t2.includes('记体重'));
  check('不再出现「三餐」字样', !t2.includes('三餐'), t2.includes('三餐') ? '仍有残留' : '');
  check('侧栏同时有「体重记录」「美食记忆」两项', (await evalJs(`Array.from(document.querySelectorAll('.dsb-item .dsb-label')).map(e=>e.textContent.trim()).filter(t=>t==='体重记录'||t==='美食记忆').length`)) === 2);
  check('无控制台错误', errors.length === 0, errors.slice(0, 2).join(' | '));
  check('无接口 4xx/5xx', failed.length === 0, failed.slice(0, 2).join(' | '));
  check('1440px 无横向溢出', (await overflowX()) <= 0, `溢出 ${await overflowX()}px`);
  await shot('life_weight_full.png');

  // ---------- 3. 美食记忆页 ----------
  console.log('\n== 3. /life/meals 美食记忆 ==');
  await goto('/life/meals', '.life-meal', 2000);
  const t3 = await bodyText();
  check('标题为「美食记忆」', t3.includes('美食记忆'));
  check('含只记大餐的说明文案', t3.includes('只记大餐与值得纪念的一顿'));
  check('含美食汇总表', t3.includes('美食汇总'));
  check('工具栏是「📷 记一顿」', t3.includes('记一顿'));
  check('侧栏高亮落在「美食记忆」', (await activeNav()) === '美食记忆', `实际「${await activeNav()}」`);
  const cards = await evalJs(`document.querySelectorAll('.meal-card').length`);
  check('渲染出美食卡片', cards > 0, `${cards} 张`);
  const ops = await evalJs(`document.querySelector('.meal-card') ? Array.from(document.querySelectorAll('.meal-card')[0].querySelectorAll('.meal-op')).map(b=>b.textContent.trim()) : []`);
  check('卡片有 预览/编辑/删除 三键', JSON.stringify(ops) === JSON.stringify(['预览', '编辑', '删除']), JSON.stringify(ops));
  check('汇总表列头是场合而非早午晚', t3.includes('大餐') && t3.includes('纪念日') && t3.includes('旅行') && t3.includes('家常'));
  check('无控制台错误', errors.length === 0, errors.slice(0, 2).join(' | '));
  check('无接口 4xx/5xx', failed.length === 0, failed.slice(0, 2).join(' | '));
  await shot('life_meals.png');

  // ---------- 4. 大图预览灯箱 ----------
  console.log('\n== 4. 大图预览灯箱 ==');
  await evalJs(`document.querySelector('.meal-card .meal-img-wrap').click(); 'ok'`);
  await new Promise((r) => setTimeout(r, 700));
  const lbOpen = await evalJs(`!!document.querySelector('.meal-lb')`);
  check('灯箱已打开', lbOpen);
  const lbImg = await evalJs(`(() => { const i = document.querySelector('.meal-lb-img'); return i ? { w: i.naturalWidth, h: i.naturalHeight } : null })()`);
  check('灯箱大图已加载（naturalWidth>0）', !!lbImg && lbImg.w > 0, JSON.stringify(lbImg));
  const lbBtns = await evalJs(`Array.from(document.querySelectorAll('.meal-lb-btn')).map(b=>b.textContent.trim())`);
  check('灯箱内有 编辑/删除/关闭', JSON.stringify(lbBtns) === JSON.stringify(['编辑', '删除', '关闭']), JSON.stringify(lbBtns));
  await shot('life_meals_lightbox.png');
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
  await new Promise((r) => setTimeout(r, 600));
  check('Esc 可关闭灯箱', !(await evalJs(`!!document.querySelector('.meal-lb')`)));

  // ---------- 5. 编辑弹窗预填 ----------
  console.log('\n== 5. 编辑弹窗 ==');
  await evalJs(`document.querySelector('.meal-card .meal-op:nth-child(2)').click(); 'ok'`);
  await new Promise((r) => setTimeout(r, 800));
  const dlgTitle = await evalJs(`(() => { const t = document.querySelector('.el-dialog__title'); return t ? t.textContent.trim() : '' })()`);
  check('弹窗标题为「编辑美食记忆」', dlgTitle === '编辑美食记忆', `实际「${dlgTitle}」`);
  const radioTxt = await evalJs(`Array.from(document.querySelectorAll('.el-dialog .el-radio-button__inner')).map(e=>e.textContent.trim())`);
  check('场合选项为新四类（+旧值兜底）', radioTxt.some((t) => t.includes('大餐')) && radioTxt.some((t) => t.includes('纪念日')), JSON.stringify(radioTxt));
  const hasPreview = await evalJs(`!!document.querySelector('.el-dialog .meal-photo-preview img')`);
  check('编辑弹窗已带出原图预览', hasPreview);
  const saveBtn = await evalJs(`(() => { const b = Array.from(document.querySelectorAll('.el-dialog__footer .el-button')).pop(); return b ? b.textContent.trim() : '' })()`);
  check('主按钮文案为「保存」', saveBtn === '保存', `实际「${saveBtn}」`);
  await shot('life_meals_edit.png');
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
  await new Promise((r) => setTimeout(r, 500));

  // ---------- 6. 移动端 375px ----------
  console.log('\n== 6. 移动端 375px ==');
  await send('Emulation.setDeviceMetricsOverride', { width: 375, height: 812, deviceScaleFactor: 2, mobile: true });
  await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  await goto('/life/meals', '.life-meal', 2000);
  check('375px 无横向溢出', (await overflowX()) <= 0, `溢出 ${await overflowX()}px`);
  check('卡片操作键常显（触屏无 hover）', (await evalJs(`(() => { const o = document.querySelector('.meal-op'); return o ? getComputedStyle(o).opacity : 'none' })()`)) === '1');
  await shot('life_meals_375.png');
  await goto('/life/weight', '.life-members-head', 1500);
  check('体重页 375px 无横向溢出', (await overflowX()) <= 0, `溢出 ${await overflowX()}px`);
  await shot('life_weight_375.png');

  console.log('\n== 汇总 ==');
  const bad = results.filter((r) => !r[1]);
  console.log(`  ${results.length - bad.length}/${results.length} 通过`);
  bad.forEach(([n]) => console.log('  FAIL:', n));
  process.exit(bad.length ? 1 : 0);
})().catch((e) => { console.error('FATAL', e); process.exit(2); });