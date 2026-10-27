<template>
  <section v-if="data" class="lw glass-card" aria-label="今日定律">
    <header class="lw-head">
      <div class="lw-title">
        <span class="lw-tag">杂学</span>
        今日定律
        <em class="lw-meta">{{ data.domain }} · 第 {{ data.position }}/{{ data.total }} 条</em>
      </div>
      <div class="lw-nav">
        <button class="lw-nav-btn" title="看昨天" @click="go(-1)">‹</button>
        <span class="lw-date">{{ data.date.slice(5) }}</span>
        <button class="lw-nav-btn" title="看明天" @click="go(1)">›</button>
        <FoldBtn :open="open" open-text="展开" @toggle="open = !open" />
      </div>
    </header>

    <div class="lw-hd">
      <h3 class="lw-name">{{ data.name }}</h3>
      <span v-if="data.name_en" class="lw-en">{{ data.name_en }}</span>
      <span v-if="data.who" class="lw-who">{{ data.who }}</span>
    </div>
    <p class="lw-one">{{ data.one_line }}</p>

    <div v-if="open" class="lw-body">
      <p class="lw-explain">{{ data.explain }}</p>

      <div class="lw-note">
        <b>长什么样</b>
        <p>{{ data.reality }}</p>
      </div>

      <div class="lw-note lw-note--use">
        <b>怎么用</b>
        <p>{{ data.use }}</p>
      </div>

      <div class="lw-note lw-note--caveat">
        <b>别过头</b>
        <p>{{ data.caveat }}</p>
      </div>
    </div>
  </section>
</template>

<script setup>
/**
 * 工作台「今日定律」卡（v2.46.255）
 *
 * 夜星喜欢看「瞎猫理论 / 好运设计」这类东西 —— 读完会点头、能拿去解释自己生活的说法。
 *
 * 默认收起（工作台已经有英语/知识/场景三张长卡了），只露名字 + 一句话。
 * 想细看再展开：讲清来历 → 生活里的样子 → 怎么用 → 什么时候别过头。
 */
import { onMounted, ref } from 'vue'
import { workbenchApi } from '@/api/workbench'
import FoldBtn from '@/components/workbench/FoldBtn.vue'

const data = ref(null)
const open = ref(false)
const offset = ref(0)

async function load(off = 0) {
  try {
    const res = await workbenchApi.laws.today(off)
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
.lw { padding: 16px 20px 16px; }

.lw-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 8px; flex-wrap: wrap; }
.lw-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; letter-spacing: .02em; color: var(--tc-text, #0b1622); }
.lw-tag {
  font-size: 10.5px; font-weight: 600; letter-spacing: .08em; padding: 2px 7px; border-radius: 6px;
  background: rgba(24, 24, 27, .08); color: var(--tc-text-2, #46586e);
}
.lw-meta { font-style: normal; font-size: 11.5px; font-weight: 600; color: var(--tc-text-3, #5b6f8a); }
.lw-nav { display: flex; align-items: center; gap: 4px; }
.lw-nav-btn {
  width: 22px; height: 22px; border: 0; background: transparent; cursor: pointer;
  color: var(--tc-text-3, #5b6f8a); font-size: 15px; line-height: 1; border-radius: 6px;
}
.lw-nav-btn:hover { background: rgba(14, 147, 184, .1); color: var(--tc-cyan, #0e93b8); }
.lw-date { font-size: 11px; color: var(--tc-text-3, #5b6f8a); font-variant-numeric: tabular-nums; min-width: 38px; text-align: center; }

.lw-hd { display: flex; align-items: baseline; gap: 9px; flex-wrap: wrap; }
.lw-name { margin: 0; font-size: 19px; line-height: 1.4; letter-spacing: -.01em; color: var(--tc-text, #0b1622); }
.lw-en { font-size: 11px; color: var(--tc-text-3, #5b6f8a); letter-spacing: .01em; }
.lw-who {
  font-size: 10.5px; padding: 1px 6px; border-radius: 4px;
  background: rgba(15, 60, 110, .05); color: var(--tc-text-3, #5b6f8a);
}
.lw-one { margin: 6px 0 0; font-size: 13.5px; line-height: 1.75; color: var(--tc-text-2, #46586e); font-weight: 500; }

.lw-body { margin-top: 12px; }
.lw-explain {
  margin: 0 0 12px; padding: 11px 13px; border-radius: 10px;
  background: rgba(15, 60, 110, .035);
  font-size: 13.5px; line-height: 1.95; color: var(--tc-text-2, #46586e); white-space: pre-wrap;
}

.lw-note { display: grid; grid-template-columns: 58px minmax(0, 1fr); gap: 10px; padding: 9px 0; }
.lw-note + .lw-note { border-top: 1px dashed var(--tc-line, rgba(15, 60, 110, .1)); }
.lw-note b {
  font-size: 11px; font-weight: 600; letter-spacing: .04em; color: var(--tc-cyan-deep, #0a708c);
  border-left: 2px solid var(--tc-cyan, #0e93b8); padding-left: 8px; line-height: 1.7;
}
.lw-note p { margin: 0; font-size: 12.5px; line-height: 1.85; color: var(--tc-text-2, #46586e); }
.lw-note--use b { color: var(--lj-seal, #a9812f); border-left-color: var(--lj-seal, #a9812f); }
.lw-note--caveat b { color: #b4552f; border-left-color: #c9694a; }
</style>
