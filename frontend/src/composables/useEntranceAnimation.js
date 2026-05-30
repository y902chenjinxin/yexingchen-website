/**
 * useEntranceAnimation.js
 * 入场动画 composable - "命轮渐显"电影级入场
 *
 * Phase 1: 墨色渐显（0-1s）
 * Phase 2: 灵气涌动（1-2.5s）
 * Phase 3: 阵法浮现（2.5-3.5s）
 * Phase 4: 岛屿凝聚（3.5-5.5s）
 * Phase 5: 顶栏淡入（5-6s）
 */

import { ref, onMounted } from 'vue'

export function useEntranceAnimation() {
  const isComplete = ref(false)
  const currentPhase = ref(0) // 0-4
  const progress = ref(0) // 0-1

  const phases = [
    { name: 'ink-appear', duration: 1000, start: 0, description: '墨色渐显' },
    { name: 'qi-flow', duration: 1500, start: 1000, description: '灵气涌动' },
    { name: 'symbols-appear', duration: 1000, start: 2500, description: '阵法浮现' },
    { name: 'islands-materialize', duration: 2000, start: 3500, description: '岛屿凝聚' },
    { name: 'topbar-fadein', duration: 1000, start: 5000, description: '顶栏淡入' }
  ]

  let animationTimeline = null
  let hasRun = false

  const runEntrance = () => {
    if (hasRun) return // 只执行一次
    hasRun = true

    // 添加入场class到body
    document.body.classList.add('entrance-active')

    phases.forEach((phase, index) => {
      setTimeout(() => {
        currentPhase.value = index
        document.body.classList.add(`entrance-${phase.name}`)

        // 设置CSS进度变量
        document.documentElement.style.setProperty(
          '--entrance-progress',
          (index + 1) / phases.length
        )

        // Phase 4 时触发岛屿动画
        if (phase.name === 'islands-materialize') {
          document.body.classList.add('entrance-islands-active')
        }
      }, phase.start)
    })

    // 完成
    animationTimeline = setTimeout(() => {
      isComplete.value = true
      document.body.classList.remove('entrance-active')
      document.body.classList.add('entrance-complete')
    }, 6000)
  }

  const skipEntrance = () => {
    // 跳过动画，立即显示完整内容
    if (animationTimeline) {
      clearTimeout(animationTimeline)
    }

    phases.forEach((phase) => {
      document.body.classList.add(`entrance-${phase.name}`)
    })

    document.body.classList.add('entrance-complete')
    isComplete.value = true

    document.documentElement.style.setProperty('--entrance-progress', '1')
  }

  const reset = () => {
    hasRun = false
    isComplete.value = false
    currentPhase.value = 0
    progress.value = 0

    // 移除所有入场class
    document.body.classList.remove(
      'entrance-active',
      'entrance-complete',
      ...phases.map(p => `entrance-${p.name}`),
      'entrance-islands-active'
    )
  }

  onMounted(() => {
    // 监听用户交互以跳过动画
    const handleInteraction = () => {
      if (!isComplete.value && hasRun) {
        skipEntrance()
      }
      // 移除监听（一次性）
      document.removeEventListener('click', handleInteraction)
      document.removeEventListener('keydown', handleInteraction)
    }

    document.addEventListener('click', handleInteraction)
    document.addEventListener('keydown', handleInteraction)
  })

  return {
    isComplete,
    currentPhase,
    progress,
    phases,
    runEntrance,
    skipEntrance,
    reset
  }
}