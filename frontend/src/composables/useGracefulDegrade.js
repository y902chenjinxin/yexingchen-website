/**
 * useGracefulDegrade.js
 * 性能降级 composable - 自动检测设备能力并设置功能开关
 */

import { ref, onMounted, computed } from 'vue'

export function useGracefulDegrade() {
  const deviceTier = ref('high') // high | mid | low
  const initialFps = ref(60)

  const featureFlags = ref({
    // 【景】
    fiveLayerBackground: true,   // 五层背景
    godRays: true,              // 丁达尔光柱
    breathCycle: true,          // 呼吸节奏

    // 【物】
    islandSpirit: true,         // 岛屿灵物
    islandGlow: true,          // 岛屿发光

    // 【人】
    cursorTrail: true,         // 鼠标灵气轨迹
    daoName: true,            // 道号显示
    cultivationProgress: true, // 修为进度

    // 【声】
    audioReactive: true,       // 音频驱动
    islandSound: true,         // 岛屿音效

    // 【时】
    celestialSystem: true,     // 天象系统

    // 【感】
    rippleEffect: true,        // 灵气波纹
    gestureControl: true,      // 手势控制
    keyboardNav: true,         // 键盘导航

    // 【光】
    shaderBloom: true,         // Bloom效果
    jadeGlow: true,            // 玉石光感

    // 【转场】
    inkTransition: true,       // 砚台转场

    // 【包容】
    reducedMotion: true,       // 减少动效模式
    highContrast: true         // 高对比模式
  })

  const detectDeviceTier = () => {
    const cores = navigator.hardwareConcurrency || 4
    const memory = navigator.deviceMemory || 4
    const saveData = navigator.connection?.saveData || false
    const connection = navigator.connection

    // 网络状态检测
    const isSlow = connection?.effectiveType === '2g' || connection?.effectiveType === 'slow-2g'

    // 节省数据模式
    if (saveData || isSlow) {
      return 'low'
    }

    // 内存低于4GB
    if (memory < 4) {
      return 'low'
    }

    // CPU核心数
    if (cores < 2) {
      return 'low'
    }
    if (cores < 4) {
      return 'mid'
    }

    return 'high'
  }

  const detectInitialFps = () => {
    return new Promise((resolve) => {
      let frames = 0
      const startTime = performance.now()

      const countFrame = () => {
        frames++
        const elapsed = performance.now() - startTime

        if (elapsed < 500) {
          requestAnimationFrame(countFrame)
        } else {
          const fps = Math.round((frames / elapsed) * 1000)
          resolve(fps)
        }
      }

      requestAnimationFrame(countFrame)
    })
  }

  const applyDegrade = async (tier) => {
    deviceTier.value = tier

    // 根据设备等级调整功能开关
    switch (tier) {
      case 'high':
        // 全开
        Object.keys(featureFlags.value).forEach(key => {
          featureFlags.value[key] = true
        })
        break

      case 'mid':
        // 关闭部分重型功能
        featureFlags.value.godRays = false
        featureFlags.value.audioReactive = false
        featureFlags.value.shaderBloom = false
        break

      case 'low':
        // 仅保留核心功能
        featureFlags.value.fiveLayerBackground = true
        featureFlags.value.islandGlow = true
        featureFlags.value.keyboardNav = true
        featureFlags.value.inkTransition = true
        featureFlags.value.reducedMotion = true

        // 关闭重型功能
        featureFlags.value.godRays = false
        featureFlags.value.cursorTrail = false
        featureFlags.value.audioReactive = false
        featureFlags.value.islandSound = false
        featureFlags.value.shaderBloom = false
        featureFlags.value.rippleEffect = false
        featureFlags.value.gestureControl = false
        break
    }

    return tier
  }

  const init = async () => {
    // 首先检测硬件
    let tier = detectDeviceTier()

    // 如果硬件检测通过，检测帧率
    if (tier !== 'low') {
      const fps = await detectInitialFps()
      initialFps.value = fps

      if (fps < 30) {
        tier = 'mid'
      }
      if (fps < 20) {
        tier = 'low'
      }
    }

    await applyDegrade(tier)
  }

  // 动态调整（运行时）
  const setTier = (tier) => {
    applyDegrade(tier)
  }

  const isFeatureEnabled = (feature) => {
    return featureFlags.value[feature] === true
  }

  // 兼容 prefers-reduced-motion
  const prefersReducedMotion = computed(() => {
    if (typeof window === 'undefined') return false
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  })

  onMounted(() => {
    init()
  })

  return {
    deviceTier,
    featureFlags,
    initialFps,
    isFeatureEnabled,
    setTier,
    init,
    prefersReducedMotion
  }
}