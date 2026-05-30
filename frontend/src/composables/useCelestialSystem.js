/**
 * useCelestialSystem.js
 * 天象系统 composable
 * 管理十二时辰、节气、月相等天象变化
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'

// 十二时辰定义
const SHICHEN_NAMES = [
  { name: '子时', start: 23, end: 1, description: '深夜幽蓝，星星更亮' },
  { name: '丑时', start: 1, end: 3, description: '极暗，仅余微光' },
  { name: '寅时', start: 3, end: 5, description: '黎明前的深紫' },
  { name: '卯时', start: 5, end: 7, description: '日出霞光，金红渐现' },
  { name: '辰时', start: 7, end: 9, description: '晨曦清明' },
  { name: '巳时', start: 9, end: 11, description: '明亮暖黄' },
  { name: '午时', start: 11, end: 13, description: '正午骄阳' },
  { name: '未时', start: 13, end: 15, description: '午后暖阳' },
  { name: '申时', start: 15, end: 17, description: '下午金橙' },
  { name: '酉时', start: 17, end: 19, description: '夕阳晚霞' },
  { name: '戌时', start: 19, end: 21, description: '暮色苍茫' },
  { name: '亥时', start: 21, end: 23, description: '夜幕降临' }
]

// 二十四节气（按时间顺序）
const SOLAR_TERMS = [
  { name: '小寒', month: 1, day: 5, season: 'winter', atmosphere: '凛冬雪韵' },
  { name: '大寒', month: 1, day: 20, season: 'winter', atmosphere: '寒至极深' },
  { name: '立春', month: 2, day: 4, season: 'spring', atmosphere: '春回大地' },
  { name: '雨水', month: 2, day: 19, season: 'spring', atmosphere: '润物无声' },
  { name: '惊蛰', month: 3, day: 6, season: 'spring', atmosphere: '春雷惊醒' },
  { name: '春分', month: 3, day: 21, season: 'spring', atmosphere: '昼夜平分' },
  { name: '清明', month: 4, day: 5, season: 'spring', atmosphere: '清明时节' },
  { name: '谷雨', month: 4, day: 20, season: 'spring', atmosphere: '雨生百谷' },
  { name: '立夏', month: 5, day: 6, season: 'summer', atmosphere: '夏日初临' },
  { name: '小满', month: 5, day: 21, season: 'summer', atmosphere: '小麦渐满' },
  { name: '芒种', month: 6, day: 6, season: 'summer', atmosphere: '忙种时节' },
  { name: '夏至', month: 6, day: 21, season: 'summer', atmosphere: '阳极阴生' },
  { name: '小暑', month: 7, day: 7, season: 'summer', atmosphere: '暑气渐盛' },
  { name: '大暑', month: 7, day: 23, season: 'summer', atmosphere: '大热特热' },
  { name: '立秋', month: 8, day: 8, season: 'autumn', atmosphere: '秋意渐起' },
  { name: '处暑', month: 8, day: 23, season: 'autumn', atmosphere: '暑气将消' },
  { name: '白露', month: 9, day: 8, season: 'autumn', atmosphere: '露凝而白' },
  { name: '秋分', month: 9, day: 23, season: 'autumn', atmosphere: '金风送爽' },
  { name: '寒露', month: 10, day: 8, season: 'autumn', atmosphere: '露气寒冷' },
  { name: '霜降', month: 10, day: 23, season: 'autumn', atmosphere: '霜始凝结' },
  { name: '立冬', month: 11, day: 7, season: 'winter', atmosphere: '冬之开始' },
  { name: '小雪', month: 11, day: 22, season: 'winter', atmosphere: '雪意渐浓' },
  { name: '大雪', month: 12, day: 7, season: 'winter', atmosphere: '大雪封山' },
  { name: '冬至', month: 12, day: 22, season: 'winter', atmosphere: '阴极阳生' }
]

// seeded random function
function seededRandom(seed) {
  const x = Math.abs(Math.sin(seed * 12.9898) * 43758.5453) % 1
  return x
}

export function useCelestialSystem() {
  const currentHour = ref(new Date().getHours())
  const currentMonth = ref(new Date().getMonth() + 1)
  const currentDay = ref(new Date().getDate())

  // 十二时辰映射
  const hourToTheme = {
    0: 0,  // 子时
    1: 1,  // 丑时
    2: 2,  // 寅时
    3: 3,  // 卯时
    4: 4,  // 辰时
    5: 5,  // 巳时
    6: 6,  // 午时
    7: 7,  // 未时
    8: 8,  // 申时
    9: 9,  // 酉时
    10: 10, // 戌时
    11: 11, // 亥时
    12: 0,  // 下一轮子时
    13: 1,
    14: 2,
    15: 3,
    16: 4,
    17: 5,
    18: 6,
    19: 7,
    20: 8,
    21: 9,
    22: 10,
    23: 11
  }

  // 节气映射
  const solarTerms = {
    // 春季
    '02-03': 'spring',   // 立春
    '02-18': 'spring',   // 雨水
    '03-05': 'spring',   // 惊蛰
    '03-20': 'spring',   // 春分
    '04-04': 'spring',   // 清明
    '04-20': 'spring',   // 谷雨
    // 夏季
    '05-05': 'summer',   // 立夏
    '05-21': 'summer',   // 小满
    '06-05': 'summer',   // 芒种
    '06-21': 'summer',   // 夏至
    '07-07': 'summer',   // 小暑
    '07-22': 'summer',   // 大暑
    // 秋季
    '08-07': 'autumn',   // 立秋
    '08-23': 'autumn',   // 处暑
    '09-07': 'autumn',   // 白露
    '09-23': 'autumn',   // 秋分
    '10-08': 'autumn',   // 寒露
    '10-23': 'autumn',   // 霜降
    // 冬季
    '11-07': 'winter',   // 立冬
    '11-22': 'winter',   // 小雪
    '12-07': 'winter',   // 大雪
    '12-21': 'winter',   // 冬至
    '01-05': 'winter',   // 小寒
    '01-20': 'winter'    // 大寒
  }

  // 当前主题索引（0-11）
  const themeIndex = computed(() => hourToTheme[currentHour.value] || 0)

  // 当前季节
  const currentSeason = computed(() => {
    const key = `${String(currentMonth.value).padStart(2, '0')}-${String(currentDay.value).padStart(2, '0')}`
    return solarTerms[key] || 'normal'
  })

  // 节气强度
  const solarTermIntensity = computed(() => {
    switch (currentSeason.value) {
      case 'spring': return 0.8
      case 'summer': return 1.2
      case 'autumn': return 1.0
      case 'winter': return 0.9
      default: return 1.0
    }
  })

  // 获取当前时辰信息
  const shichenInfo = computed(() => SHICHEN_NAMES[themeIndex.value] || SHICHEN_NAMES[0])

  // 获取当前节气信息
  const getCurrentSolarTermInfo = () => {
    const key = `${String(currentMonth.value).padStart(2, '0')}-${String(currentDay.value).padStart(2, '0')}`
    const found = SOLAR_TERMS.find(t => {
      const tKey = `${String(t.month).padStart(2, '0')}-${String(t.day).padStart(2, '0')}`
      return tKey === key
    })
    return found || SOLAR_TERMS[2] // 默认返回立春
  }

  const solarTermInfo = computed(() => getCurrentSolarTermInfo())

  // 时辰名称
  const shichenName = computed(() => shichenInfo.value?.name || '子时')
  const solarTermName = computed(() => solarTermInfo.value?.name || '立春')

  // 更新天象
  const updateCelestial = () => {
    const now = new Date()
    currentHour.value = now.getHours()
    currentMonth.value = now.getMonth() + 1
    currentDay.value = now.getDate()

    // 应用到CSS变量
    const root = document.documentElement
    root.style.setProperty('--color-bg-current', `var(--color-bg-theme-${themeIndex.value})`)
    root.style.setProperty('--color-glow-current', `var(--color-glow-theme-${themeIndex.value})`)
    root.style.setProperty('--color-cloud-current', `var(--color-cloud-theme-${themeIndex.value})`)
    root.style.setProperty('--solar-term-intensity', solarTermIntensity.value)
  }

  let interval = null

  onMounted(() => {
    updateCelestial()
    // 每分钟更新一次
    interval = setInterval(updateCelestial, 60000)
  })

  onUnmounted(() => {
    if (interval) {
      clearInterval(interval)
    }
  })

  // 生成装饰物件的随机种子
  const getDecorationSeed = (type, index = 0) => {
    const date = new Date()
    const daySeed = date.getFullYear() * 10000 + (date.getMonth() + 1) * 100 + date.getDate()
    const minuteSeed = Math.floor(Date.now() / 60000)
    return seededRandom(daySeed + type.charCodeAt(0) * 100 + index + minuteSeed)
  }

  // 判断装饰物件是否应该显示
  const shouldShowDecoration = (type, probability) => {
    const seed = getDecorationSeed(type, Math.floor(Date.now() / 60000))
    return seed < probability
  }

  return {
    themeIndex,
    currentSeason,
    solarTermIntensity,
    shichenInfo,
    solarTermInfo,
    shichenName,
    solarTermName,
    updateCelestial,
    SHICHEN_NAMES,
    SOLAR_TERMS,
    getDecorationSeed,
    shouldShowDecoration
  }
}