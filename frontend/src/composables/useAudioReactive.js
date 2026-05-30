/**
 * useAudioReactive.js
 * 音频驱动视觉 composable
 * 通过 Web Audio API 提取频率数据，驱动岛屿呼吸和粒子密度
 */

import { ref, onMounted, onUnmounted } from 'vue'

export function useAudioReactive(audioElement) {
  const isInitialized = ref(false)
  const lowFrequency = ref(0)    // 低频 → 岛屿呼吸
  const highFrequency = ref(0)    // 高频 → 粒子密度

  let audioContext = null
  let analyser = null
  let dataArray = null
  let animationFrame = null

  const init = () => {
    if (!audioElement?.value) return

    try {
      audioContext = new (window.AudioContext || window.webkitAudioContext)()
      analyser = audioContext.createAnalyser()
      analyser.fftSize = 256

      const source = audioContext.createMediaElementSource(audioElement.value)
      source.connect(analyser)
      analyser.connect(audioContext.destination)

      dataArray = new Uint8Array(analyser.frequencyBinCount)
      isInitialized.value = true

      // 开始分析
      analyze()
    } catch (e) {
      console.warn('Audio reactive initialization failed:', e)
    }
  }

  const analyze = () => {
    if (!analyser || !dataArray) return

    analyser.getByteFrequencyData(dataArray)

    // 提取低频（0-8）
    const lowSum = dataArray.slice(0, 8).reduce((a, b) => a + b, 0)
    lowFrequency.value = lowSum / (8 * 255)

    // 提取高频（8-32）
    const highSum = dataArray.slice(8, 32).reduce((a, b) => a + b, 0)
    highFrequency.value = highSum / (24 * 255)

    // 应用到CSS变量
    document.documentElement.style.setProperty(
      '--island-breathe',
      0.8 + lowFrequency.value * 0.4
    )
    document.documentElement.style.setProperty(
      '--particle-density',
      0.5 + highFrequency.value * 0.5
    )

    animationFrame = requestAnimationFrame(analyze)
  }

  const pause = () => {
    if (animationFrame) {
      cancelAnimationFrame(animationFrame)
      animationFrame = null
    }
  }

  const resume = () => {
    if (isInitialized.value && !animationFrame) {
      analyze()
    }
  }

  // 重置为默认值（关闭音频时）
  const reset = () => {
    lowFrequency.value = 0
    highFrequency.value = 0
    document.documentElement.style.setProperty('--island-breathe', '1')
    document.documentElement.style.setProperty('--particle-density', '0.5')
  }

  onMounted(() => {
    // 等待音频元素准备好
    if (audioElement?.value) {
      init()
    } else {
      // 监听音频元素ready
      const checkAudio = setInterval(() => {
        if (audioElement?.value) {
          init()
          clearInterval(checkAudio)
        }
      }, 100)

      onUnmounted(() => clearInterval(checkAudio))
    }
  })

  onUnmounted(() => {
    pause()
    if (audioContext) {
      audioContext.close()
    }
  })

  return {
    isInitialized,
    lowFrequency,
    highFrequency,
    init,
    pause,
    resume,
    reset
  }
}