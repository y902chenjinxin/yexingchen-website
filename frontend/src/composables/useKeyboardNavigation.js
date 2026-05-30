/**
 * useKeyboardNavigation.js
 * 键盘导航 composable
 * 支持Tab按方位顺序、方向键、快捷键
 */

import { ref, onMounted, onUnmounted } from 'vue'

export function useKeyboardNavigation(options = {}) {
  const {
    onNavigateToIsland = () => {},
    onEscape = () => {},
    onHelp = () => {}
  } = options

  const isActive = ref(true)
  const currentIndex = ref(0)
  const islandCount = ref(5) // 五岛

  // 方位顺序：东→南→西→北（但实际上是从上开始，顺时针）
  const navigateOrder = [0, 1, 2, 3, 4] // 音乐岛→小说岛→视频岛→日志岛→工具岛

  const handleKeyDown = (e) => {
    if (!isActive.value) return

    switch (e.key) {
      case 'Tab':
        // 按方位顺序遍历
        if (e.shiftKey) {
          // 反向
          currentIndex.value = (currentIndex.value - 1 + islandCount.value) % islandCount.value
        } else {
          currentIndex.value = (currentIndex.value + 1) % islandCount.value
        }
        e.preventDefault()
        break

      case 'ArrowUp':
      case 'ArrowLeft':
        // 上/左：逆时针
        currentIndex.value = (currentIndex.value - 1 + islandCount.value) % islandCount.value
        e.preventDefault()
        break

      case 'ArrowDown':
      case 'ArrowRight':
        // 下/右：顺时针
        currentIndex.value = (currentIndex.value + 1) % islandCount.value
        e.preventDefault()
        break

      case 'Enter':
        // 进入当前岛屿
        onNavigateToIsland(currentIndex.value)
        e.preventDefault()
        break

      case 'Escape':
        // 退出秘境
        onEscape()
        e.preventDefault()
        break

      case '?':
        // 显示帮助
        onHelp()
        e.preventDefault()
        break

      // 秘法快捷键
      case 'ArrowUp':
        if (checkKonamiSequence('up')) return
        break
    }
  }

  // Konami Code 检测（用于道心通明）
  let konamiIndex = 0
  const konamiCode = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'KeyB', 'KeyA']

  const checkKonamiSequence = (key) => {
    if (konamiCode[konamiIndex] === key) {
      konamiIndex++
      if (konamiIndex === konamiCode.length) {
        // 触发道心通明效果
        triggerDaoXinTongMing()
        konamiIndex = 0
        return true
      }
    } else {
      konamiIndex = 0
    }
    return false
  }

  // 道心通明效果
  const triggerDaoXinTongMing = () => {
    document.body.classList.add('dao-xin-tong-ming')

    // 设置金色高亮
    document.documentElement.style.setProperty('--global-glow', '1')

    setTimeout(() => {
      document.body.classList.remove('dao-xin-tong-ming')
      document.documentElement.style.setProperty('--global-glow', '0')
    }, 5000)
  }

  // 设置当前焦点
  const setCurrentIndex = (index) => {
    currentIndex.value = Math.max(0, Math.min(index, islandCount.value - 1))
  }

  // 激活/停用
  const activate = () => {
    isActive.value = true
  }

  const deactivate = () => {
    isActive.value = false
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKeyDown)
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeyDown)
  })

  return {
    isActive,
    currentIndex,
    setCurrentIndex,
    activate,
    deactivate,
    triggerDaoXinTongMing
  }
}