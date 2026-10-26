<template>
  <section v-if="data" class="kn glass-card" aria-label="每日知识">
    <header class="kn-head">
      <div class="kn-title">
        <span class="kn-tag">知识</span>
        每日知识
        <em class="kn-meta">{{ data.field }} · 第 {{ data.position }}/{{ data.total }} 条</em>
      </div>
      <div class="kn-nav">
        <button class="kn-nav-btn" title="看昨天" @click="go(-1)">‹</button>
        <span class="kn-date">{{ data.date.slice(5) }}</span>
        <button class="kn-nav-btn" title="看明天" @click="go(1)">›</button>
      </div>
    </header>

    <div class="kn-hd">
      <h2 class="kn-concept">{{ data.concept }}</h2>
      <span class="kn-en">{{ data.concept_en }}</span>
      <button class="kn-fold" @click="open = !open">{{ open ? '收起' : '展开' }}</button>
    </div>
    <p class="kn-one">{{ data.one_line }}</p>

    <div v-if="open" class="kn-body">
      <p class="kn-fable">{{ data.fable }}</p>

      <div class="kn-note kn-note--insight">
        <b>所以呢</b>
        <p>{{ data.insight }}</p>
      </div>

      <div class="kn-note kn-note--apply">
        <b>怎么用</b>
        <p>{{ data.apply }}</p>
      </div>

      <p class="kn-q">{{ data.question }}</p>
    </div>
    <p v-else class="kn-hint">点「展开」读这个小故事 —— 记住故事比记住名词有用。</p>
  </section>
</template>

<script setup>
/**
 * 工作台「每日知识」卡片（v2.46.248）
 *
 * 夜星：「每天在里面找一个知识点，用通俗易懂的话编一个寓言故事，能让我快速理解的，
 *        主要就是想形成被动学习的效果。」
 *
 * 所以主体是**故事**，不是名词解释。默认展开 —— 折叠起来就失去意义了；
 * 但他想安静的时候可以收起，收起后只剩一句话，不占视线。
 */
import { onMounted, ref } from 'vue'
import { workbenchApi } from '@/api/workbench'

const data = ref(null)
const open = ref(true)
const offset = ref(0)

async function load(off = 0) {
  try {
    const res = await workbenchApi.knowledge.today(off)
    data.value = res?.data || res || null
    offset.value = off
  } catch { /* 静默失败，不影响工作台其它模块 */ }
}

function go(delta) {
  load(offset.value + delta)
}

onMounted(() => load(0))
</script>

<style scoped>
.kn { padding: 16px 20px 18px; }

.kn-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 10px; }
.kn-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; letter-spacing: .02em; color: var(--tc-text, #0b1622); }
.kn-tag {
  font-size: 10.5px; font-weight: 600; letter-spacing: .08em; padding: 2px 7px; border-radius: 6px;
  background: rgba(14, 147, 184, .12); color: var(--tc-cyan-deep, #0a708c);
}
.kn-meta { font-style: normal; font-size: 11.5px; font-weight: 600; color: var(--tc-text-3, #5b6f8a); }
.kn-nav { display: flex; align-items: center; gap: 2px; }
.kn-nav-btn {
  width: 22px; height: 22px; border: 0; background: transparent; cursor: pointer;
  color: var(--tc-text-3, #5b6f8a); font-size: 15px; line-height: 1; border-radius: 6px;
}
.kn-nav-btn:hover { background: rgba(14, 147, 184, .1); color: var(--tc-cyan, #0e93b8); }
.kn-date { font-size: 11px; color: var(--tc-text-3, #5b6f8a); font-variant-numeric: tabular-nums; min-width: 38px; text-align: center; }

.kn-hd { display: flex; align-items: baseline; gap: 9px; flex-wrap: wrap; }
.kn-concept { margin: 0; font-size: 20px; letter-spacing: -.01em; color: var(--tc-text, #0b1622); }
.kn-en { font-size: 11.5px; color: var(--tc-text-3, #5b6f8a); letter-spacing: .02em; }
.kn-fold {
  margin-left: auto; border: 0; background: transparent; cursor: pointer; padding: 2px 4px;
  font: inherit; font-size: 11.5px; color: var(--tc-cyan, #0e93b8);
}
.kn-one {
  margin: 6px 0 0; font-size: 13.5px; line-height: 1.7;
  color: var(--lj-seal, #a9812f); font-weight: 600;
}

.kn-body { margin-top: 12px; }
.kn-fable {
  margin: 0 0 12px; font-size: 13.5px; line-height: 1.95;
  color: var(--tc-text-2, #46586e); white-space: pre-wrap;
}

.kn-note { display: grid; grid-template-columns: 46px minmax(0, 1fr); gap: 10px; padding: 10px 0 10px 0; }
.kn-note + .kn-note { border-top: 1px dashed var(--tc-line, rgba(15, 60, 110, .1)); }
.kn-note b {
  font-size: 11px; font-weight: 600; letter-spacing: .06em; color: var(--tc-cyan-deep, #0a708c);
  border-left: 2px solid var(--tc-cyan, #0e93b8); padding-left: 8px; line-height: 1.6;
}
.kn-note p { margin: 0; font-size: 12.5px; line-height: 1.85; color: var(--tc-text-2, #46586e); }
.kn-note--apply b { color: var(--lj-seal, #a9812f); border-left-color: var(--lj-seal, #a9812f); }

.kn-q {
  margin: 10px 0 0; padding-top: 10px; font-size: 12.5px; line-height: 1.7;
  border-top: 1px dashed var(--tc-line, rgba(15, 60, 110, .1));
  color: var(--tc-text-3, #5b6f8a); font-style: italic;
}
.kn-q::before { content: '？'; margin-right: 6px; font-style: normal; opacity: .6; }
.kn-hint { margin: 8px 0 0; font-size: 11.5px; color: var(--tc-text-3, #5b6f8a); }
</style>
