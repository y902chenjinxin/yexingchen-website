/**
 * 习惯打卡 store（v2.46.140）
 *
 * 后端 `app/routers/workbench/habits.py` 早就写好了（Habit + HabitCheckin，
 * 返回 checked_today / streak / week_count / total_count / heat），但**前端一直没有页面用它** ——
 * `api/workbench.js` 里只有一行封装，全站 grep 不到调用。这里补上唯一的数据出口。
 *
 * 设计要点：
 *   · **单一来源**：页面、工作台卡片、提醒都读这个 store，避免各自请求导致「卡片说 2/3、页面说 1/3」
 *   · **打卡是乐观更新**：先改本地再请求，失败回滚 —— 打卡这种高频轻动作等 300ms 会很挫
 *   · **跨天自愈**：进页面时若发现本地缓存的日期不是今天，强制重新拉一次（否则昨晚的 checked_today 会留到今天）
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { workbenchApi } from '@/api/workbench'

/** 本地日期 YYYY-MM-DD（不能用 toISOString，那是 UTC，东八区早上 8 点前会算成昨天） */
function localDay() {
  const d = new Date()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

export const useHabitsStore = defineStore('habits', () => {
  const list = ref([])
  const loading = ref(false)
  const error = ref('')
  /** 这批数据属于哪一天（判断跨天） */
  const day = ref('')
  let inflight = null

  const doneCount = computed(() => list.value.filter((h) => h.checked_today).length)
  const total = computed(() => list.value.length)
  /** 今日完成率 0~100 */
  const progress = computed(() => (total.value ? Math.round((doneCount.value / total.value) * 100) : 0))
  /** 还没打卡的（工作台卡片只展示这几条） */
  const pending = computed(() => list.value.filter((h) => !h.checked_today))
  /** 最长连续天数 */
  const bestStreak = computed(() => list.value.reduce((m, h) => Math.max(m, h.streak || 0), 0))
  /** 全部打卡完成 */
  const allDone = computed(() => total.value > 0 && doneCount.value === total.value)

  async function load(force = false) {
    // 跨天 or 强制 → 重新拉；否则复用 inflight 去重
    const stale = day.value !== localDay()
    if (!force && !stale && list.value.length) return list.value
    if (inflight) return inflight
    loading.value = true
    error.value = ''
    inflight = (async () => {
      try {
        const res = await workbenchApi.habits.list()
        const rows = res?.data?.habits || res?.habits || []
        list.value = rows
        day.value = localDay()
        return rows
      } catch (e) {
        error.value = e?.message || '加载失败'
        throw e
      } finally {
        loading.value = false
        inflight = null
      }
    })()
    return inflight
  }

  /** 打卡 / 取消打卡（乐观更新 + 失败回滚） */
  async function toggle(habit) {
    const prev = { checked: habit.checked_today, streak: habit.streak, week: habit.week_count, total: habit.total_count }
    habit.checked_today = !prev.checked
    habit.streak = prev.checked ? Math.max(0, prev.streak - 1) : prev.streak + 1
    habit.week_count = Math.max(0, prev.week + (prev.checked ? -1 : 1))
    habit.total_count = Math.max(0, prev.total + (prev.checked ? -1 : 1))
    // 热力图末格跟着动（今天的格子）
    if (Array.isArray(habit.heat) && habit.heat.length) {
      const today = localDay()
      const cell = habit.heat.find((c) => c.date === today)
      if (cell) cell.checked = habit.checked_today
      else habit.heat[habit.heat.length - 1].checked = habit.checked_today
    }
    try {
      await workbenchApi.habits.toggle(habit.id)
    } catch (e) {
      habit.checked_today = prev.checked
      habit.streak = prev.streak
      habit.week_count = prev.week
      habit.total_count = prev.total
      throw e
    }
  }

  async function create(payload) {
    const res = await workbenchApi.habits.create(payload)
    await load(true)
    return res?.data?.id
  }

  async function update(id, payload) {
    await workbenchApi.habits.update(id, payload)
    await load(true)
  }

  async function remove(id) {
    list.value = list.value.filter((h) => h.id !== id)
    await workbenchApi.habits.remove(id)
  }

  return {
    list, loading, error, day,
    doneCount, total, progress, pending, bestStreak, allDone,
    load, toggle, create, update, remove,
  }
})
