/**
 * useRandomEvents.js
 * 随机惊喜事件 composable
 * 流星雨、灵气爆发、仙鹤群飞、祥云降临、天雷隐现
 */

import { ref, onMounted, onUnmounted } from 'vue'

// 随机事件类型
const EVENT_TYPES = {
  METEOR_SHOWER: 'meteor_shower',
  QI_BURST: 'qi_burst',
  CRANE_SWARM: 'crane_swarm',
  AUSPICIOUS_CLOUDS: 'auspicious_clouds',
  DISTANT_THUNDER: 'distant_thunder'
}

// 事件配置
const EVENT_CONFIG = {
  [EVENT_TYPES.METEOR_SHOWER]: {
    name: '流星雨',
    duration: 3000,
    probability: 0.15
  },
  [EVENT_TYPES.QI_BURST]: {
    name: '灵气爆发',
    duration: 2000,
    probability: 0.2
  },
  [EVENT_TYPES.CRANE_SWARM]: {
    name: '仙鹤群飞',
    duration: 6000,
    probability: 0.1
  },
  [EVENT_TYPES.AUSPICIOUS_CLOUDS]: {
    name: '祥云降临',
    duration: 5000,
    probability: 0.18
  },
  [EVENT_TYPES.DISTANT_THUNDER]: {
    name: '天雷隐现',
    duration: 4000,
    probability: 0.12
  }
}

// cooldown时间（30分钟）
const COOLDOWN_MS = 30 * 60 * 1000

// seeded random
function seededRandom(seed) {
  const x = Math.abs(Math.sin(seed * 12.9898) * 43758.5453) % 1
  return x
}

export function useRandomEvents() {
  const activeEvent = ref(null)
  const eventQueue = ref([])
  const showHint = ref(false)
  const hintText = '天机：可遇不可求'

  let checkInterval = null
  let eventTimeout = null

  // 获取localStorage中的最后触发时间
  const getLastTriggerTime = () => {
    try {
      const last = localStorage.getItem('random_event_last_trigger')
      return last ? parseInt(last, 10) : 0
    } catch {
      return 0
    }
  }

  // 设置最后触发时间
  const setLastTriggerTime = (time) => {
    try {
      localStorage.setItem('random_event_last_trigger', time.toString())
    } catch {
      // localStorage不可用
    }
  }

  // 检查是否在冷却期
  const isInCooldown = () => {
    const lastTrigger = getLastTriggerTime()
    const now = Date.now()
    return (now - lastTrigger) < COOLDOWN_MS
  }

  // 获取距离下次可触发的时间（毫秒）
  const getCooldownRemaining = () => {
    const lastTrigger = getLastTriggerTime()
    const now = Date.now()
    const elapsed = now - lastTrigger
    return Math.max(0, COOLDOWN_MS - elapsed)
  }

  // 随机选择事件类型
  const selectRandomEvent = () => {
    const now = Date.now()
    const seed = now % 1000000
    const random = seededRandom(seed)

    let cumulative = 0
    for (const [type, config] of Object.entries(EVENT_CONFIG)) {
      cumulative += config.probability
      if (random < cumulative) {
        return type
      }
    }
    return null
  }

  // 触发事件
  const triggerEvent = (eventType) => {
    if (activeEvent.value) return

    activeEvent.value = eventType
    setLastTriggerTime(Date.now())

    const config = EVENT_CONFIG[eventType]
    if (eventTimeout) {
      clearTimeout(eventTimeout)
    }
    eventTimeout = setTimeout(() => {
      activeEvent.value = null
    }, config.duration)
  }

  // 检查是否应该触发新事件
  const checkAndTrigger = () => {
    // 如果有事件在执行，不检查
    if (activeEvent.value) return

    // 如果在冷却期，不触发
    if (isInCooldown()) return

    // 随机选择事件
    const eventType = selectRandomEvent()
    if (eventType) {
      triggerEvent(eventType)
    }
  }

  // 显示提示
  const showEventHint = () => {
    showHint.value = true
  }

  // 隐藏提示
  const hideEventHint = () => {
    showHint.value = false
  }

  onMounted(() => {
    // 每30秒检查一次是否触发事件
    checkInterval = setInterval(checkAndTrigger, 30000)
    // 启动时立即检查一次
    setTimeout(checkAndTrigger, 5000)
  })

  onUnmounted(() => {
    if (checkInterval) {
      clearInterval(checkInterval)
    }
    if (eventTimeout) {
      clearTimeout(eventTimeout)
    }
  })

  return {
    activeEvent,
    eventQueue,
    showHint,
    hintText,
    EVENT_TYPES,
    EVENT_CONFIG,
    checkAndTrigger,
    showEventHint,
    hideEventHint,
    getCooldownRemaining
  }
}