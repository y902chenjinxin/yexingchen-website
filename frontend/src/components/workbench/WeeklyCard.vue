<template>
  <section v-if="data" class="wk glass-card" aria-label="本周回顾">
    <button class="wk-row" :aria-expanded="open" @click="open = !open">
      <span class="wk-tag">本周</span>
      <span class="wk-span">{{ span }}</span>
      <span class="wk-key">
        <template v-if="m.expense_count">支出 ¥{{ fmtMoney(m.expense_yuan) }}</template>
        <template v-if="m.habit_due"> · 习惯 {{ m.habit_done }}/{{ m.habit_due }}</template>
        <template v-if="m.weight_delta !== null && m.weight_delta !== undefined"> · 体重 {{ m.weight_delta > 0 ? '+' : '' }}{{ m.weight_delta }}kg</template>
        <template v-if="!m.expense_count && !m.habit_due">这一周没什么记录</template>
      </span>
      <i class="wk-arw" :class="{ on: open }">⌄</i>
    </button>

    <div v-if="open" class="wk-body">
      <p class="wk-text">{{ data.body }}</p>

      <dl class="wk-grid">
        <div v-if="m.expense_count" class="wk-cell">
          <dt>支出</dt>
          <dd>{{ m.expense_count }} 笔 · ¥{{ fmtMoney(m.expense_yuan) }}</dd>
        </div>
        <div v-if="m.income_yuan" class="wk-cell">
          <dt>收入</dt>
          <dd>¥{{ fmtMoney(m.income_yuan) }}</dd>
        </div>
        <div v-if="m.habit_due" class="wk-cell">
          <dt>习惯完成</dt>
          <dd>{{ m.habit_done }}/{{ m.habit_due }}（{{ Math.round((m.habit_done / m.habit_due) * 100) }}%）</dd>
        </div>
        <div v-if="m.weight_delta !== null && m.weight_delta !== undefined" class="wk-cell">
          <dt>体重</dt>
          <dd>{{ m.weight_from }} → {{ m.weight_to }}</dd>
        </div>
        <div v-if="m.task_done || m.task_open" class="wk-cell">
          <dt>任务</dt>
          <dd>完成 {{ m.task_done }}<template v-if="m.task_open"> · 待办 {{ m.task_open }}</template></dd>
        </div>
        <div v-if="m.quiz_total" class="wk-cell">
          <dt>答题</dt>
          <dd>{{ m.quiz_correct }}/{{ m.quiz_total }} 对</dd>
        </div>
      </dl>

      <p class="wk-foot">
        {{ data.week_start.slice(5) }} ~ {{ data.week_end.slice(5) }} · 每周一自动汇总上一周
      </p>
    </div>
  </section>
</template>

<script setup>
/**
 * 工作台「本周回顾」卡（v2.46.276）
 *
 * 夜星：「我不知道还应该加些什么了，没有应用场景了。」
 *
 * 判断是：他不缺功能，缺**数据汇总**。记账、打卡、体重、任务、答题各自躺在各自页面，
 * 「这周过得怎么样」只能靠回忆。这张卡把它们串成一段话。
 *
 * 形态刻意做得矮：收起时只有一行（周区间 + 三个关键数），点开才看正文与明细。
 * 首页已经被我加过太多东西，这次不再占一整屏。
 *
 * 正文由后端规则模板生成（不依赖 LLM），所以每周一定会有内容，也不会因为接口挂了空白。
 */
import { computed, onMounted, ref } from 'vue'
import { workbenchApi } from '@/api/workbench'

const data = ref(null)
const open = ref(false)

const m = computed(() => data.value?.metrics || {})
const span = computed(() => {
  if (!data.value) return ''
  return `${data.value.week_start.slice(5)} ~ ${data.value.week_end.slice(5)}`
})

const fmtMoney = (v) => Number(v || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })

onMounted(async () => {
  try {
    const res = await workbenchApi.weekly.latest()
    data.value = res?.data || res || null
  } catch { /* 静默失败，不影响工作台其它模块 */ }
})
</script>

<style scoped>
.wk { padding: 0; overflow: hidden; }

/* 收起态：一行。不占地方是这次的硬要求。 */
.wk-row {
  width: 100%; display: flex; align-items: center; gap: 8px;
  padding: 11px 16px; border: 0; background: transparent;
  cursor: pointer; font: inherit; text-align: left;
  transition: background-color .15s;
}
.wk-row:hover { background: rgba(14, 147, 184, .045); }

.wk-tag {
  flex: none; font-size: 10.5px; font-weight: 600; letter-spacing: .08em;
  padding: 2px 7px; border-radius: 6px;
  background: rgba(24, 24, 27, .08); color: var(--tc-text-2, #46586e);
}
.wk-span {
  flex: none; font-size: 12px; color: var(--tc-text-3, #5b6f8a);
  font-variant-numeric: tabular-nums;
}
.wk-key {
  flex: 1; min-width: 0; font-size: 12.5px; color: var(--tc-text-2, #46586e);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.wk-arw {
  flex: none; font-style: normal; font-size: 12px; color: var(--tc-text-3, #5b6f8a);
  transition: transform .18s;
}
.wk-arw.on { transform: rotate(180deg); }

.wk-body { padding: 2px 16px 14px; }
.wk-text {
  margin: 0 0 11px; padding: 11px 13px; border-radius: 10px;
  background: rgba(15, 60, 110, .035);
  font-size: 13px; line-height: 1.95; color: var(--tc-text-2, #46586e);
}

.wk-grid {
  margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px 14px;
}
.wk-cell { display: flex; flex-direction: column; gap: 2px; }
.wk-cell dt { font-size: 10.5px; letter-spacing: .04em; color: var(--tc-text-3, #5b6f8a); }
.wk-cell dd {
  margin: 0; font-size: 12.5px; font-weight: 500;
  color: var(--tc-text, #0b1622); font-variant-numeric: tabular-nums;
}

.wk-foot {
  margin: 11px 0 0; padding-top: 9px;
  border-top: 1px solid var(--tc-line, rgba(15, 60, 110, .08));
  font-size: 11px; color: var(--tc-text-3, #5b6f8a); letter-spacing: .02em;
}

@media (max-width: 520px) {
  .wk-row { padding: 10px 15px; gap: 6px; flex-wrap: wrap; }
  .wk-key { flex: 1 0 100%; order: 3; font-size: 12px; }
  .wk-arw { margin-left: auto; }
  .wk-body { padding: 2px 15px 13px; }
  .wk-text { font-size: 12.5px; line-height: 1.9; }
  .wk-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px 10px; }
}
</style>
