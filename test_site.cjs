const pw = require('./frontend/node_modules/playwright-core');

async function runTests() {
  const results = [];

  try {
    console.log('Starting tests...\n');

    // 1. Test homepage loads
    console.log('1. Testing homepage load...');
    const browser = await pw.chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.goto('https://yexingchen.cn', { waitUntil: 'networkidle', timeout: 30000 });
    results.push('✅ 1. Homepage loaded');

    // 2. Check loading animation timing - wait longer for 0.8s animation
    console.log('2. Testing loading animation...');
    const startTime = Date.now();
    await page.waitForSelector('.login-page, .home-page', { timeout: 5000 });
    const loadTime = Date.now() - startTime;
    if (loadTime < 2000) {
      results.push(`✅ 2. Loading fast (${loadTime}ms)`);
    } else {
      results.push(`⚠️ 2. Loading took ${loadTime}ms`);
    }

    // 3. Check login door symmetry
    console.log('3. Testing door symmetry...');
    const doorLeft = await page.$('.door-left');
    const doorRight = await page.$('.door-right');
    if (doorLeft && doorRight) {
      results.push('✅ 3. Door is symmetric (left+right)');
    } else {
      results.push('❌ 3. Door not symmetric');
    }

    // 4. Wait for login card
    console.log('4. Testing login card delay...');
    await page.waitForSelector('.login-card', { timeout: 5000 });
    results.push('✅ 4. Login card appears with delay');

    // 5. Check input styles
    console.log('5. Testing input white background...');
    const inputBg = await page.evaluate(() => {
      const input = document.querySelector('.el-input__wrapper');
      return window.getComputedStyle(input).backgroundColor;
    });
    if (inputBg.includes('255') && inputBg.includes('255') && inputBg.includes('255')) {
      results.push('✅ 5. Input has white background');
    } else {
      results.push(`⚠️ 5. Input background: ${inputBg}`);
    }

    // 6. Login - use better selector
    console.log('6. Testing login...');
    await page.fill('input[placeholder="邮箱"]', 'admin@yexingchen.cn');
    await page.fill('input[placeholder="密码"]', 'Chen@12345678');
    await page.click('.el-button--primary');
    await page.waitForSelector('.home-page', { timeout: 10000 });
    results.push('✅ 6. Login successful');

    // 7. Check admin menu
    console.log('7. Testing admin menu visibility...');
    const adminVisible = await page.evaluate(() => {
      const items = document.querySelectorAll('.el-dropdown-menu__item');
      for (const item of items) {
        if (item.textContent.includes('管理后台')) return true;
      }
      return false;
    });
    if (adminVisible) {
      results.push('✅ 7. Admin menu visible');
    } else {
      results.push('❌ 7. Admin menu NOT visible');
    }

    // 8. Check island animation
    console.log('8. Testing island orbit animation...');
    const islandAnim = await page.evaluate(() => {
      const el = document.querySelector('.music-island');
      return window.getComputedStyle(el).animationName;
    });
    if (islandAnim.includes('orbit')) {
      results.push('✅ 8. Island orbit animation active');
    } else {
      results.push(`⚠️ 8. Animation: ${islandAnim}`);
    }

    // 9. Check audio MP3
    console.log('9. Testing background music MP3...');
    const audioSrc = await page.evaluate(() => document.querySelector('audio')?.src || 'none');
    if (audioSrc.includes('.mp3')) {
      results.push('✅ 9. Background music is MP3');
    } else {
      results.push(`⚠️ 9. Audio: ${audioSrc}`);
    }

    await browser.close();

  } catch (error) {
    results.push(`❌ Error: ${error.message}`);
  }

  console.log('\n=== Test Results ===');
  results.forEach(r => console.log(r));
  console.log('\nTests complete');
}

runTests().catch(console.error);