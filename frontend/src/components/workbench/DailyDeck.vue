<template>
  <section class="dk" aria-label="今日阅读">
    <div class="dk-bar">
      <div class="dk-chips" role="tablist">
        <button
          v-for="c in cards"
          :key="c.key"
          class="dk-chip"
          :class="{ on: cur === c.key, seen: seen.has(c.key) }"
          role="tab"
          :aria-selected="cur === c.key"
          @click="pick(c.key)"
        >
          {{ c.label }}
        </button>
      </div>
      <span class="dk-prog" :title="`今天看过 ${seen.size} 张`">{{ seen.size }}/{{ cards.length }}</span>
    </div>

    <!-- 只挂载当前这张：其余不渲染，也就不发请求 -->
    <component :is="curComp" :key="cur" class="dk-card" />
  </section>
</template>

<script setup>
/**
 * 「今日阅读」容器（v2.46.273）
 *
 * 夜星：「按你推荐的来，但是我希望全部一轮做完。」
 *
 * 起因是我连续三轮往首页加卡：英语 / 知识 / 场景 / 定律 / 逻辑 / 答题，
 * 六张同形同重的卡纵向堆叠，手机一屏只到「今天要做」，要滑两屏才到底。
 *
 * 现在收进一个容器：顶部一排 chips，只渲染选中的那一张。
 * - 默认展开「今天还没看过的第一张」——点击变成一件有进度的事，不是多一道门
 * - 右上角 x/6 就是进度，不再额外做红点
 * - 记住上次看的那张（换了页面回来还在原位）
 *
 * 桌面端不用这个组件：屏幕够宽，走两列网格（见 WorkbenchView 的 .bento-learn-grid）。
 */
import { computed, onMounted, ref } from 'vue'
import StudyCard from '@/components/workbench/StudyCard.vue'
import KnowledgeCard from '@/components/workbench/KnowledgeCard.vue'
import SocialCard from '@/components/workbench/SocialCard.vue'
import LawCard from '@/components/workbench/LawCard.vue'
import LogicCard from '@/components/workbench/LogicCard.vue'
import QuizCard from '@/components/workbench/QuizCard.vue'

const cards = [
  { key: 'study', label: '英语', comp: StudyCard },
  { key: 'knowledge', label: '知识', comp: KnowledgeCard },
  { key: 'social', label: '场景', comp: SocialCard },
  { key: 'law', label: '定律', comp: LawCard },
  { key: 'logic', label: '逻辑', comp: LogicCard },
  { key: 'quiz', label: '答题', comp: QuizCard },
]

const LAST_KEY = 'xh_deck_last'
const seenKey = () => {
  const d = new Date()
  return `xh_deck_seen_${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const cur = ref('study')
const seen = ref(new Set())

const curComp = computed(() => (cards.find(c => c.key === cur.value) || cards[0]).comp)

function readSeen() {
  try {
    const arr = JSON.parse(localStorage.getItem(seenKey()) || '[]')
    seen.value = new Set(Array.isArray(arr) ? arr : [])
  } catch { seen.value = new Set() }
}

function markSeen(key) {
  const s = new Set(seen.value)
  s.add(key)
  seen.value = s
  try { localStorage.setItem(seenKey(), JSON.stringify([...s])) } catch { /* 隐私模式 */ }
}

function pick(key) {
  cur.value = key
  markSeen(key)
  try { localStorage.setItem(LAST_KEY, key) } catch { /* 同上 */ }
}

onMounted(() => {
  readSeen()
  let start = ''
  try { start = localStorage.getItem(LAST_KEY) || '' } catch { start = '' }
  // 优先「今天还没看的」：让打开首页这个动作本身产生进度；
  // 都看过了就回到上次那张，别每次都跳回第一页
  const firstUnseen = cards.find(c => !seen.value.has(c.key))
  cur.value = (firstUnseen || cards.find(c => c.key === start) || cards[0]).key
  markSeen(cur.value)
})
</script>

<style scoped>
.dk { display: block; }

.dk-bar {
  display: flex; align-items: center; gap: 8px;
  margin: 14px 0 6px; padding: 0 1px;
}
.dk-chips {
  flex: 1; min-width: 0;
  display: flex; gap: 6px; overflow-x: auto;
  -webkit-overflow-scrolling: touch; scrollbar-width: none;
}
.dk-chips::-webkit-scrollbar { display: none; }

.dk-chip {
  flex: none;
  padding: 4px 12px; border-radius: 999px; cursor: pointer;
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .16));
  background: transparent; font: inherit; font-size: 12px; line-height: 1.6;
  color: var(--tc-text-2, #46586e);
  transition: background-color .15s, border-color .15s, color .15s;
}
/* 看过但没选中：边框实一点，暗示「这张读过了」 */
.dk-chip.seen:not(.on) {
  border-color: rgba(14, 147, 184, .38);
  color: var(--tc-cyan-deep, #0a708c);
}
.dk-chip.on {
  background: var(--tc-cyan, #0e93b8); border-color: var(--tc-cyan, #0e93b8);
  color: #fff; font-weight: 600;
}

.dk-prog {
  flex: none; font-size: 11px; font-variant-numeric: tabular-nums;
  color: var(--tc-text-3, #5b6f8a); letter-spacing: .02em;
}

.dk-card { display: block; }
</style>
