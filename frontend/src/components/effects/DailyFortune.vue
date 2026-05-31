/**
 * DailyFortune.vue
 * 每日运势组件 - 显示今日宜忌和节气祝福
 */
<template>
  <div class="daily-fortune" :class="{ 'fortune-animate': showAnimation }">
    <div class="fortune-header">
      <span class="fortune-icon">{{ fortuneIcon }}</span>
      <span class="fortune-title">{{ fortuneTitle }}</span>
    </div>
    <div class="fortune-content">
      <div class="fortune-solar-term">{{ solarTermName }} {{ shichenName }}</div>
      <div class="fortune-tip">{{ fortuneTip }}</div>
      <div class="fortune-lucky-color">
        <span class="lucky-label">幸运色：</span>
        <span class="lucky-color" :style="{ color: luckyColor }">{{ luckyColorName }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const STORAGE_KEY = 'daily_fortune_data'
const fortuneData = ref({
  title: '万事皆宜',
  icon: '☀️',
  tip: '今日诸事顺遂，宜修身养性',
  luckyColor: 'var(--color-fortune-jade)',
  luckyColorName: '翡翠绿'
})

const showAnimation = ref(false)
const solarTermName = ref('立夏')
const shichenName = ref('辰时')

// 节气和时辰名称
const SOLAR_TERMS_MONTH = {
  1: ['小寒', '大寒'], 2: ['立春', '雨水'], 3: ['惊蛰', '春分'],
  4: ['清明', '谷雨'], 5: ['立夏', '小满'], 6: ['芒种', '夏至'],
  7: ['小暑', '大暑'], 8: ['立秋', '处暑'], 9: ['白露', '秋分'],
  10: ['寒露', '霜降'], 11: ['立冬', '小雪'], 12: ['大雪', '冬至']
}

const SHICHEN_NAMES = ['子时', '丑时', '寅时', '卯时', '辰时', '巳时',
                       '午时', '未时', '申时', '酉时', '戌时', '亥时']

const FORTUNE_TIPS = [
  '今日诸事顺遂，宜修身养性',
  '宜静心养气，忌躁进',
  '今日宜沉淀思考，忌轻举妄动',
  '诸事可成，宜把握机缘',
  '今日宜学习进步，忌虚度光阴',
  '宜与人为善，广结善缘',
  '今日宜蓄势待发，忌锋芒毕露',
  '宜稳中求进，忌急于求成'
]

const LUCKY_COLORS = [
  { color: 'var(--color-fortune-jade)', name: '翡翠绿' },
  { color: 'var(--color-fortune-gold)', name: '古铜金' },
  { color: 'var(--color-fortune-purple)', name: '紫霄色' },
  { color: 'var(--color-fortune-jade-dark)', name: '墨绿' },
  { color: 'var(--color-fortune-rose)', name: '紫薇' },
  { color: 'var(--color-fortune-paper)', name: '暖纸色' }
]

// 计算当前节气和时辰
function getCurrentSolarTermAndHour() {
  const now = new Date()
  const month = now.getMonth() + 1
  const day = now.getDate()
  const hour = now.getHours()

  // 节气（简化版：每月两个节气，按日期大致划分）
  const terms = SOLAR_TERMS_MONTH[month] || ['立春', '雨水']
  const termIndex = day <= 15 ? 0 : 1
  solarTermName.value = terms[termIndex]

  // 时辰
  shichenName.value = SHICHEN_NAMES[Math.floor((hour + 1) / 2) % 12] || '辰时'
}

function loadFortune() {
  try {
    const today = new Date().toDateString()
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const data = JSON.parse(stored)
      if (data.date === today) {
        fortuneData.value = data.fortune
        return
      }
    }
  } catch (e) {
    console.warn('Failed to load fortune data:', e)
  }

  // 生成新的运势
  generateFortune()
}

function generateFortune() {
  const now = new Date()
  const daySeed = now.getFullYear() * 10000 + (now.getMonth() + 1) * 100 + now.getDate()
  const seed = (x) => Math.abs(Math.sin(daySeed * 12.9898 + x * 78.233)) % 1

  // 根据日期选择运势
  const titleIndex = Math.floor(seed(1) * 8)
  const tipIndex = Math.floor(seed(2) * FORTUNE_TIPS.length)
  const colorIndex = Math.floor(seed(3) * LUCKY_COLORS.length)

  fortuneData.value = {
    title: ['万事皆宜', '诸事顺遂', '静心养性', '厚积薄发', '把握机缘', '广结善缘', '稳中求进', '顺势而为'][titleIndex],
    icon: ['☀️', '🌙', '⭐', '🌸', '🍃', '💫', '✨', '🌿'][titleIndex],
    tip: FORTUNE_TIPS[tipIndex],
    luckyColor: LUCKY_COLORS[colorIndex].color,
    luckyColorName: LUCKY_COLORS[colorIndex].name
  }

  // 保存到localStorage
  try {
    const today = new Date().toDateString()
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      date: today,
      fortune: fortuneData.value
    }))
  } catch (e) {
    console.warn('Failed to save fortune data:', e)
  }
}

const fortuneIcon = computed(() => fortuneData.value.icon)
const fortuneTitle = computed(() => fortuneData.value.title)
const fortuneTip = computed(() => fortuneData.value.tip)
const luckyColor = computed(() => fortuneData.value.luckyColor)
const luckyColorName = computed(() => fortuneData.value.luckyColorName)

onMounted(() => {
  getCurrentSolarTermAndHour()
  loadFortune()
})
</script>

<style scoped>
.daily-fortune {
  position: fixed;
  bottom: 160px;
  right: 30px;
  z-index: 100;
  width: 160px;
  background: rgba(243, 237, 224, 0.18);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(212, 175, 55, 0.3);
  border-radius: 8px;
  padding: 12px;
  cursor: default;
  transition: all 0.3s ease;
}

.daily-fortune:hover {
  transform: scale(1.02);
  background: rgba(243, 237, 224, 0.25);
  border-color: rgba(212, 175, 55, 0.5);
  box-shadow: 0 4px 20px rgba(212, 175, 55, 0.15);
}

.fortune-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(201, 169, 98, 0.25);
}

.fortune-icon {
  font-size: 16px;
}

.fortune-title {
  font-family: var(--font-serif);
  font-size: 14px;
  color: rgba(180, 140, 60, 0.9);
}

.fortune-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.fortune-solar-term {
  font-family: var(--font-serif);
  font-size: 12px;
  color: rgba(120, 100, 80, 0.8);
}

.fortune-tip {
  font-size: 11px;
  color: rgba(100, 80, 60, 0.75);
  line-height: 1.4;
}

.fortune-lucky-color {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
}

.lucky-label {
  color: rgba(100, 80, 60, 0.6);
}

.lucky-color {
  font-weight: 600;
}

.fortune-animate {
  animation: fortune-pulse 0.6s ease-out;
}

@keyframes fortune-pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); }
}

@media (max-width: 768px) {
  .daily-fortune {
    bottom: 140px;
    right: 15px;
    width: 140px;
    padding: 10px;
  }

  .fortune-title {
    font-size: 13px;
  }

  .fortune-tip {
    font-size: 10px;
  }
}
</style>