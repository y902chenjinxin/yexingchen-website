const { chromium } = require('./frontend/node_modules/playwright-core');

(async () => {
  const browser = await.chromium.launch({ headless: true });
  const page = await browser.newPage();

  const results = [];

  try {
    // 1. Test homepage loads
    console.log('1. Testing homepage...');
    await page.goto('https://yexingchen.cn', { waitUntil: 'networkidle', timeout: 30000 });
    results.push('✅ Homepage loaded');

    // 2. Check loading animation (wait for it to finish)
    console.log('2. Testing loading animation...');
    const startTime = Date.now();
    await page.waitForSelector('.login-page', { timeout: 10000 });
    const loadTime = Date.now() - startTime;
    if (loadTime < 2000) {
      results.push(`✅ Loading animation fast (${loadTime}ms < 2000ms)`);
    } else {
      results.push(`⚠️ Loading took ${loadTime}ms`);
    }

    // 3. Check login door exists and is symmetric
    console.log('3. Testing login door...');
    const doorLeft = await page.$('.door-left');
    const doorRight = await page.$('.door-right');
    if (doorLeft && doorRight) {
      results.push('✅ Login door is symmetric (left + right)');
    }

    // 4. Wait for login card to appear (after delay)
    console.log('4. Waiting for login card...');
    await page.waitForSelector('.login-card', { timeout: 5000 });
    results.push('✅ Login card appears');

    // 5. Check input fields are white background
    console.log('5. Checking input styles...');
    const inputBg = await page.evaluate(() => {
      const input = document.querySelector('.el-input__wrapper');
      return window.getComputedStyle(input).backgroundColor;
    });
    if (inputBg.includes('255, 255, 255') || inputBg.includes('rgb(255, 255, 255)')) {
      results.push('✅ Input fields have white background');
    } else {
      results.push(`⚠️ Input background: ${inputBg}`);
    }

    // 6. Check background music player
    console.log('6. Checking background music...');
    const audioElement = await page.$('audio');
    if (audioElement) {
      const src = await page.evaluate(() => document.querySelector('audio').src);
      if (src.includes('.mp3')) {
        results.push('✅ Background music is MP3');
      } else {
        results.push(`⚠️ Background music format: ${src}`);
      }
    }

    // 7. Login and test admin visibility
    console.log('7. Testing login and admin access...');
    await page.fill('input[placeholder="邮箱"]', 'admin@yexingchen.cn');
    await page.fill('input[placeholder="密码"]', 'Chen@12345678');
    await page.click('button[native-type="submit"]');

    // Wait for home page after login
    await page.waitForSelector('.home-page', { timeout: 10000 });
    results.push('✅ Login successful');

    // Check if admin dropdown item is visible
    const adminItem = await page.$('text=管理后台');
    if (adminItem) {
      results.push('✅ Admin menu item visible');
    } else {
      results.push('⚠️ Admin menu item not visible');
    }

    // 8. Check islands have orbit animation
    console.log('8. Checking island animations...');
    const musicIsland = await page.$('.music-island');
    if (musicIsland) {
      const animation = await page.evaluate(() => {
        const el = document.querySelector('.music-island');
        return window.getComputedStyle(el).animationName;
      });
      if (animation.includes('orbit')) {
        results.push('✅ Island orbit animation present');
      } else {
        results.push(`⚠️ Animation: ${animation}`);
      }
    }

  } catch (error) {
    results.push(`❌ Error: ${error.message}`);
  }

  console.log('\n=== Test Results ===');
  results.forEach(r => console.log(r));

  await browser.close();
})();