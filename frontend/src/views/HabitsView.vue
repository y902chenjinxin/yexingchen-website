<template>
  <div class="hb-page">
    <div class="hb-inner">
      <header class="hb-head">
        <BackButton class="hb-back" />
        <div class="hb-titles">
          <h1 class="hb-title">今天</h1>
          <p class="hb-sub">
            {{ doneCount }}/{{ total }} 已完成<template v-if="bestStreak"> · 最长连续 {{ bestStreak }} 天</template>
          </p>
        </div>
        <div class="hb-head-right">
          <IconButton
            :icon="managing ? 'check' : 'settings'"
            :label="managing ? '完成管理' : '管理'"
            size="sm"
            @click="managing = !managing"
          />
          <IconButton icon="plus" label="新习惯" variant="primary" @click="openCreate" />
        </div>
      </header>

      <!-- 今日进度 -->
      <section v-if="total" class="hb-progress glass-card">
        <div class="hb-ring">
          <svg viewBox="0 0 64 64" aria-hidden="true">
            <circle class="hb-ring-bg" cx="32" cy="32" r="27" />
            <circle
              class="hb-ring-fg"
              :class="{ full: allDone }"
              cx="32" cy="32" r="27"
              :stroke-dasharray="`${(progress / 100) * 169.6} 169.6`"
            />
          </svg>
          <span class="hb-ring-txt">{{ progress }}<i>%</i></span>
        </div>
        <div class="hb-progress-side">
          <div class="hb-progress-line" :class="{ done: allDone }">
            <template v-if="allDone">今天的都做完了</template>
            <template v-else>还剩 <b>{{ pending.length }}</b> 件没做</template>
          </div>
          <div class="hb-progress-hint">
            <template v-if="bestStreak">最长连续 {{ bestStreak }} 天 · 别断链</template>
            <template v-else>点一下就算打卡，连续天数会自动累计</template>
          </div>
        </div>
      </section>

      <!-- 今日清单 -->
      <section v-if="total" class="hb-card glass-card">
        <ul class="hb-list">
          <li v-for="h in list" :key="h.id" class="hb-row" :class="{ done: h.checked_today }">
            <button
              v-if="!managing"
              class="hb-hit"
              :aria-pressed="h.checked_today ? 'true' : 'false'"
              :aria-label="`${h.name}，${h.checked_today ? '已打卡，点击取消' : '未打卡，点击打卡'}`"
              @click="onToggle(h)"
            >
              <span class="hb-ico" :style="h.color ? { color: h.color } : null">
                <AppIcon :icon="h.icon || '✓'" :size="18" />
              </span>
              <span class="hb-main">
                <span class="hb-name">{{ h.name }}</span>
                <span class="hb-meta">
                  连续 {{ h.streak }} 天 · 本周 {{ h.week_count }}<template v-if="h.weekly_goal">/{{ h.weekly_goal }}</template>
                  · 累计 {{ h.total_count }}
                  <template v-if="h.penalty_cents"> · 罚 ¥{{ (h.penalty_cents / 100).toFixed(0) }}/天</template>
                </span>
              </span>
              <span class="hb-tick" :class="{ on: h.checked_today }" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M5 12.6 9.6 17l9.4-10" />
                </svg>
              </span>
            </button>

            <!-- 管理模式：改 / 删 -->
            <div v-else class="hb-manage">
              <span class="hb-ico"><AppIcon :icon="h.icon || '✓'" :size="17" /></span>
              <span class="hb-main"><span class="hb-name">{{ h.name }}</span></span>
              <IconButton icon="edit" size="sm" label="编辑" @click="openEdit(h)" />
              <IconButton icon="trash" size="sm" label="删除" variant="danger" @click="onRemove(h)" />
            </div>
          </li>
        </ul>
      </section>

      <!-- 空态 -->
      <section v-if="!total && !loading" class="hb-empty">
        <EmptyState
          tone="data"
          title="还没有每天要做的事"
          description="先设 1~3 个每天想坚持的小动作（喝水、走 6000 步、写 200 字）。坚持 30 天，这里会给你一条链。"
          action-label="＋ 新建第一个"
          @action="openCreate"
        />
      </section>

      <!-- 本周复盘（v2.46.143） -->
      <section v-if="weekly && total" class="hb-card glass-card">
        <div class="hb-card-head">
          <h2 class="hb-card-title">本周复盘</h2>
          <span class="hb-card-sub">{{ weekly.week_start }} 起 · 第 {{ weekly.days_elapsed }} 天</span>
        </div>
        <div class="hb-wk">
          <div class="hb-wk-stat">
            <b>{{ weekly.rate }}<i>%</i></b>
            <span>完成率</span>
          </div>
          <div class="hb-wk-stat">
            <b>{{ weekly.checked }}<i>/{{ weekly.possible }}</i></b>
            <span>打卡</span>
          </div>
          <div class="hb-wk-stat" :class="{ warn: weekly.penalty_count > 0 }">
            <b>{{ weekly.penalty_count }}</b>
            <span>断链</span>
          </div>
          <div class="hb-wk-stat" :class="{ warn: weekly.penalty_cents > 0 }">
            <b>¥{{ (weekly.penalty_cents / 100).toFixed(0) }}</b>
            <span>罚金</span>
          </div>
        </div>
        <p class="hb-wk-text">{{ weekly.text }}</p>
        <p class="hb-wk-advice"><span>小玄</span>{{ weekly.suggestion }}</p>
      </section>

      <!-- 最近 30 天记录 -->
      <section v-if="total" class="hb-card glass-card">
        <div class="hb-card-head">
          <h2 class="hb-card-title">最近 30 天</h2>
          <span class="hb-card-sub">一共 {{ totalCheckins }} 次打卡</span>
        </div>
        <div v-for="h in list" :key="'heat' + h.id" class="hb-heat-row">
          <span class="hb-heat-name" :title="h.name">{{ h.name }}</span>
          <span class="hb-cells" :aria-label="`${h.name} 最近 30 天打卡 ${heatCount(h)} 天`">
            <i
              v-for="(c, i) in h.heat"
              :key="i"
              :class="{ on: c.checked }"
              :title="c.date + (c.checked ? ' 已打卡' : '')"
            ></i>
          </span>
          <span class="hb-heat-n">{{ heatCount(h) }}/30</span>
        </div>
      </section>
    </div>

    <!-- 新建 / 编辑 -->
    <el-dialog v-model="dialog" :title="form.id ? '编辑习惯' : '新建习惯'" width="420px" append-to-body>
      <div class="hb-form">
        <label class="hb-field">
          <span>名称</span>
          <el-input v-model="form.name" maxlength="64" placeholder="例如：走 6000 步" />
        </label>
        <div class="hb-field">
          <span>图标</span>
          <div class="hb-icons">
            <button
              v-for="ic in ICON_CHOICES"
              :key="ic"
              type="button"
              class="hb-icon-btn"
              :class="{ on: form.icon === ic }"
              @click="form.icon = ic"
            >
              <AppIcon :icon="ic" :size="18" />
            </button>
          </div>
        </div>
        <label class="hb-field">
          <span>每周目标（0 = 不限）</span>
          <el-input-number v-model="form.weekly_goal" :min="0" :max="7" controls-position="right" />
        </label>
        <label class="hb-field">
          <span>断链自罚（每天，元；填 0 = 关闭）</span>
          <el-input-number v-model="form.penalty_yuan" :min="0" :max="1000" :step="1" :precision="2" controls-position="right" />
        </label>
        <label class="hb-field">
          <span>宽限天数（连续漏的前 N 天不罚）</span>
          <el-input-number v-model="form.penalty_grace" :min="0" :max="7" controls-position="right" />
        </label>
        <p class="hb-form-tip">开了自罚后，漏一天会自动在账本记一笔「断链罚金」支出（个人零花池），漏几天记几笔。</p>
      </div>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="!form.name.trim()" @click="submit">
          {{ form.id ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 「今天」页（v2.46.140）
 *
 * 夜星的两条需求落点：
 *   1) 每天做什么 + 提醒 + 工作台可见 → 本页 + TodayHabitsCard（工作台卡片含每日一次提醒）
 *   2) 完成进度和记录 → 今日完成率环 / 连续天数 / 本周次数 / 最近 30 天热力格 / 累计次数
 *
 * 后端接口是现成的（app/routers/workbench/habits.py），本页只做界面；
 * 数据统一走 stores/habits，保证工作台卡片和本页永远同一个数。
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import BackButton from '@/components/BackButton.vue'
import EmptyState from '@/components/EmptyState.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import IconButton from '@/components/common/IconButton.vue'
import { useHabitsStore } from '@/stores/habits'

const store = useHabitsStore()
const { list, weekly, loading, doneCount, total, progress, pending, bestStreak, allDone } = storeToRefs(store)

const managing = ref(false)
const dialog = ref(false)
const saving = ref(false)
const form = reactive({
  id: 0,
  name: '',
  icon: '✓',
  weekly_goal: 0,
  penalty_yuan: 0,   // 存「元」，提交时转分
  penalty_grace: 0,
})

/** 图标候选：走 AppIcon 的 emoji 查表，命中就画线性图标；没命中的原样显示也不难看 */
const ICON_CHOICES = ['💧', '🏃', '📖', '✍️', '🧘', '💰', '🌙', '☀️', '🥗', '🧹', '📷', '🎯']

const totalCheckins = computed(() => list.value.reduce((s, h) => s + (h.total_count || 0), 0))

function heatCount(h) {
  return (h.heat || []).filter((c) => c.checked).length
}

async function onToggle(h) {
  try {
    await store.toggle(h)
    if (store.allDone && store.total) ElMessage({ message: '今天的都做完了，收工。', type: 'success', duration: 1800 })
  } catch {
    ElMessage({ message: '打卡没成功，再点一次', type: 'warning', duration: 2200 })
  }
}

function openCreate() {
  Object.assign(form, { id: 0, name: '', icon: ICON_CHOICES[0], weekly_goal: 0, penalty_yuan: 0, penalty_grace: 0 })
  dialog.value = true
}

function openEdit(h) {
  Object.assign(form, {
    id: h.id,
    name: h.name,
    icon: h.icon || '✓',
    weekly_goal: h.weekly_goal || 0,
    penalty_yuan: (h.penalty_cents || 0) / 100,
    penalty_grace: h.penalty_grace || 0,
  })
  dialog.value = true
}

async function submit() {
  if (!form.name.trim()) return
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      icon: form.icon,
      color: null,
      weekly_goal: form.weekly_goal || 0,
      // 元 → 分（后端只认分，避免浮点误差）
      penalty_cents: Math.round((Number(form.penalty_yuan) || 0) * 100),
      penalty_grace: form.penalty_grace || 0,
    }
    if (form.id) await store.update(form.id, payload)
    else await store.create(payload)
    dialog.value = false
    ElMessage({ message: form.id ? '已保存' : '已创建，今天就可以开始打卡', type: 'success', duration: 1800 })
  } catch (e) {
    ElMessage({ message: e?.message || '保存失败', type: 'error' })
  } finally {
    saving.value = false
  }
}

async function onRemove(h) {
  try {
    await ElMessageBox.confirm(`删除「${h.name}」会连同它的全部打卡记录一起删掉，确定吗？`, '删除习惯', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch { return }
  try {
    await store.remove(h.id)
    ElMessage({ message: '已删除', type: 'success', duration: 1500 })
  } catch (e) {
    ElMessage({ message: e?.message || '删除失败', type: 'error' })
  }
}

/** 进页面先结算断链罚金（幂等），有新罚单就弹一条，再拉本周复盘 */
async function bootSettle() {
  const items = await store.settle()
  if (!items.length) return
  const yuan = (items.reduce((s, i) => s + i.amount_cents, 0) / 100).toFixed(0)
  ElNotification({
    title: `断链了 ${items.length} 天，已记 ¥${yuan}`,
    message: `账本里多了 ${items.length} 笔「断链罚金」：${items.slice(0, 3).map((i) => `${i.date.slice(5)} ${i.habit}`).join('、')}${items.length > 3 ? ' …' : ''}`,
    type: 'warning',
    duration: 7000,
    position: 'bottom-right',
  })
}

onMounted(async () => {
  try {
    await store.load(true)
  } catch {
    ElMessage({ message: '加载失败，稍后重试', type: 'warning' })
  }
  await bootSettle()
  await store.loadWeekly()
})
</script>

<style scoped>
.hb-page { min-height: 100%; padding: 22px 20px 40px; }
.hb-inner { max-width: 780px; margin: 0 auto; }

/* 页头 */
.hb-head { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.hb-titles { flex: 1; min-width: 0; }
.hb-title {
  margin: 0; font-size: 26px; font-weight: 700; letter-spacing: .02em;
  font-family: 'Noto Serif SC', 'Songti SC', Georgia, serif;
  color: var(--tc-text, #0b1622);
}
.hb-sub { margin: 3px 0 0; font-size: 12.5px; color: var(--tc-text-2, #46586e); }
.hb-head-right { display: flex; align-items: center; gap: 8px; flex: none; }

/* 进度 */
.hb-progress { display: flex; align-items: center; gap: 16px; padding: 16px 18px; margin-bottom: 14px; }
.hb-ring { position: relative; width: 64px; height: 64px; flex: none; }
.hb-ring svg { width: 64px; height: 64px; transform: rotate(-90deg); }
.hb-ring-bg { fill: none; stroke: var(--tc-line, rgba(15, 60, 110, .14)); stroke-width: 6; }
.hb-ring-fg {
  fill: none; stroke: var(--tc-cyan, #0e93b8); stroke-width: 6; stroke-linecap: round;
  transition: stroke-dasharray .35s cubic-bezier(.2, .8, .2, 1);
}
.hb-ring-fg.full { stroke: var(--color-success, #0f7a56); }
.hb-ring-txt {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--tc-text, #0b1622);
}
.hb-ring-txt i { font-size: 9px; font-style: normal; margin-left: 1px; opacity: .6; }
.hb-progress-side { min-width: 0; }
.hb-progress-line { font-size: 14px; font-weight: 600; color: var(--tc-text, #0b1622); }
.hb-progress-line b { color: var(--tc-cyan, #0e93b8); }
.hb-progress-line.done { color: var(--color-success, #0f7a56); }
.hb-progress-hint { margin-top: 4px; font-size: 11.5px; color: var(--tc-text-3, #5b6f8a); }

/* 列表 */
.hb-card { padding: 10px 8px; margin-bottom: 14px; }
.hb-card-head { display: flex; align-items: baseline; justify-content: space-between; padding: 6px 10px 10px; }
.hb-card-title { margin: 0; font-size: 13.5px; font-weight: 700; color: var(--tc-text, #0b1622); }
.hb-card-sub { font-size: 11.5px; color: var(--tc-text-3, #5b6f8a); }

.hb-list { list-style: none; margin: 0; padding: 0; }
.hb-row + .hb-row { border-top: 1px dashed var(--tc-line, rgba(15, 60, 110, .14)); }
.hb-hit, .hb-manage {
  width: 100%; display: flex; align-items: center; gap: 11px;
  padding: 12px 10px; border: 0; background: transparent; border-radius: 10px;
  font: inherit; text-align: left; color: var(--tc-text, #0b1622); cursor: pointer;
}
.hb-hit:hover { background: rgba(14, 147, 184, .07); }
.hb-manage { cursor: default; }
.hb-ico { display: inline-flex; color: var(--tc-cyan, #0e93b8); flex: none; }
.hb-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.hb-name { font-size: 14.5px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hb-row.done .hb-name { color: var(--tc-text-2, #46586e); }
.hb-meta { font-size: 11.5px; color: var(--tc-text-3, #5b6f8a); font-variant-numeric: tabular-nums; }
.hb-tick {
  width: 24px; height: 24px; border-radius: 50%; flex: none;
  border: 1.5px solid var(--tc-line-strong, rgba(15, 60, 110, .26));
  display: flex; align-items: center; justify-content: center; color: transparent;
  transition: background-color .16s, border-color .16s, color .16s;
}
.hb-tick svg { width: 15px; height: 15px; }
.hb-tick.on {
  background: var(--tc-cyan, #0e93b8); border-color: var(--tc-cyan, #0e93b8); color: #fff;
}

/* 热力 */
.hb-heat-row { display: flex; align-items: center; gap: 10px; padding: 7px 10px; }
.hb-heat-name {
  width: 88px; flex: none; font-size: 12px; color: var(--tc-text-2, #46586e);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.hb-cells { display: flex; gap: 3px; flex: 1; min-width: 0; }
.hb-cells i {
  /* 30 格排一行：给明确高度，别靠 aspect-ratio（flex 里宽度先定，高度会被算成 0，看着像虚线） */
  flex: 1 1 0; height: 9px; min-width: 4px; border-radius: 2.5px;
  background: var(--tc-line, rgba(15, 60, 110, .14));
}
.hb-cells i.on { background: var(--tc-cyan, #0e93b8); }
.hb-heat-n { width: 42px; text-align: right; font-size: 11px; color: var(--tc-text-3, #5b6f8a); font-variant-numeric: tabular-nums; }

.hb-empty { padding: 20px 0; }

/* 本周复盘 */
.hb-wk { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; padding: 4px 10px 2px; }
.hb-wk-stat {
  display: flex; flex-direction: column; align-items: center; gap: 3px;
  padding: 10px 4px; border-radius: 10px; background: rgba(14, 147, 184, .06);
}
.hb-wk-stat b { font-size: 17px; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--tc-text, #0b1622); }
.hb-wk-stat b i { font-size: 10px; font-style: normal; opacity: .55; margin-left: 1px; }
.hb-wk-stat span { font-size: 11px; color: var(--tc-text-3, #5b6f8a); }
.hb-wk-stat.warn { background: rgba(255, 77, 109, .09); }
.hb-wk-stat.warn b { color: var(--color-danger, #cf2540); }
.hb-wk-text { margin: 10px 10px 0; font-size: 12.5px; color: var(--tc-text-2, #46586e); line-height: 1.65; }
.hb-wk-advice {
  margin: 8px 10px 6px; padding-left: 8px; font-size: 12.5px; line-height: 1.65;
  color: var(--tc-text, #0b1622); border-left: 2px solid var(--tc-cyan, #0e93b8);
}
.hb-wk-advice span {
  display: inline-block; margin-right: 6px; padding: 1px 6px; border-radius: 999px;
  background: rgba(14, 147, 184, .12); color: var(--tc-cyan-deep, #0a708c);
  font-size: 10.5px; font-weight: 700;
}

/* 弹窗表单 */
.hb-form { display: flex; flex-direction: column; gap: 14px; }
.hb-field { display: flex; flex-direction: column; gap: 6px; font-size: 12.5px; color: var(--tc-text-2, #46586e); }
.hb-icons { display: flex; flex-wrap: wrap; gap: 6px; }
.hb-icon-btn {
  width: 34px; height: 34px; border-radius: 9px; border: 1px solid var(--tc-line, rgba(15, 60, 110, .14));
  background: transparent; color: var(--tc-text-2, #46586e); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.hb-icon-btn.on { border-color: var(--tc-cyan, #0e93b8); color: var(--tc-cyan, #0e93b8); background: rgba(14, 147, 184, .08); }
.hb-form-tip { margin: -4px 0 0; font-size: 11.5px; line-height: 1.6; color: var(--tc-text-3, #5b6f8a); }

/* 手机端 */
:global(#app.is-mobile .hb-page) { padding: 14px 14px 90px; }
:global(#app.is-mobile .hb-title) { font-size: 30px; }
:global(#app.is-mobile .hb-progress) { padding: 14px; gap: 12px; }
:global(#app.is-mobile .hb-heat-name) { width: 68px; }
:global(#app.is-mobile .hb-cells i) { height: 8px; min-width: 3px; border-radius: 2px; }
</style>
