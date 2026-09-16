// 将 app-icon.svg 渲成无水印 1024x1024 PNG（供 APK mipmap 烘焙）
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const svg = path.resolve(__dirname, 'app-icon.svg');
  const out = path.resolve(__dirname, 'app-icon-1024.png');
  const browser = await chromium.launch({
    executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  });
  const page = await browser.newPage({ viewport: { width: 1024, height: 1024 }, deviceScaleFactor: 1 });
  await page.goto('file://' + svg.replace(/\\/g, '/'));
  await page.waitForTimeout(150);
  await page.screenshot({ path: out, omitBackground: true });
  await browser.close();
  console.log('OK ->', out);
})();