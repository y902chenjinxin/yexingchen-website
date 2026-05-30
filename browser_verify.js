#!/usr/bin/env node
/**
 * browser_verify.js
 * 通过 Chrome DevTools Protocol 完成自动化验证
 * 如果 Chrome 未以调试模式启动，自动启动一个
 *
 * 使用方式：
 *   node browser_verify.js
 *
 * 退出码：0 = 成功, 1 = 失败
 */
const WebSocket = require('websocket').w3cwebsocket;
const http = require('http');
const { spawn, exec } = require('child_process');
const path = require('path');

let ws;
let msgId = 0;

function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++msgId;
    ws.send(JSON.stringify({ id, method, params }));
    const handler = (event) => {
      const response = JSON.parse(event.data);
      if (response.id === id) { ws.removeEventListener('message', handler); resolve(response); }
    };
    ws.addEventListener('message', handler);
    setTimeout(() => { ws.removeEventListener('message', handler); reject(new Error('timeout')); }, 20000);
  });
}

function checkChromeRunning() {
  return new Promise((resolve) => {
    const req = http.get('http://localhost:9222/json', (res) => {
      resolve(true);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(2000, () => { req.destroy(); resolve(false); });
  });
}

function launchChrome() {
  return new Promise((resolve, reject) => {
    // Chrome 安装路径
    const chromePaths = [
      'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
      'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
      '/c/Program Files/Google/Chrome/Application/chrome.exe',
      '/c/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    ];

    let chromePath = null;
    for (const p of chromePaths) {
      try {
        require('fs').accessSync(p);
        chromePath = p;
        break;
      } catch (e) {}
    }

    if (!chromePath) {
      reject(new Error('Chrome not found'));
      return;
    }

    // 使用调试端口启动 Chrome
    const debugPort = 9222;
    const userDataDir = path.join(process.env.TEMP || '/tmp', 'chrome-debug-' + Date.now());

    console.log('[Browser] Launching Chrome with debugging port...');

    const chrome = spawn(chromePath, [
      `--remote-debugging-port=${debugPort}`,
      '--no-first-run',
      '--no-default-browser-check',
      `--user-data-dir=${userDataDir}`,
    ], {
      detached: true,
      stdio: 'ignore'
    });

    chrome.unref();

    // 等待 Chrome 启动
    setTimeout(resolve, 4000);
  });
}

async function verify() {
  // 1. 检查 Chrome 是否运行中
  console.log('[Browser] Checking Chrome debugging port...');
  const isRunning = await checkChromeRunning();

  if (!isRunning) {
    console.log('[Browser] Chrome not running, launching...');
    await launchChrome();
    console.log('[Browser] Chrome launched\n');
  } else {
    console.log('[Browser] Chrome already running with debugging port\n');
  }

  // 2. 获取 Chrome target
  const targets = await new Promise((resolve, reject) => {
    http.get('http://localhost:9222/json', res => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => resolve(JSON.parse(body)));
    }).on('error', reject);
  });

  const target = targets.find(t => t.type === 'page' && !t.url.includes('newtab')) || targets[0];

  // 3. Connect to Chrome
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });

  // 4. Enable domains
  await send('Runtime.enable');
  await send('Page.enable');

  // 5. Navigate to yexingchen.cn
  await send('Page.navigate', { url: 'https://yexingchen.cn' });
  await new Promise(r => setTimeout(r, 3000));

  // 6. Check login and authenticate
  const needsLogin = await send('Runtime.evaluate', {
    expression: 'document.getElementById("app").innerHTML.includes("login-page")'
  });

  if (needsLogin.result.result.value) {
    await send('Runtime.evaluate', {
      expression: `(() => { const emailInput = document.querySelector("input[type=text]"); const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set; nativeInputValueSetter.call(emailInput, "admin@yexingchen.cn"); emailInput.dispatchEvent(new Event("input", { bubbles: true })); })()`
    });
    await send('Runtime.evaluate', {
      expression: `(() => { const passwordInput = document.querySelector("input[type=password]"); const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set; nativeInputValueSetter.call(passwordInput, "Chen@12345678"); passwordInput.dispatchEvent(new Event("input", { bubbles: true })); })()`
    });
    await send('Runtime.evaluate', { expression: 'document.querySelector("button[type=submit]").click()' });
    await new Promise(r => setTimeout(r, 5000));
  }

  // 7. Simulate mouse movement
  const mouseMoves = [
    { x: 300, y: 200 },
    { x: 500, y: 350, steps: 8 },
    { x: 700, y: 450, steps: 8 },
    { x: 900, y: 550, steps: 8 },
    { x: 400, y: 400, steps: 8 },
  ];

  for (const move of mouseMoves) {
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: move.x, y: move.y });
    if (move.steps) await new Promise(r => setTimeout(r, 100));
  }
  await new Promise(r => setTimeout(r, 600));

  // 8. Analyze MouseTrail canvas
  const analysisRaw = await send('Runtime.evaluate', {
    expression: `(function() {
      var canvases = document.querySelectorAll('canvas');
      for (var i = 0; i < canvases.length; i++) {
        var c = canvases[i];
        if (c.className && c.className.includes('mouse-trail')) {
          var ctx = c.getContext('2d');
          var imageData = ctx.getImageData(0, 0, c.width, c.height);
          var n = 0, g = 0;
          for (var j = 0; j < imageData.data.length; j += 4) {
            var r = imageData.data[j], gv = imageData.data[j+1], b = imageData.data[j+2], a = imageData.data[j+3];
            if (a > 0) n++;
            if (a > 50 && gv > 200 && r < 150 && b > 150) g++;
          }
          return JSON.stringify({ found: true, nonTransparent: n, greenishPixels: g });
        }
      }
      return JSON.stringify({ found: false });
    })()`
  });

  const result = JSON.parse(analysisRaw.result.result.value);

  ws.close();

  // 9. Return verification result
  if (!result.found) {
    console.error('[FAIL] MouseTrail canvas not found');
    process.exit(1);
  }

  if (result.nonTransparent < 50) {
    console.error('[FAIL] Insufficient particles:', result.nonTransparent);
    process.exit(1);
  }

  if (result.greenishPixels < 20) {
    console.error('[FAIL] Incorrect color - greenish pixels:', result.greenishPixels);
    process.exit(1);
  }

  console.log('[PASS] Verification passed - particles:', result.nonTransparent, 'greenish:', result.greenishPixels);
  process.exit(0);
}

verify().catch(e => {
  console.error('[FAIL]', e.message);
  process.exit(1);
});