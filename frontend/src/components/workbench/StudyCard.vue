<template>
  <section v-if="data" class="sc glass-card" aria-label="每日英语">
    <header class="sc-head">
      <div class="sc-title">
        <span class="sc-tag">学习</span>
        每日英语
        <em class="sc-day">第 {{ data.day_no }} 天</em>
      </div>
      <div class="sc-nav">
        <button class="sc-nav-btn" title="看昨天" @click="go(-1)">‹</button>
        <span class="sc-date">{{ data.date.slice(5) }}</span>
        <button class="sc-nav-btn" title="看明天" @click="go(1)">›</button>
      </div>
    </header>

    <div class="sc-body">
      <!-- 左：单词本体 -->
      <div class="sc-left">
        <div class="sc-wordline">
          <h2 class="sc-word">{{ data.w }}</h2>
          <span class="sc-ipa">{{ data.ipa }}</span>
          <span class="sc-pos">{{ data.pos }}</span>
        </div>
        <p class="sc-zh">{{ data.zh }}</p>

        <div class="sc-block">
          <div class="sc-lbl">{{ data.forms_label }}</div>
          <div class="sc-chips">
            <span v-for="f in data.forms" :key="f[0]" class="sc-chip">
              <i>{{ f[0] }}</i>{{ f[1] }}
            </span>
          </div>
        </div>

        <div class="sc-block">
          <div class="sc-lbl">组词 / 搭配</div>
          <ul class="sc-coll">
            <li v-for="c in data.collocations" :key="c[0]">
              <b>{{ c[0] }}</b>
              <em>{{ c[1] }}</em>
            </li>
          </ul>
        </div>
      </div>

      <!-- 右：长句（>50 词，默认收起，不占视线） -->
      <div class="sc-right">
        <button class="sc-sent-toggle" :class="{ open }" @click="open = !open">
          <span class="sc-sent-title">
            {{ open ? '长句' : `读一个长句` }}
            <em>{{ data.word_count }} 词</em>
          </span>
          <span class="sc-sent-arrow">{{ open ? '收起' : '展开' }}</span>
        </button>
        <div v-if="open" class="sc-sent">
          <p class="sc-en">{{ data.sentence }}</p>
          <p class="sc-cn">{{ data.sentence_zh }}</p>
        </div>
        <p v-else class="sc-hint">
          每天读一个长句，不查词也能猜大意 —— 学语言靠的是见面次数，不是背的次数。
        </p>
      </div>
    </div>
  </section>
</template>

<script setup>
/**
 * 工作台「每日英语」卡片（v2.46.245）
 *
 * 夜星要「被动学习」：打开工作台就顺手看一眼，不用专门去学。
 * 内容全部来自后端内置词库（30 条按日期轮换），不调外部模型 ——
 * 每天都要出现的东西，稳定比「新鲜」重要，断网也能用。
 *
 * 长句默认收起：>50 词的英文段子铺在首页会喧宾夺主，展开才看。
 */
import { onMounted, ref } from 'vue'
import { workbenchApi } from '@/api/workbench'

const data = ref(null)
const open = ref(false)
const offset = ref(0)

async function load(off = 0) {
  try {
    const res = await workbenchApi.study.today(off)
    data.value = res?.data || res || null
    offset.value = off
    open.value = false
  } catch { /* 卡片静默失败，不影响工作台其它模块 */ }
}

function go(delta) {
  load(offset.value + delta)
}

onMounted(() => load(0))
</script>

<style scoped>
.sc { padding: 16px 20px 18px; }
.sc-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 12px; }
.sc-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; letter-spacing: .02em; color: var(--tc-text, #0b1622); }
.sc-tag {
  font-size: 10.5px; font-weight: 600; letter-spacing: .08em; padding: 2px 7px; border-radius: 6px;
  background: var(--tc-seal-soft, rgba(199, 169, 107, .18)); color: var(--lj-seal, #a9812f);
}
.sc-day { font-style: normal; font-size: 11.5px; font-weight: 600; color: var(--tc-text-3, #5b6f8a); }
.sc-nav { display: flex; align-items: center; gap: 2px; }
.sc-nav-btn {
  width: 22px; height: 22px; border: 0; background: transparent; cursor: pointer;
  color: var(--tc-text-3, #5b6f8a); font-size: 15px; line-height: 1; border-radius: 6px;
}
.sc-nav-btn:hover { background: rgba(14, 147, 184, .1); color: var(--tc-cyan, #0e93b8); }
.sc-date { font-size: 11px; color: var(--tc-text-3, #5b6f8a); font-variant-numeric: tabular-nums; min-width: 38px; text-align: center; }

.sc-body { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr); gap: 22px; }
@media (max-width: 860px) { .sc-body { grid-template-columns: 1fr; gap: 14px; } }

.sc-wordline { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.sc-word { margin: 0; font-size: 26px; letter-spacing: -.01em; color: var(--tc-text, #0b1622); }
.sc-ipa { font-size: 12.5px; color: var(--tc-text-3, #5b6f8a); }
.sc-pos { font-size: 11.5px; padding: 1px 6px; border-radius: 5px; background: rgba(14, 147, 184, .1); color: var(--tc-cyan, #0e93b8); }
.sc-zh { margin: 4px 0 12px; font-size: 13.5px; color: var(--tc-text-2, #46586e); }

.sc-block { margin-bottom: 10px; }
.sc-lbl { font-size: 11px; letter-spacing: .1em; color: var(--tc-text-3, #5b6f8a); margin-bottom: 5px; }
.sc-chips { display: flex; flex-wrap: wrap; gap: 5px; }
.sc-chip {
  font-size: 12px; padding: 3px 8px; border-radius: 7px;
  background: rgba(15, 60, 110, .05); color: var(--tc-text, #0b1622);
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .1));
}
.sc-chip i { font-style: normal; color: var(--tc-text-3, #5b6f8a); margin-right: 5px; font-size: 10.5px; }
.sc-coll { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.sc-coll li { display: flex; align-items: baseline; gap: 8px; font-size: 12.5px; }
.sc-coll b { color: var(--tc-text, #0b1622); font-weight: 600; }
.sc-coll em { font-style: normal; color: var(--tc-text-3, #5b6f8a); font-size: 11.5px; }

.sc-sent-toggle {
  width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 8px 12px; border-radius: 10px; cursor: pointer; font: inherit;
  border: 1px dashed var(--tc-line-strong, rgba(15, 60, 110, .26)); background: transparent;
  color: var(--tc-text-2, #46586e); transition: border-color .15s, background-color .15s;
}
.sc-sent-toggle:hover { border-color: var(--tc-cyan, #0e93b8); background: rgba(14, 147, 184, .05); }
.sc-sent-toggle.open { border-style: solid; }
.sc-sent-title { font-size: 12.5px; font-weight: 600; color: var(--tc-text, #0b1622); }
.sc-sent-title em { font-style: normal; font-weight: 400; font-size: 11px; color: var(--tc-text-3, #5b6f8a); margin-left: 6px; }
.sc-sent-arrow { font-size: 11.5px; color: var(--tc-cyan, #0e93b8); }
.sc-sent { margin-top: 10px; }
.sc-en {
  margin: 0 0 8px; font-size: 13.5px; line-height: 1.85; color: var(--tc-text, #0b1622);
  letter-spacing: .01em;
}
.sc-cn { margin: 0; font-size: 12.5px; line-height: 1.8; color: var(--tc-text-3, #5b6f8a); }
.sc-hint { margin: 8px 2px 0; font-size: 11.5px; line-height: 1.7; color: var(--tc-text-3, #5b6f8a); }
</style>
