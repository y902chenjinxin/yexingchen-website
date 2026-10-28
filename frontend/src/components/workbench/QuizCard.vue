<template>
  <section v-if="data" class="qz glass-card" aria-label="每日一题">
    <header class="qz-head">
      <div class="qz-title">
        <span class="qz-tag">答题</span>
        每日一题
        <em class="qz-meta">{{ data.cat }} · 第 {{ data.cat_position }}/{{ data.cat_total }} 条</em>
      </div>
      <div class="qz-nav">
        <button class="qz-nav-btn" title="看昨天" @click="go(-1)">‹</button>
        <span class="qz-date">{{ (data.date || '').slice(5) }}</span>
        <button class="qz-nav-btn" title="看明天" @click="go(1)">›</button>
      </div>
    </header>

    <div class="qz-hd">
      <span class="qz-lv" :class="'lv' + data.level">{{ LV[data.level] || '中等' }}</span>
      <p class="qz-q">{{ data.q }}</p>
    </div>

    <ul class="qz-opts">
      <li v-for="(o, i) in data.options" :key="i">
        <button
          class="qz-opt"
          :class="optClass(i)"
          :disabled="answered"
          @click="choose(i)"
        >
          <span class="qz-key">{{ KEY[i] }}</span>
          <span class="qz-txt">{{ o }}</span>
          <span v-if="answered && i === data.answer" class="qz-mark ok">✓</span>
          <span v-else-if="answered && i === picked" class="qz-mark bad">✗</span>
        </button>
      </li>
    </ul>

    <!-- 答完才展开：先做题，再看解析，顺序别反 -->
    <div v-if="answered" class="qz-sol">
      <p class="qz-verdict" :class="{ bad: !isRight }">
        {{ isRight ? '答对了' : `答错了 · 正确答案是 ${KEY[data.answer]}` }}
      </p>
      <p class="qz-why">{{ data.why }}</p>
      <p class="qz-trick"><b>绕过这个坑</b>{{ data.trick }}</p>
    </div>

    <p v-if="answered" class="qz-foot">
      已答 {{ stats.total }} 题 · 正确 {{ stats.correct }} 题<template v-if="stats.total">（{{ Math.round((stats.correct / stats.total) * 100) }}%）</template>
      · 题库 {{ data.total }} 题，每天一题
    </p>
  </section>
</template>

<script setup>
/**
 * 工作台「每日一题」卡（v2.46.270）
 *
 * 夜星：
 * > 给我找一些脑筋急转弯的题目，考公的题目等等，就是那种绕来绕去的，
 * > 但是能扩张思维边界的，然后每天以卡片形式出一题，要有选项和最终答案的。
 *
 * 和另两张卡的分工：
 *   定律卡 —— 世界怎么运转（读）
 *   逻辑卡 —— 怎么想（读）
 *   这张   —— **做**：四选一，答完才给解析。光看「确认偏误」的定义记不住，
 *             被它坑一次才记得住。
 *
 * 答题记录存 localStorage（按日期 key，同一天只累计一次），不上传后端：
 * 一天一题的数据量不值得建表，也不能跨设备同步 —— 想要同步再说。
 */
import { computed, onMounted, ref } from 'vue'
import { workbenchApi } from '@/api/workbench'

const KEY = ['A', 'B', 'C', 'D']
const LV = { 1: '简单', 2: '中等', 3: '烧脑' }
const STATS_KEY = 'xh_quiz_stats'

const data = ref(null)
const picked = ref(null)
const offset = ref(0)
const stats = ref({ total: 0, correct: 0 })

const answered = computed(() => picked.value !== null)
const isRight = computed(() => answered.value && picked.value === data.value?.answer)

const dayKey = (d) => `xh_quiz_${d}`

function readStats() {
  try {
    const s = JSON.parse(localStorage.getItem(STATS_KEY) || '{}')
    stats.value = { total: Number(s.total) || 0, correct: Number(s.correct) || 0 }
  } catch { stats.value = { total: 0, correct: 0 } }
}

/** 恢复这一天的作答记录；题目换过（id 对不上）就当没答过 */
function restore() {
  picked.value = null
  if (!data.value) return
  try {
    const rec = JSON.parse(localStorage.getItem(dayKey(data.value.date)) || 'null')
    if (rec && rec.id === data.value.id && Number.isInteger(rec.picked)) picked.value = rec.picked
  } catch { picked.value = null }
}

function choose(i) {
  if (answered.value || !data.value) return
  picked.value = i
  const right = i === data.value.answer
  try {
    localStorage.setItem(dayKey(data.value.date), JSON.stringify({
      id: data.value.id, picked: i, right,
    }))
    const s = stats.value
    localStorage.setItem(STATS_KEY, JSON.stringify({
      total: s.total + 1, correct: s.correct + (right ? 1 : 0),
    }))
  } catch { /* 隐私模式写不进去，不影响答题 */ }
  readStats()
}

function optClass(i) {
  if (!answered.value) return ''
  if (i === data.value.answer) return 'is-ok'
  if (i === picked.value) return 'is-bad'
  return 'is-dim'
}

async function load(off = 0) {
  try {
    const res = await workbenchApi.quiz.today(off)
    data.value = res?.data || res || null
    offset.value = off
    restore()
  } catch { /* 静默失败，不影响工作台其它模块 */ }
}

function go(delta) {
  load(offset.value + delta)
}

onMounted(() => {
  readStats()
  load(0)
})
</script>

<style scoped>
.qz { padding: 16px 20px; }

.qz-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.qz-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; letter-spacing: .02em; color: var(--tc-text, #0b1622); }
.qz-tag {
  font-size: 10.5px; font-weight: 600; letter-spacing: .08em; padding: 2px 7px; border-radius: 6px;
  background: rgba(24, 24, 27, .08); color: var(--tc-text-2, #46586e);
}
.qz-meta { font-style: normal; font-size: 11.5px; font-weight: 600; color: var(--tc-text-3, #5b6f8a); }
.qz-nav { display: flex; align-items: center; gap: 4px; }
.qz-nav-btn {
  width: 22px; height: 22px; border: 0; background: transparent; cursor: pointer;
  color: var(--tc-text-3, #5b6f8a); font-size: 15px; line-height: 1; border-radius: 6px;
}
.qz-nav-btn:hover { background: rgba(14, 147, 184, .1); color: var(--tc-cyan, #0e93b8); }
.qz-date { font-size: 11px; color: var(--tc-text-3, #5b6f8a); font-variant-numeric: tabular-nums; min-width: 38px; text-align: center; }

.qz-hd { display: flex; align-items: flex-start; gap: 9px; }
.qz-lv {
  flex: none; margin-top: 2px; padding: 1px 7px; border-radius: 5px;
  font-size: 10.5px; font-weight: 600; letter-spacing: .04em;
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .16)); color: var(--tc-text-3, #5b6f8a);
}
.qz-lv.lv3 { border-color: rgba(201, 105, 74, .5); color: #b4552f; }
.qz-q { margin: 0; font-size: 14px; line-height: 1.8; color: var(--tc-text, #0b1622); }

/* ---------- 选项 ---------- */
.qz-opts { list-style: none; margin: 12px 0 0; padding: 0; display: grid; gap: 7px; }
.qz-opt {
  width: 100%; display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; border-radius: 10px; cursor: pointer; text-align: left;
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .14));
  background: transparent; font: inherit;
  transition: border-color .15s, background-color .15s, opacity .15s;
}
.qz-opt:hover:not(:disabled) {
  border-color: var(--tc-cyan, #0e93b8);
  background: rgba(14, 147, 184, .05);
}
.qz-opt:disabled { cursor: default; }
.qz-key {
  flex: none; width: 20px; height: 20px; border-radius: 50%;
  display: grid; place-items: center;
  font-size: 11px; font-weight: 700; letter-spacing: 0;
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .2)); color: var(--tc-text-3, #5b6f8a);
}
.qz-txt { flex: 1; min-width: 0; font-size: 13px; line-height: 1.65; color: var(--tc-text-2, #46586e); }
.qz-mark { flex: none; font-size: 14px; font-weight: 700; }

.qz-opt.is-ok {
  border-color: rgba(14, 147, 184, .55); background: rgba(14, 147, 184, .09);
}
.qz-opt.is-ok .qz-key { border-color: var(--tc-cyan, #0e93b8); background: var(--tc-cyan, #0e93b8); color: #fff; }
.qz-opt.is-ok .qz-txt { color: var(--tc-text, #0b1622); font-weight: 500; }
.qz-opt.is-ok .qz-mark { color: var(--tc-cyan-deep, #0a708c); }

.qz-opt.is-bad { border-color: rgba(201, 105, 74, .55); background: rgba(201, 105, 74, .08); }
.qz-opt.is-bad .qz-key { border-color: #c9694a; background: #c9694a; color: #fff; }
.qz-opt.is-bad .qz-mark { color: #b4552f; }

.qz-opt.is-dim { opacity: .5; }

/* ---------- 解析 ---------- */
.qz-sol { margin-top: 14px; }
.qz-verdict {
  margin: 0 0 8px; font-size: 13px; font-weight: 700; letter-spacing: .01em;
  color: var(--tc-cyan-deep, #0a708c);
}
.qz-verdict.bad { color: #b4552f; }
.qz-why {
  margin: 0; padding: 11px 13px; border-radius: 10px;
  background: rgba(15, 60, 110, .035);
  font-size: 13px; line-height: 1.9; color: var(--tc-text-2, #46586e); white-space: pre-wrap;
}
.qz-trick {
  margin: 9px 0 0; display: grid; grid-template-columns: 80px minmax(0, 1fr); gap: 10px;
  font-size: 12.5px; line-height: 1.85; color: var(--tc-text-2, #46586e);
}
.qz-trick b {
  font-size: 11px; font-weight: 600; letter-spacing: .04em;
  color: var(--lj-seal, #a9812f); border-left: 2px solid var(--lj-seal, #a9812f);
  padding-left: 8px; line-height: 1.7;
}

.qz-foot {
  margin: 12px 0 0; padding-top: 9px;
  border-top: 1px solid var(--tc-line, rgba(15, 60, 110, .08));
  font-size: 11px; color: var(--tc-text-3, #5b6f8a); letter-spacing: .02em;
}

@media (max-width: 520px) {
  .qz { padding: 14px 15px; }
  .qz-q { font-size: 13.5px; line-height: 1.75; }
  .qz-opt { padding: 10px 11px; }
  .qz-txt { font-size: 12.5px; }
  .qz-trick { grid-template-columns: 1fr; gap: 4px; }
  .qz-trick b { border-left: 0; padding-left: 0; }
  .qz-trick b::before { content: '· '; }
}
</style>
