/**
 * useIslandSound.js
 * 岛屿音效 composable
 * 每个岛屿有独特的音效，hover时触发"灵气共鸣"
 */

import { ref, onUnmounted } from 'vue'

export function useIslandSound() {
  const isEnabled = ref(true)
  const currentIsland = ref(null)

  // 音频元素
  let hoverSound = null
  let ambientSounds = {}

  // 岛屿音效配置
  const islandSounds = {
    music: {
      hover: '/sounds/guqin.mp3',  // 古琴音
      ambient: '/sounds/bgm-music.mp3'
    },
    novel: {
      hover: '/sounds/page-turn.mp3',  // 翻书声
      ambient: '/sounds/bgm-novel.mp3'
    },
    video: {
      hover: '/sounds/camera.mp3',    // 镜头光圈
      ambient: '/sounds/bgm-video.mp3'
    },
    log: {
      hover: '/sounds/ink.mp3',       // 墨迹
      ambient: '/sounds/bgm-log.mp3'
    },
    tool: {
      hover: '/sounds/gear.mp3',      // 齿轮
      ambient: '/sounds/bgm-tool.mp3'
    }
  }

  // 播放hover音效
  const playHoverSound = (islandType) => {
    if (!isEnabled.value) return

    // 停止之前的hover音效
    if (hoverSound) {
      hoverSound.pause()
      hoverSound.currentTime = 0
    }

    const soundConfig = islandSounds[islandType]
    if (!soundConfig?.hover) return

    try {
      hoverSound = new Audio(soundConfig.hover)
      hoverSound.volume = 0.3  // 较小音量
      hoverSound.play().catch(() => {
        // 忽略自动播放限制
      })
      currentIsland.value = islandType
    } catch (e) {
      console.warn('Sound playback failed:', e)
    }
  }

  // 停止hover音效
  const stopHoverSound = () => {
    if (hoverSound) {
      hoverSound.pause()
      hoverSound.currentTime = 0
      hoverSound = null
    }
    currentIsland.value = null
  }

  // 播放氛围音效
  const playAmbientSound = (islandType) => {
    const soundConfig = islandSounds[islandType]
    if (!soundConfig?.ambient) return

    // 已有则不重复播放
    if (ambientSounds[islandType]) return

    try {
      ambientSounds[islandType] = new Audio(soundConfig.ambient)
      ambientSounds[islandType].volume = 0.15
      ambientSounds[islandType].loop = true
      ambientSounds[islandType].play().catch(() => {})
    } catch (e) {
      console.warn('Ambient sound playback failed:', e)
    }
  }

  // 停止所有氛围音效
  const stopAllAmbient = () => {
    Object.values(ambientSounds).forEach(sound => {
      if (sound) {
        sound.pause()
        sound.currentTime = 0
      }
    })
    ambientSounds = {}
  }

  // 设置音量
  const setVolume = (volume) => {
    if (hoverSound) {
      hoverSound.volume = volume * 0.3
    }
    Object.values(ambientSounds).forEach(sound => {
      if (sound) {
        sound.volume = volume * 0.15
      }
    })
  }

  // 启用/禁用
  const enable = () => {
    isEnabled.value = true
  }

  const disable = () => {
    isEnabled.value = false
    stopHoverSound()
    stopAllAmbient()
  }

  onUnmounted(() => {
    stopHoverSound()
    stopAllAmbient()
  })

  return {
    isEnabled,
    currentIsland,
    playHoverSound,
    stopHoverSound,
    playAmbientSound,
    stopAllAmbient,
    setVolume,
    enable,
    disable
  }
}