/**
 * useBreathCycle.js
 * 呼吸节奏 composable - 4-7-8调息为基准
 * 用于控制元素的"呼吸感"，不是均匀循环，而是有停顿的韵律
 */

import { ref, onMounted, onUnmounted } from 'vue'

export function useBreathCycle(options = {}) {
  const {
    breathIn = 4000,      // 吸气 4s
    breathHold = 7000,    // 屏息 7s
    breathOut = 8000,      // 呼气 8s
    initialDelay = 0       // 初始延迟
  } = options

  const phase = ref('inhale')  // inhale | hold | exhale
  const progress = ref(0)       // 0-1 当前阶段进度
  const totalProgress = ref(0)  // 0-1 总呼吸周期进度
  const isActive = ref(true)

  let animationFrame = null
  let startTime = null

  const totalDuration = breathIn + breathHold + breathOut

  const animate = (timestamp) => {
    if (!isActive.value) return

    if (!startTime) startTime = timestamp
    const elapsed = timestamp - startTime + initialDelay

    // 计算总周期进度
    const cyclePosition = elapsed % totalDuration
    totalProgress.value = cyclePosition / totalDuration

    // 计算当前阶段
    if (cyclePosition < breathIn) {
      // 吸气阶段
      phase.value = 'inhale'
      progress.value = cyclePosition / breathIn
    } else if (cyclePosition < breathIn + breathHold) {
      // 屏息阶段
      phase.value = 'hold'
      progress.value = (cyclePosition - breathIn) / breathHold
    } else {
      // 呼气阶段
      phase.value = 'exhale'
      progress.value = (cyclePosition - breathIn - breathHold) / breathOut
    }

    animationFrame = requestAnimationFrame(animate)
  }

  const start = () => {
    isActive.value = true
    startTime = null
    animationFrame = requestAnimationFrame(animate)
  }

  const stop = () => {
    isActive.value = false
    if (animationFrame) {
      cancelAnimationFrame(animationFrame)
      animationFrame = null
    }
  }

  const pause = () => {
    isActive.value = false
  }

  const resume = () => {
    isActive.value = true
  }

  onMounted(() => {
    start()
  })

  onUnmounted(() => {
    stop()
  })

  return {
    phase,
    progress,
    totalProgress,
    isActive,
    start,
    stop,
    pause,
    resume,
    // 计算CSS变量的便捷方法
    getBreathStyle: () => {
      const scale = phase.value === 'inhale'
        ? 1 + (progress.value * 0.1)  // 吸气: 1 → 1.1
        : phase.value === 'hold'
        ? 1.1  // 屏息: 保持1.1
        : 1.1 - (progress.value * 0.1) // 呼气: 1.1 → 1

      const opacity = phase.value === 'inhale'
        ? 0.3 + (progress.value * 0.7)  // 0.3 → 1
        : phase.value === 'hold'
        ? 1  // 屏息: 保持1
        : 1 - (progress.value * 0.7)   // 1 → 0.3

      return {
        transform: `scale(${scale})`,
        opacity: opacity
      }
    }
  }
}