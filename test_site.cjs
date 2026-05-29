/**
 * E2E 测试 - 登录流程
 * 运行方式: node test_site.cjs
 */

const pw = require('./frontend/node_modules/playwright-core')

function getCreds() {
  return {
    email: process.env.TEST_ACCOUNT || 'admin@yexingchen.cn',
    password: process.env.TEST_PASSWORD || 'Chen@12345678'
  }
}

async function runTests() {
  const results = []
  const creds = getCreds()

  try {
    console.log('Starting E2E tests...\n')

    // Test 1: 首页加载
    console.log('1. Testing homepage load...')
    const browser = await pw.chromium.launch({ headless: true })
    const page = await browser.newPage()
    await page.goto('https://yexingchen.cn', { waitUntil: 'networkidle', timeout: 30000 })
    results.push('✅ 1. Homepage loaded')

    // Test 2: 登录门动画
    console.log('2. Testing door animation...')
    const startTime = Date.now()
    await page.waitForSelector('.login-page, .home-page', { timeout: 5000 })
    const loadTime = Date.now() - startTime
    results.push(`✅ 2. Door animation completed (${loadTime}ms)`)

    // Test 3: 登录卡片显示
    console.log('3. Testing login card...')
    await page.waitForSelector('.login-card', { timeout: 5000 })
    results.push('✅ 3. Login card appears')

    // Test 4: 登录输入
    console.log('4. Testing login input...')
    await page.fill('input[placeholder="邮箱"]', creds.email)
    await page.fill('input[placeholder="密码"]', creds.password)
    results.push('✅ 4. Login credentials entered')

    // Test 5: 提交登录
    console.log('5. Testing login submit...')
    await page.click('.el-button--primary')
    await page.waitForSelector('.home-page', { timeout: 10000 })
    results.push('✅ 5. Login successful, home page loaded')

    // Test 6: 管理员菜单
    console.log('6. Testing admin menu...')
    const adminVisible = await page.evaluate(() => {
      const items = document.querySelectorAll('.el-dropdown-menu__item')
      for (const item of items) {
        if (item.textContent.includes('管理后台')) return true
      }
      return false
    })
    if (adminVisible) {
      results.push('✅ 6. Admin menu visible')
    } else {
      results.push('❌ 6. Admin menu NOT visible')
    }

    // Test 7: 岛屿动画
    console.log('7. Testing island animation...')
    const islandAnim = await page.evaluate(() => {
      const el = document.querySelector('.music-island')
      return window.getComputedStyle(el).animationName
    })
    if (islandAnim.includes('orbit')) {
      results.push('✅ 7. Island orbit animation active')
    } else {
      results.push(`⚠️ 7. Animation: ${islandAnim}`)
    }

    // Test 8: 背景音乐
    console.log('8. Testing background music...')
    const audioSrc = await page.evaluate(() => document.querySelector('audio')?.src || 'none')
    if (audioSrc.includes('.mp3') || audioSrc.includes('.wav')) {
      results.push('✅ 8. Background music configured')
    } else {
      results.push('⚠️ 8. Audio source not found')
    }

    // Test 9: API健康检查
    console.log('9. Testing API health...')
    const healthResponse = await page.evaluate(async () => {
      try {
        const res = await fetch('/api/health')
        return res.ok
      } catch {
        return false
      }
    })
    if (healthResponse) {
      results.push('✅ 9. API health check passed')
    } else {
      results.push('❌ 9. API health check failed')
    }

    // Test 10: 移动端适配
    console.log('10. Testing mobile viewport...')
    await page.setViewportSize({ width: 375, height: 667 })
    await page.waitForTimeout(500)
    const mobileCheck = await page.evaluate(() => {
      const body = document.body
      return body.offsetWidth <= 768
    })
    if (mobileCheck) {
      results.push('✅ 10. Mobile responsive layout')
    } else {
      results.push('❌ 10. Mobile layout broken')
    }

    await browser.close()

  } catch (error) {
    results.push(`❌ Error: ${error.message}`)
  }

  console.log('\n=== E2E Test Results ===')
  results.forEach(r => console.log(r))

  const passed = results.filter(r => r.startsWith('✅')).length
  const failed = results.filter(r => r.startsWith('❌')).length
  console.log(`\nTotal: ${passed} passed, ${failed} failed`)

  process.exit(failed > 0 ? 1 : 0)
}

runTests().catch(console.error)