/**
 * useGestureControl.js
 * 手势控制 composable
 * 移动端玉简轮播手势：左右滑动、双击进入、长按操作
 */

import { ref, onMounted, onUnmounted } from 'vue'

export function useGestureControl(options = {}) {
  const {
    onSwipeLeft = () => {},
    onSwipeRight = () => {},
    onSwipeUp = () => {},
    onDoubleTap = () => {},
    onLongPress = () => {},
    onPinch = () => {},
    targetSelector = '.jade-carousel'
  } = options

  const isEnabled = ref(true)

  // 手势状态
  let initialDistance = 0
  let initialScale = 1
  let longPressTimer = null
  let lastTapTime = 0
  let touchStartX = 0
  let touchStartY = 0

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

  // 检查是否在目标区域内
  const isInTargetArea = (x, y) => {
    const target = document.querySelector(targetSelector)
    if (!target) return false
    const rect = target.getBoundingClientRect()
    return x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom
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
      const touch = e.touches[0]
      touchStartX = touch.clientX
      touchStartY = touch.clientY

      // 单指长按（500ms）
      longPressTimer = setTimeout(() => {
        if (isInTargetArea(touchStartX, touchStartY)) {
          onLongPress({ x: touchStartX, y: touchStartY })
        }
        longPressTimer = null
      }, 500)

      // 双击检测
      const now = Date.now()
      if (now - lastTapTime < 300) {
        if (isInTargetArea(touchStartX, touchStartY)) {
          onDoubleTap({ x: touchStartX, y: touchStartY })
        }
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

    // 取消长按（如果有移动超过10px）
    if (longPressTimer && e.touches.length === 1) {
      const touch = e.touches[0]
      const movement = Math.abs(touch.clientX - touchStartX) +
                       Math.abs(touch.clientY - touchStartY)

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

    // 单指手势检测
    if (e.changedTouches.length === 1) {
      const touch = e.changedTouches[0]
      const deltaX = touch.clientX - touchStartX
      const deltaY = touch.clientY - touchStartY

      // 水平滑动超过50px且水平距离大于垂直距离
      if (Math.abs(deltaX) > 50 && Math.abs(deltaX) > Math.abs(deltaY)) {
        if (deltaX < 0) {
          onSwipeLeft()
        } else {
          onSwipeRight()
        }
      }
      // 垂直上滑超过100px
      else if (deltaY < -100 && Math.abs(deltaY) > Math.abs(deltaX)) {
        onSwipeUp()
      }
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