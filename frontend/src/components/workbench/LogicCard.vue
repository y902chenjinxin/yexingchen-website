<template>
  <section v-if="data" class="lz glass-card" aria-label="每日思维逻辑">
    <header class="lz-head">
      <div class="lz-title">
        <span class="lz-tag">逻辑</span>
        每日思维逻辑
        <em class="lz-meta">{{ data.cat }} · 第 {{ data.cat_position }}/{{ data.cat_total }} 条</em>
      </div>
      <div class="lz-nav">
        <button class="lz-nav-btn" title="看昨天" @click="go(-1)">‹</button>
        <span class="lz-date">{{ (data.date || '').slice(5) }}</span>
        <button class="lz-nav-btn" title="看明天" @click="go(1)">›</button>
        <FoldBtn :open="open" open-text="看怎么拆" close-text="收起" @toggle="open = !open" />
      </div>
    </header>

    <div class="lz-hd">
      <h3 class="lz-name">{{ data.name }}</h3>
      <span v-if="data.name_en" class="lz-en">{{ data.name_en }}</span>
    </div>
    <p class="lz-one">{{ data.one_line }}</p>

    <div v-if="open" class="lz-body">
      <div class="lz-note">
        <b>它怎么运作</b>
        <p>{{ data.shape }}</p>
      </div>

      <div class="lz-note lz-note--eg">
        <b>举个例子</b>
        <p>{{ data.example }}</p>
      </div>

      <div class="lz-note lz-note--how">
        <b>怎么拆</b>
        <p>{{ data.howto }}</p>
      </div>

      <div class="lz-note lz-note--caveat">
        <b>别过头</b>
        <p>{{ data.caveat }}</p>
      </div>

      <p class="lz-foot">
        共 {{ data.total }} 条 · 每天一条，轮完一遍约 {{ Math.round(data.total / 30) }} 个月
      </p>
    </div>
  </section>
</template>

<script setup>
/**
 * 工作台「每日思维逻辑」卡（v2.46.269）
 *
 * 夜星：
 * > 长脑子最快的就是学习思维逻辑，将 github 上所有关于思维逻辑的内容都以卡片的形式每天提供。
 *
 * 和「今日定律」的分工：
 *   定律卡 —— 有名有姓的效应，解释**世界怎么运转**
 *   这张卡 —— 专门练**怎么想**：谬误（别人怎么糊弄你）、偏差（你自己先歪在哪）、
 *             模型（换个角度看系统）、方法（怎么把话说实）
 *
 * 数据 127 条来自 GitHub 公开清单（logic / mind-models / cognitive-bias 三类仓库）
 * 交叉整理，按四类轮转交错，所以连续几天不重样。
 *
 * 默认收起（只露名字 + 一句话），展开才看四段：机制 → 例子 → 拆法 → 别过头。
 */
import { onMounted, ref } from 'vue'
import { workbenchApi } from '@/api/workbench'
import FoldBtn from '@/components/workbench/FoldBtn.vue'

const data = ref(null)
const open = ref(false)
const offset = ref(0)

async function load(off = 0) {
  try {
    const res = await workbenchApi.logic.today(off)
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
.lz { padding: 16px 20px; }

.lz-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 8px; flex-wrap: wrap; }
.lz-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; letter-spacing: .02em; color: var(--tc-text, #0b1622); }
.lz-tag {
  font-size: 10.5px; font-weight: 600; letter-spacing: .08em; padding: 2px 7px; border-radius: 6px;
  background: rgba(24, 24, 27, .08); color: var(--tc-text-2, #46586e);
}
.lz-meta { font-style: normal; font-size: 11.5px; font-weight: 600; color: var(--tc-text-3, #5b6f8a); }
.lz-nav { display: flex; align-items: center; gap: 4px; }
.lz-nav-btn {
  width: 22px; height: 22px; border: 0; background: transparent; cursor: pointer;
  color: var(--tc-text-3, #5b6f8a); font-size: 15px; line-height: 1; border-radius: 6px;
}
.lz-nav-btn:hover { background: rgba(14, 147, 184, .1); color: var(--tc-cyan, #0e93b8); }
.lz-date { font-size: 11px; color: var(--tc-text-3, #5b6f8a); font-variant-numeric: tabular-nums; min-width: 38px; text-align: center; }

.lz-hd { display: flex; align-items: baseline; gap: 9px; flex-wrap: wrap; }
.lz-name { margin: 0; font-size: 19px; line-height: 1.4; letter-spacing: -.01em; color: var(--tc-text, #0b1622); }
.lz-en { font-size: 11px; color: var(--tc-text-3, #5b6f8a); letter-spacing: .01em; }
.lz-one { margin: 6px 0 0; font-size: 13.5px; line-height: 1.75; color: var(--tc-text-2, #46586e); font-weight: 500; }

.lz-body { margin-top: 12px; }

.lz-note { display: grid; grid-template-columns: 62px minmax(0, 1fr); gap: 10px; padding: 9px 0; }
.lz-note + .lz-note { border-top: 1px dashed var(--tc-line, rgba(15, 60, 110, .1)); }
.lz-note b {
  font-size: 11px; font-weight: 600; letter-spacing: .04em; color: var(--tc-cyan-deep, #0a708c);
  border-left: 2px solid var(--tc-cyan, #0e93b8); padding-left: 8px; line-height: 1.7;
}
.lz-note p { margin: 0; font-size: 12.5px; line-height: 1.85; color: var(--tc-text-2, #46586e); }

/* 例子给一点底色，跟两段分析分开：读的时候是先看故事再看道理 */
.lz-note--eg p {
  padding: 9px 12px; border-radius: 9px;
  background: rgba(15, 60, 110, .035);
  color: var(--tc-text-2, #46586e);
}
.lz-note--how b { color: var(--lj-seal, #a9812f); border-left-color: var(--lj-seal, #a9812f); }
.lz-note--caveat b { color: #b4552f; border-left-color: #c9694a; }

.lz-foot {
  margin: 10px 0 0; padding-top: 9px;
  border-top: 1px solid var(--tc-line, rgba(15, 60, 110, .08));
  font-size: 11px; color: var(--tc-text-3, #5b6f8a); letter-spacing: .02em;
}

@media (max-width: 520px) {
  .lz { padding: 14px 15px; }
  .lz-name { font-size: 17.5px; }
  .lz-one { font-size: 13px; }
  .lz-note { grid-template-columns: 1fr; gap: 4px; }
  .lz-note b { border-left: 0; padding-left: 0; }
  .lz-note b::before { content: '· '; }
}
</style>
