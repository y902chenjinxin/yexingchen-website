<template>
  <section v-if="data" class="qz glass-card" aria-label="每日一题">
    <header class="qz-head">
      <div class="qz-title">
        <span class="qz-tag">答题</span>
        每日一题
        <em class="qz-meta">{{ data.cat }} · 第 {{ data.cat_position }}/{{ data.cat_total }} 条</em>
      </div>
      <div class="qz-nav">
        <button v-if="wrongN" class="qz-wrong" :title="`错题本里有 ${wrongN} 道题`" @click="openWrong">
          错题 {{ wrongN }}
        </button>
        <button class="qz-nav-btn" title="看昨天" @click="go(-1)">‹</button>
        <span class="qz-date">{{ (data.date || '').slice(5) }}</span>
        <button class="qz-nav-btn" title="看明天" @click="go(1)">›</button>
      </div>
    </header>

    <div class="qz-hd">
      <span class="qz-lv" :class="'lv' + data.level">{{ LV[data.level] || '中等' }}</span>
      <p class="qz-q">{{ data.q }}</p>
    </div>

    <!-- 资料分析题带一张小表（v2.46.271）：手机放得下就放，放不下横向滚 -->
    <div v-if="data.table" class="qz-tablewrap">
      <table class="qz-table">
        <caption v-if="data.table.caption">{{ data.table.caption }}</caption>
        <thead>
          <tr><th v-for="(h, i) in data.table.head" :key="i">{{ h }}</th></tr>
        </thead>
        <tbody>
          <tr v-for="(row, r) in data.table.rows" :key="r">
            <td v-for="(c, i) in row" :key="i">{{ c }}</td>
          </tr>
        </tbody>
      </table>
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

      <!-- 相关阅读（v2.46.273）：做完题还能往下走一步。
           175 题里只有 19 题真的在考某个可命名的效应，其余是纯计算/字面题，
           本来就没有延伸可读 —— 所以没有 related 就不渲染，不留空框。 -->
      <div v-if="data.related" class="qz-rel">
        <button class="qz-rel-head" @click="relOpen = !relOpen">
          <span class="qz-rel-tag">相关阅读</span>
          <b>{{ data.related.name }}</b>
          <em>{{ data.related.one_line }}</em>
          <i class="qz-rel-arw" :class="{ on: relOpen }">⌄</i>
        </button>

        <div v-if="relOpen" class="qz-rel-body">
          <p class="qz-rel-note"><b>它怎么运作</b><span>{{ data.related.shape }}</span></p>
          <p class="qz-rel-note"><b>举个例子</b><span>{{ data.related.example }}</span></p>
          <p class="qz-rel-note qz-rel-note--how"><b>怎么拆</b><span>{{ data.related.howto }}</span></p>
          <p class="qz-rel-note qz-rel-note--caveat"><b>别过头</b><span>{{ data.related.caveat }}</span></p>
        </div>
      </div>

      <div class="qz-foot">
        <div class="qz-days" title="最近 7 天">
          <span
            v-for="d in days"
            :key="d.key"
            class="qz-day"
            :class="[d.state, { today: d.today }]"
            :title="`${d.label} · ${d.state === 'ok' ? '答对' : d.state === 'bad' ? '答错' : '未答'}`"
          />
        </div>
        <span class="qz-stat">
          已答 {{ stats.total }} 题 · 正确 {{ stats.correct }} 题<template v-if="stats.total">（{{ Math.round((stats.correct / stats.total) * 100) }}%）</template>
        </span>
      </div>
    </div>

    <QuizWrongDrawer ref="drawer" />
  </section>
</template>

<script setup>
/**
 * 工作台「每日一题」卡（v2.46.270，v2.46.273 加错题本 / 相关阅读 / 七天格）
 *
 * 夜星：
 * > 给我找一些脑筋急转弯、考公的题目…每天以卡片形式出一题，要有选项和最终答案。
 *
 * 三张卡的分工：
 *   定律卡 —— 世界怎么运转（读）
 *   逻辑卡 —— 怎么想（读）
 *   这张   —— **做**：四选一，答完才给解析。
 *
 * 三件配套（v2.46.273）：
 *   错题本   —— 答错的自动收进 localStorage，顶部「错题 N」进抽屉看
 *   相关阅读 —— 19 道题挂着概念（沉没成本/确认偏误…），可展开完整解释
 *   七天格   —— 最近 7 天对错一眼看到，比一个百分比更有推动力
 *
 * 日期一律用「本地年月日」拼字符串，不走 toISOString（有过时区退一天的坑）。
 */
import { computed, onMounted, ref } from 'vue'
import { workbenchApi } from '@/api/workbench'
import { addWrong, readWrong } from '@/composables/useQuizWrong'
import QuizWrongDrawer from '@/components/workbench/QuizWrongDrawer.vue'

const KEY = ['A', 'B', 'C', 'D']
const LV = { 1: '简单', 2: '中等', 3: '烧脑' }
const STATS_KEY = 'xh_quiz_stats'

const data = ref(null)
const picked = ref(null)
const offset = ref(0)
const stats = ref({ total: 0, correct: 0 })
const wrongN = ref(0)
const drawer = ref(null)
const relOpen = ref(false)

const answered = computed(() => picked.value !== null)
const isRight = computed(() => answered.value && picked.value === data.value?.answer)

const fmtDate = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
const dayKey = (d) => `xh_quiz_${d}`

/** 最近 7 天（含今天）：对 / 错 / 未答，做连续性反馈 */
const days = computed(() => {
  const out = []
  const now = new Date()
  for (let k = 6; k >= 0; k--) {
    // 用构造器减天数，不用毫秒加法（跨月、夏令时会错一天）
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - k)
    const key = fmtDate(d)
    let state = 'none'
    try {
      const rec = JSON.parse(localStorage.getItem(dayKey(key)) || 'null')
      if (rec) state = rec.right ? 'ok' : 'bad'
    } catch { state = 'none' }
    out.push({ key, label: `${d.getMonth() + 1}/${d.getDate()}`, state, today: k === 0 })
  }
  return out
})

function readStats() {
  try {
    const s = JSON.parse(localStorage.getItem(STATS_KEY) || '{}')
    stats.value = { total: Number(s.total) || 0, correct: Number(s.correct) || 0 }
  } catch { stats.value = { total: 0, correct: 0 } }
}

function refreshWrong() { wrongN.value = readWrong().length }

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
  const d = data.value
  const right = i === d.answer
  try {
    localStorage.setItem(dayKey(d.date), JSON.stringify({ id: d.id, picked: i, right }))
    const s = stats.value
    localStorage.setItem(STATS_KEY, JSON.stringify({
      total: s.total + 1, correct: s.correct + (right ? 1 : 0),
    }))
  } catch { /* 隐私模式写不进去，不影响答题 */ }
  // 答错才进错题本：存完整快照，日后不依赖题库还在不在
  if (!right) {
    addWrong({
      id: d.id, date: d.date, q: d.q, options: d.options, answer: d.answer,
      picked: i, why: d.why, trick: d.trick, topic: d.topic || '',
    })
  }
  readStats()
  refreshWrong()
}

function optClass(i) {
  if (!answered.value) return ''
  if (i === data.value.answer) return 'is-ok'
  if (i === picked.value) return 'is-bad'
  return 'is-dim'
}

function openWrong() { drawer.value?.show() }

async function load(off = 0) {
  try {
    const res = await workbenchApi.quiz.today(off)
    data.value = res?.data || res || null
    offset.value = off
    relOpen.value = false
    restore()
  } catch { /* 静默失败，不影响工作台其它模块 */ }
}

function go(delta) {
  load(offset.value + delta)
}

onMounted(() => {
  readStats()
  refreshWrong()
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

/* 错题入口：只在有错题时出现，带数字才像「有待办」 */
.qz-wrong {
  border: 1px solid rgba(201, 105, 74, .45); border-radius: 999px;
  background: rgba(201, 105, 74, .07); cursor: pointer; padding: 2px 9px;
  font: inherit; font-size: 11px; font-weight: 600; color: #b4552f;
}
.qz-wrong:hover { background: rgba(201, 105, 74, .14); }

.qz-hd { display: flex; align-items: flex-start; gap: 9px; }
.qz-lv {
  flex: none; margin-top: 2px; padding: 1px 7px; border-radius: 5px;
  font-size: 10.5px; font-weight: 600; letter-spacing: .04em;
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .16)); color: var(--tc-text-3, #5b6f8a);
}
.qz-lv.lv3 { border-color: rgba(201, 105, 74, .5); color: #b4552f; }
.qz-q { margin: 0; font-size: 14px; line-height: 1.8; color: var(--tc-text, #0b1622); }

/* ---------- 资料分析的小表格 ---------- */
.qz-tablewrap { margin-top: 10px; overflow-x: auto; -webkit-overflow-scrolling: touch; }
.qz-table {
  width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums;
  font-size: 12px; line-height: 1.6;
}
.qz-table caption {
  caption-side: top; text-align: left; padding-bottom: 5px;
  font-size: 11.5px; color: var(--tc-text-3, #5b6f8a); letter-spacing: .01em;
}
.qz-table th, .qz-table td {
  padding: 6px 10px; border-bottom: 1px solid var(--tc-line, rgba(15, 60, 110, .1));
  text-align: right; white-space: nowrap; color: var(--tc-text-2, #46586e);
}
.qz-table th {
  font-weight: 600; font-size: 11.5px; color: var(--tc-text-3, #5b6f8a);
  background: rgba(15, 60, 110, .035); border-bottom-color: var(--tc-line, rgba(15, 60, 110, .16));
}
.qz-table th:first-child, .qz-table td:first-child {
  text-align: left; font-weight: 500; color: var(--tc-text, #0b1622);
}
.qz-table tbody tr:last-child td { border-bottom: 0; }

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

.qz-opt.is-ok { border-color: rgba(14, 147, 184, .55); background: rgba(14, 147, 184, .09); }
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

/* ---------- 相关阅读 ---------- */
.qz-rel { margin-top: 11px; border: 1px solid var(--tc-line, rgba(15, 60, 110, .12)); border-radius: 11px; overflow: hidden; }
.qz-rel-head {
  width: 100%; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 9px 12px; border: 0; background: rgba(15, 60, 110, .028);
  cursor: pointer; text-align: left; font: inherit;
}
.qz-rel-head:hover { background: rgba(14, 147, 184, .06); }
.qz-rel-tag {
  flex: none; font-size: 10px; font-weight: 600; letter-spacing: .06em;
  padding: 1px 6px; border-radius: 4px;
  background: rgba(14, 147, 184, .1); color: var(--tc-cyan-deep, #0a708c);
}
.qz-rel-head b { font-size: 12.5px; font-weight: 600; color: var(--tc-text, #0b1622); }
.qz-rel-head em {
  flex: 1; min-width: 0; font-style: normal; font-size: 11.5px; color: var(--tc-text-3, #5b6f8a);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.qz-rel-arw { flex: none; font-style: normal; font-size: 12px; color: var(--tc-text-3, #5b6f8a); transition: transform .18s; }
.qz-rel-arw.on { transform: rotate(180deg); }

.qz-rel-body { padding: 4px 12px 10px; }
.qz-rel-note {
  margin: 7px 0 0; display: grid; grid-template-columns: 76px minmax(0, 1fr); gap: 9px;
  font-size: 12.5px; line-height: 1.85; color: var(--tc-text-2, #46586e);
}
.qz-rel-note b {
  font-size: 11px; font-weight: 600; color: var(--tc-cyan-deep, #0a708c);
  border-left: 2px solid var(--tc-cyan, #0e93b8); padding-left: 8px; line-height: 1.7;
}
.qz-rel-note--how b { color: var(--lj-seal, #a9812f); border-left-color: var(--lj-seal, #a9812f); }
.qz-rel-note--caveat b { color: #b4552f; border-left-color: #c9694a; }

/* ---------- 底部：七天格 + 累计 ---------- */
.qz-foot {
  margin: 12px 0 0; padding-top: 10px;
  border-top: 1px solid var(--tc-line, rgba(15, 60, 110, .08));
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
}
.qz-days { display: flex; gap: 4px; }
.qz-day {
  width: 16px; height: 16px; border-radius: 4px;
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .16)); background: transparent;
}
.qz-day.ok { background: var(--tc-cyan, #0e93b8); border-color: var(--tc-cyan, #0e93b8); }
.qz-day.bad { background: #c9694a; border-color: #c9694a; }
.qz-day.today { box-shadow: 0 0 0 2px rgba(14, 147, 184, .18); }
.qz-stat { font-size: 11px; color: var(--tc-text-3, #5b6f8a); letter-spacing: .02em; }

@media (max-width: 520px) {
  .qz { padding: 14px 15px; }
  .qz-q { font-size: 13.5px; line-height: 1.75; }
  .qz-opt { padding: 10px 11px; }
  .qz-txt { font-size: 12.5px; }
  .qz-trick, .qz-rel-note { grid-template-columns: 1fr; gap: 4px; }
  .qz-trick b, .qz-rel-note b { border-left: 0; padding-left: 0; }
  .qz-trick b::before, .qz-rel-note b::before { content: '· '; }
  .qz-rel-head em { display: none; }
}
</style>
