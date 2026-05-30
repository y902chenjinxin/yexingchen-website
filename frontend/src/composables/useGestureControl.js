/**
 * useGestureControl.js
 * 手势控制 composable
 * 移动端特有的交互：捏合、长按、滑动
 */

import { ref, onMounted, onUnmounted } from 'vue'

export function useGestureControl(options = {}) {
  const {
    onPinch = () => {},
    onLongPress = () => {},
    onSwipeUp = () => {},
    onDoubleTap = () => {}
  } = options

  const isEnabled = ref(true)

  // 手势状态
  let initialDistance = 0
  let initialScale = 1
  let longPressTimer = null
  let lastTapTime = 0

  // 计算两点之间的距离
  const getDistance = (touches) => {
    const dx = touches[0].clientX - touches[1].clientX
    const dy = touches[0].clientY - touches[1].clientY
    return Math.sqrt(dx * dx + dy * dy)
  }

  // 计算两点之间的中点
  const getCenter = (touches) => {
    return {
      x: (touches[0].clientX + touches[1].clientX) / 2,
      y: (touches[0].clientY + touches[1].clientY) / 2
    }
  }

  // 触摸开始
  const handleTouchStart = (e) => {
    if (!isEnabled.value) return

    if (e.touches.length === 2) {
      // 双指捏合开始
      initialDistance = getDistance(e.touches)
      initialScale = 1
    }

    if (e.touches.length === 1) {
      // 单指长按
      longPressTimer = setTimeout(() => {
        onLongPress(e)
        longPressTimer = null
      }, 500)

      // 双击检测
      const now = Date.now()
      if (now - lastTapTime < 300) {
        onDoubleTap(e)
        lastTapTime = 0
      } else {
        lastTapTime = now
      }
    }
  }

  // 触摸移动
  const handleTouchMove = (e) => {
    if (!isEnabled.value) return

    if (e.touches.length === 2) {
      // 双指捏合
      const currentDistance = getDistance(e.touches)
      const scale = currentDistance / initialDistance

      onPinch({
        scale: scale / initialScale,
        center: getCenter(e.touches)
      })

      initialScale = scale
      initialDistance = currentDistance
    }

    // 取消长按（如果有移动）
    if (longPressTimer && e.touches.length === 1) {
      const touch = e.touches[0]
      const movement = Math.abs(touch.clientX - e.changedTouches[0].clientX) +
                       Math.abs(touch.clientY - e.touches[0].clientY)

      if (movement > 10) {
        clearTimeout(longPressTimer)
        longPressTimer = null
      }
    }
  }

  // 触摸结束
  const handleTouchEnd = (e) => {
    if (!isEnabled.value) return

    // 清除长按定时器
    if (longPressTimer) {
      clearTimeout(longPressTimer)
      longPressTimer = null
    }

    // 检测上滑
    if (e.changedTouches.length === 1) {
      const touch = e.changedTouches[0]
      const startY = touch.clientY

      // 延迟检测上滑
      setTimeout(() => {
        const endY = touch.clientY
        if (startY - endY > 100) { // 上滑超过100px
          onSwipeUp(e)
        }
      }, 100)
    }
  }

  // 启用/禁用
  const enable = () => {
    isEnabled.value = true
  }

  const disable = () => {
    isEnabled.value = false
  }

  onMounted(() => {
    document.addEventListener('touchstart', handleTouchStart, { passive: true })
    document.addEventListener('touchmove', handleTouchMove, { passive: true })
    document.addEventListener('touchend', handleTouchEnd, { passive: true })
  })

  onUnmounted(() => {
    document.removeEventListener('touchstart', handleTouchStart)
    document.removeEventListener('touchmove', handleTouchMove)
    document.removeEventListener('touchend', handleTouchEnd)
  })

  return {
    isEnabled,
    enable,
    disable
  }
}