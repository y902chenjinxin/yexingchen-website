#!/usr/bin/env node
/**
 * browser_verify.js
 * 自动化浏览器验证 - 根据代码变动自动判断测试范围
 *
 * 使用方式：
 *   node browser_verify.js                    # 自动检测改动并测试
 *   node browser_verify.js --all             # 强制测试全部
 *   node browser_verify.js --changed         # 只测试改动的（默认）
 *
 * 退出码：0 = 成功, 1 = 失败
 */
const WebSocket = require('websocket').w3cwebsocket;
const http = require('http');
const { spawn, execSync } = require('child_process');
const path = require('path');

let ws;
let msgId = 0;
let failures = [];

// ============================================
// 测试函数定义（独立模块）
// ============================================

const testModules = {
  login: {
    name: '登录流程',
    files: ['LoginView.vue'],
    async run() {
      console.log('[1] Testing login flow...');

      // 检查是否已登录，已登录则跳过
      const alreadyLoggedIn = await send('Runtime.evaluate', {
        expression: 'window.location.href.includes("/home")'
      });
      if (alreadyLoggedIn.result.result.value) {
        console.log('   [SKIP] Already logged in, skipping login test');
        return;
      }

      await send('Page.navigate', { url: 'https://yexingchen.cn' });
      await new Promise(r => setTimeout(r, 3000));

      const loginPageLoaded = await send('Runtime.evaluate', {
        expression: 'document.getElementById("app").innerHTML.includes("login-page")'
      });
      check('Login page loaded', loginPageLoaded.result.result.value);

      await send('Runtime.evaluate', {
        expression: `(() => {
          const emailInput = document.querySelector('input[type=text], input[type="text"]');
          if (!emailInput) return 'no email input';
          const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
          nativeInputValueSetter.call(emailInput, "admin@yexingchen.cn");
          emailInput.dispatchEvent(new Event("input", { bubbles: true }));
          return 'email set';
        })()`
      });
      await send('Runtime.evaluate', {
        expression: `(() => {
          const passwordInput = document.querySelector('input[type=password]');
          const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
          nativeInputValueSetter.call(passwordInput, "Chen@12345678");
          passwordInput.dispatchEvent(new Event("input", { bubbles: true }));
        })()`
      });
      await send('Runtime.evaluate', { expression: 'document.querySelector("button[type=submit]").click()' });
      await new Promise(r => setTimeout(r, 5000));

      const afterLoginURL = await send('Runtime.evaluate', { expression: 'window.location.href' });
      check('Login successful, redirected to home', afterLoginURL.result.result.value.includes('/home'));
    }
  },

  mouse: {
    name: '鼠标轨迹',
    files: ['MouseTrail.vue'],
    async run() {
      console.log('\n[3] Testing mouse trail effect...');

      const mouseMoves = [
        { x: 300, y: 200 }, { x: 500, y: 350, steps: 8 },
        { x: 700, y: 450, steps: 8 }, { x: 900, y: 550, steps: 8 },
        { x: 400, y: 400, steps: 8 }, { x: 600, y: 300, steps: 8 },
      ];
      for (const move of mouseMoves) {
        await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: move.x, y: move.y });
        if (move.steps) await new Promise(r => setTimeout(r, 100));
      }
      await new Promise(r => setTimeout(r, 600));

      const mouseTrail = await send('Runtime.evaluate', {
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

      const mouseTrailResult = JSON.parse(mouseTrail.result.result.value);
      check('Mouse trail canvas found', mouseTrailResult.found);
      check('Mouse trail particles rendering (' + mouseTrailResult.nonTransparent + ')', mouseTrailResult.nonTransparent > 50);
      check('Mouse trail color correct (翡翠绿)', mouseTrailResult.greenishPixels > 20);
    }
  },

  islands: {
    name: '岛屿系统',
    files: ['HomeView.vue', 'IslandDetail.vue'],
    async run() {
      console.log('\n[2] Checking home page elements...');

      const homeViewLoaded = await send('Runtime.evaluate', {
        expression: 'document.querySelector(".home-page, .home-view") !== null'
      });
      check('Home view loaded', homeViewLoaded.result.result.value);

      const islandsExist = await send('Runtime.evaluate', {
        expression: 'document.querySelectorAll(".island, .island-pos").length >= 5'
      });
      check('All 5 islands rendered', islandsExist.result.result.value);

      const topBar = await send('Runtime.evaluate', {
        expression: 'document.querySelector(".top-bar") !== null'
      });
      check('Top bar exists', topBar.result.result.value);

      console.log('\n[4] Testing island hover effects...');
      const hoverEffect = await send('Runtime.evaluate', {
        expression: 'document.querySelector(".music-island-hover, .novel-island-hover, .video-island-hover, .log-island-hover, .tool-island-hover") !== null'
      });
      check('Island hover effect exists', hoverEffect.result.result.value);

      console.log('\n[5] Testing island navigation...');
      const islandSelectors = [
        '[class*="music-island"]',
        '[class*="novel-island"]',
        '[class*="video-island"]',
        '[class*="log-island"]',
        '[class*="tool-island"]'
      ];

      for (const selector of islandSelectors) {
        const islandExists = await send('Runtime.evaluate', {
          expression: `document.querySelector('${selector}') !== null`
        });
        if (islandExists.result.result.value) {
          await clickElement(selector);
          const navSuccess = await send('Runtime.evaluate', {
            expression: 'window.location.href.includes("music") || window.location.href.includes("novel") || window.location.href.includes("video") || window.location.href.includes("log") || window.location.href.includes("tool")'
          });
          check(`Navigation to ${selector} works`, navSuccess.result.result.value);
          await send('Runtime.evaluate', { expression: 'window.history.back()' });
          await new Promise(r => setTimeout(r, 1000));
        }
      }
    }
  },

  decorations: {
    name: '装饰层',
    files: ['DecorationsLayer.vue'],
    async run() {
      console.log('\n[6] Testing decoration layer...');

      const decorations = await send('Runtime.evaluate', {
        expression: 'document.querySelector(".decorations-layer, .lantern, .crane, .rune-fragment") !== null'
      });
      check('Decoration layer elements exist', decorations.result.result.value);
    }
  },

  fortune: {
    name: '每日运势',
    files: ['DailyFortune.vue'],
    async run() {
      console.log('\n[7] Testing daily fortune seal...');

      const fortune = await send('Runtime.evaluate', {
        expression: 'document.querySelector(".daily-fortune, .fortune-header, .fortune-content") !== null'
      });
      check('Daily fortune seal exists', fortune.result.result.value);
    }
  },

  celestial: {
    name: '天象系统',
    files: ['SkyLayer.vue', 'CelestialSystem.vue'],
    async run() {
      console.log('\n[8] Testing celestial system...');

      const celestial = await send('Runtime.evaluate', {
        expression: 'document.querySelector(".sky-layer, .stars-container, .star") !== null'
      });
      check('Celestial/stars system exists', celestial.result.result.value);
    }
  },

  css: {
    name: 'CSS变量',
    files: ['variables.css', '*.css'],
    async run() {
      console.log('\n[9] Checking CSS variables...');

      const cssVars = await send('Runtime.evaluate', {
        expression: `(() => {
          var styles = getComputedStyle(document.documentElement);
          return JSON.stringify({
            qiGreen: styles.getPropertyValue('--color-qi-green').trim(),
            goldBright: styles.getPropertyValue('--color-gold-bright').trim(),
            bgPrimary: styles.getPropertyValue('--color-bg-primary').trim()
          });
        })()`
      });

      const cssResult = JSON.parse(cssVars.result.result.value);
      check('--color-qi-green is set', cssResult.qiGreen.length > 0);
      check('--color-gold-bright is set', cssResult.goldBright.length > 0);
    }
  },

  mobile: {
    name: '移动端适配',
    files: ['*.vue', '*.css'],
    async run() {
      console.log('\n[10] Testing mobile viewport...');

      await send('Emulation.setDeviceMetricsOverride', {
        width: 375,
        height: 667,
        deviceScaleFactor: 1,
        mobile: true
      });
      await new Promise(r => setTimeout(r, 1000));

      const mobileLayout = await send('Runtime.evaluate', {
        expression: 'document.documentElement.scrollWidth <= 375 + 20'
      });
      check('Mobile layout (375px) - no horizontal overflow', mobileLayout.result.result.value);

      await send('Emulation.setDeviceMetricsOverride', {
        width: 1920,
        height: 1080,
        deviceScaleFactor: 1,
        mobile: false
      });
    }
  }
};

// ============================================
// 核心函数
// ============================================

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

function check(msg, condition) {
  if (condition) {
    console.log(`   [OK] ${msg}`);
    return true;
  } else {
    console.log(`   [FAIL] ${msg}`);
    failures.push(msg);
    return false;
  }
}

async function clickElement(selector) {
  await send('Runtime.evaluate', {
    expression: `document.querySelector('${selector}').click()`
  });
  await new Promise(r => setTimeout(r, 1000));
}

async function checkChromeRunning() {
  return new Promise((resolve) => {
    const req = http.get('http://localhost:9222/json', (res) => {
      resolve(true);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(2000, () => { req.destroy(); resolve(false); });
  });
}

async function launchChrome() {
  const chromePaths = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    '/c/Program Files/Google/Chrome/Application/chrome.exe',
    '/c/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  ];

  let chromePath = null;
  for (const p of chromePaths) {
    try { require('fs').accessSync(p); chromePath = p; break; } catch (e) {}
  }

  if (!chromePath) throw new Error('Chrome not found');

  const debugPort = 9222;
  const userDataDir = path.join(process.env.TEMP || '/tmp', 'chrome-debug-' + Date.now());

  console.log('[Browser] Launching Chrome...');
  const chrome = spawn(chromePath, [
    `--remote-debugging-port=${debugPort}`,
    '--no-first-run',
    '--no-default-browser-check',
    `--user-data-dir=${userDataDir}`,
  ], { detached: true, stdio: 'ignore' });
  chrome.unref();
  await new Promise(r => setTimeout(r, 4000));
}

// ============================================
// Git变动检测
// ============================================

function getChangedFiles() {
  try {
    const output = execSync('git diff --name-only HEAD~1 HEAD', {
      encoding: 'utf-8',
      cwd: process.cwd()
    });
    return output.trim().split('\n').filter(f => f.length > 0);
  } catch (e) {
    return [];
  }
}

function matchTests(changedFiles) {
  const testsToRun = new Set();

  for (const file of changedFiles) {
    for (const [key, mod] of Object.entries(testModules)) {
      const isMatch = mod.files.some(pattern => {
        if (pattern.includes('*')) {
          const regex = new RegExp('^' + pattern.replace('*', '.*') + '$');
          return regex.test(file) || file.endsWith('.vue') || file.endsWith('.css');
        }
        return file.includes(pattern);
      });
      if (isMatch) {
        testsToRun.add(key);
      }
    }
  }

  // 未知文件或无改动，测试全部
  if (testsToRun.size === 0) {
    console.log('[Info] No specific changes detected, will test all');
    for (const key of Object.keys(testModules)) {
      testsToRun.add(key);
    }
  }

  return testsToRun;
}

// ============================================
// 主流程
// ============================================

async function verify() {
  const args = process.argv.slice(2);
  const forceAll = args.includes('--all');

  console.log('============================================================');
  console.log('  [Verify] Browser Verification - yexingchen.cn');
  console.log('============================================================\n');

  // 检测代码变动
  const changedFiles = forceAll ? [] : getChangedFiles();
  const testsToRun = forceAll
    ? new Set(Object.keys(testModules))
    : matchTests(changedFiles);

  console.log('[Git] Changed files:', changedFiles.length > 0 ? changedFiles.join(', ') : '(none, testing all)');
  console.log('[Test] Will run:', [...testsToRun].map(k => testModules[k]?.name || k).join(', '));
  console.log('');

  // 1. 确保 Chrome 运行中
  const isRunning = await checkChromeRunning();
  if (!isRunning) {
    await launchChrome();
    console.log('');
  } else {
    console.log('[Browser] Chrome already running\n');
  }

  // 2. 连接 Chrome
  const targets = await new Promise((resolve, reject) => {
    http.get('http://localhost:9222/json', res => {
      let body = ''; res.on('data', chunk => body += chunk); res.on('end', () => resolve(JSON.parse(body)));
    }).on('error', reject);
  });

  const target = targets.find(t => t.type === 'page' && !t.url.includes('newtab')) || targets[0];
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  await send('Runtime.enable');
  await send('Page.enable');

  // 3. 确保已登录
  await send('Page.navigate', { url: 'https://yexingchen.cn/home' });
  await new Promise(r => setTimeout(r, 2000));

  // 4. 执行测试
  for (const testKey of testsToRun) {
    const mod = testModules[testKey];
    if (mod && mod.run) {
      try {
        await mod.run();
      } catch (e) {
        console.log(`   [ERROR] ${mod.name}: ${e.message}`);
        failures.push(`${mod.name} - ${e.message}`);
      }
    }
  }

  // 5. 汇总结果
  console.log('\n============================================================');
  console.log('  [Result] Verification Summary');
  console.log('============================================================');

  if (failures.length === 0) {
    console.log('  [PASS] All checks passed!');
    console.log('============================================================\n');
    ws.close();
    process.exit(0);
  } else {
    console.log(`  [FAIL] ${failures.length} check(s) failed:`);
    failures.forEach(f => console.log(`    - ${f}`));
    console.log('============================================================\n');
    ws.close();
    process.exit(1);
  }
}

verify().catch(e => {
  console.error('[FAIL]', e.message);
  process.exit(1);
});