<!--
  HabitsCard.vue
  玄黄・工作台「习惯打卡」横幅卡（#1）
  - 列出全部习惯，逐项：icon/name/周进度/连续 streak/今日打卡开关
  - 内联「+ 新建习惯」：name + 可选 color/weekly_goal
  - toggle/新建后重拉列表，保证 streak/week_count 等统计准确
-->
<template>
  <div class="hb-card">
    <div class="hb-head">
      <div class="hb-titles">
        <span class="hb-mark" aria-hidden="true">◉</span>
        <span class="hb-title">习惯打卡</span>
      </div>
      <div class="hb-head-right">
        <span class="hb-today">今日完成 <b>{{ doneCount }}</b> / {{ habits.length || 0 }}</span>
        <button class="hb-add" @click="showForm = !showForm">{{ showForm ? '收起' : '＋ 新建习惯' }}</button>
      </div>
    </div>

    <!-- 新建表单（内联） -->
    <form v-if="showForm" class="hb-form" @submit.prevent="createHabit">
      <input v-model="form.name" class="hb-input hb-name" placeholder="习惯名称，如「晨跑 3 公里」" maxlength="64" required />
      <div class="hb-palette" title="主题色">
        <span
          v-for="c in COLORS" :key="c"
          class="hb-swatch"
          :class="{ active: form.color === c }"
          :style="{ background: c }"
          @click="form.color = c"
        ></span>
      </div>
      <label class="hb-goal">
        每周目标
        <input v-model.number="form.weekly_goal" type="number" min="0" max="7" class="hb-input hb-goal-input" />
      </label>
      <button class="hb-btn" type="submit" :disabled="saving">{{ saving ? '保存…' : '保存' }}</button>
      <button class="hb-btn ghost" type="button" @click="showForm = false">取消</button>
    </form>

    <!-- 习惯列表 -->
    <div v-if="loading" class="hb-loading">加载习惯中…</div>
    <ul v-else-if="habits.length" class="hb-list">
      <li
        v-for="h in habits"
        :key="h.id"
        class="hb-item"
      >
        <span class="hb-icon" :style="{ background: h.color, color: contrastText(h.color) }" aria-hidden="true">{{ h.icon }}</span>
        <div class="hb-item-main">
          <span class="hb-name">{{ h.name }}</span>
          <span class="hb-week">周 {{ h.week_count }}{{ h.weekly_goal ? ' / ' + h.weekly_goal : '' }}</span>
        </div>
        <span v-if="h.streak > 0" class="hb-streak" title="连续打卡天数">
          <span class="hb-flame" aria-hidden="true">🔥</span>{{ h.streak }} 天
        </span>
        <button
          class="hb-check"
          :class="{ on: h.checked_today }"
          :title="h.checked_today ? '取消今日打卡' : '今日打卡'"
          @click="toggleHabit(h)"
        >
          <span v-if="h.checked_today" aria-hidden="true">✓</span>
        </button>
      </li>
    </ul>
    <p v-else class="hb-empty">还没有习惯，点「＋ 新建习惯」开始记录</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { workbenchApi } from '@/api/workbench'

defineOptions({ name: 'HabitsCard' })

// 可选的预设主题色（贴合工作台强调色系）
const COLORS = ['#67e8f9', '#a78bfa', '#fbbf24', '#34d399', '#fb7185', '#60a5fa']

const habits = ref([])
const loading = ref(true)
const saving = ref(false)
const showForm = ref(false)
const form = ref({ name: '', color: COLORS[0], weekly_goal: 0 })

const doneCount = computed(() => habits.value.filter(h => h.checked_today).length)

// 深色图标文字在亮色块上可读
function contrastText(hex) {
  if (!hex) return '#0f1530'
  const c = hex.replace('#', '')
  const r = parseInt(c.slice(0, 2), 16)
  const g = parseInt(c.slice(2, 4), 16)
  const b = parseInt(c.slice(4, 6), 16)
  const lum = (r * 299 + g * 587 + b * 114) / 1000
  return lum > 150 ? '#101735' : '#ffffff'
}

async function loadHabits() {
  loading.value = true
  try {
    const res = await workbenchApi.habits.list()
    habits.value = res?.data?.habits || []
  } catch { /* 静默，保留旧列表 */ }
  finally { loading.value = false }
}

async function toggleHabit(h) {
  const before = h.checked_today
  h.checked_today = !before // 即时反馈
  try {
    await workbenchApi.habits.toggle(h.id)
    await loadHabits() // 重拉保证 streak/week_count 准确
  } catch {
    h.checked_today = before // 失败回滚
  }
}

async function createHabit() {
  const name = form.value.name.trim()
  if (!name) return
  saving.value = true
  try {
    await workbenchApi.habits.create({
      name,
      color: form.value.color,
      weekly_goal: Number(form.value.weekly_goal) || 0,
    })
    form.value = { name: '', color: COLORS[0], weekly_goal: 0 }
    showForm.value = false
    await loadHabits()
  } finally { saving.value = false }
}

onMounted(loadHabits)
</script>

<style scoped>
.hb-card {
  background: var(--dp-surface);
  border: 1px solid var(--dp-line);
  border-radius: var(--dp-radius);
  padding: 16px 18px 14px;
  box-shadow: var(--dp-shadow);
}
.hb-head {
  display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  margin-bottom: 12px;
}
.hb-titles { display: flex; align-items: center; gap: 8px; }
.hb-mark { color: var(--dp-accent, #67e8f9); font-size: 14px; line-height: 1; }
.hb-title { font-size: 12px; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; color: var(--dp-text2); }
.hb-head-right { display: flex; align-items: center; gap: 12px; }
.hb-today { font-size: 12px; color: var(--dp-text3); font-variant-numeric: tabular-nums; }
.hb-today b { color: var(--dp-accent, #67e8f9); font-size: 13px; }
.hb-add {
  border: 1px solid var(--dp-line-strong);
  background: transparent; color: var(--dp-text2);
  font-size: 12px; padding: 5px 12px; border-radius: 999px; cursor: pointer;
  transition: all .18s;
}
.hb-add:hover { color: var(--dp-accent); border-color: var(--dp-accent); background: var(--dp-accent-faint, rgba(127,168,163,.12)); }

/* 新建表单 */
.hb-form {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 10px 12px; margin-bottom: 12px;
  border: 1px dashed var(--dp-line-strong); border-radius: 10px;
  background: var(--dp-surface2);
}
.hb-input {
  padding: 7px 10px; border: 1px solid var(--dp-line-strong); border-radius: 8px;
  background: transparent; color: var(--dp-text); font-size: 13px; outline: none;
}
.hb-input:focus-visible { border-color: var(--dp-accent); }
.hb-name { flex: 1; min-width: 160px; }
.hb-palette { display: flex; gap: 6px; }
.hb-swatch {
  width: 18px; height: 18px; border-radius: 50%; cursor: pointer;
  border: 2px solid transparent; transition: transform .15s, border-color .15s;
}
.hb-swatch.active { border-color: var(--dp-text); transform: scale(1.15); }
.hb-goal { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: var(--dp-text2); }
.hb-goal-input { width: 48px; }
.hb-btn {
  border: 1px solid var(--dp-line-strong); background: var(--dp-accent-faint, rgba(127,168,163,.16));
  color: var(--dp-text); font-size: 12px; padding: 7px 14px; border-radius: 8px; cursor: pointer;
}
.hb-btn:hover { border-color: var(--dp-accent); }
.hb-btn.ghost { background: transparent; }
.hb-btn:disabled { opacity: .6; cursor: not-allowed; }

/* 列表 */
.hb-loading, .hb-empty { padding: 14px 6px; text-align: center; color: var(--dp-text3); font-size: 12px; margin: 0; }
.hb-list {
  list-style: none; margin: 0; padding: 0;
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px;
}
.hb-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 10px; border-radius: 10px;
  border: 1px solid var(--dp-line); background: var(--dp-surface2, transparent);
  transition: border-color .15s, background .15s;
}
.hb-item:hover { border-color: var(--dp-line-strong); }
.hb-icon {
  width: 28px; height: 28px; flex: none; border-radius: 8px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 15px; line-height: 1;
}
.hb-item-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.hb-name { font-size: 13px; color: var(--dp-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hb-week { font-size: 11px; color: var(--dp-text3); font-variant-numeric: tabular-nums; }
.hb-streak { display: inline-flex; align-items: center; gap: 3px; font-size: 11px; color: var(--dp-text3); font-variant-numeric: tabular-nums; flex: none; }
.hb-flame { font-size: 11px; }
.hb-check {
  flex: none; width: 26px; height: 26px; border-radius: 50%; cursor: pointer;
  border: 1px solid var(--dp-line-strong); background: transparent; color: var(--dp-text3);
  display: inline-flex; align-items: center; justify-content: center; font-size: 14px; transition: all .18s;
}
.hb-check:hover { border-color: var(--dp-accent); color: var(--dp-accent); }
.hb-check.on {
  background: var(--dp-accent, #67e8f9); border-color: transparent; color: #101735;
  box-shadow: var(--dp-glow, 0 0 10px rgba(103,232,249,.35));
}
/* 移动端收窄：单列 */
@media (max-width: 720px) {
  .hb-list { grid-template-columns: 1fr; }
}
</style>