<template>
  <section v-if="data" class="so glass-card" aria-label="每日人情场景">
    <header class="so-head">
      <div class="so-title">
        <span class="so-tag">处世</span>
        每日场景
        <em class="so-domain">{{ data.domain }}</em>
      </div>
      <div class="so-nav">
        <button class="so-nav-btn" title="看昨天" @click.stop="go(-1)">‹</button>
        <span class="so-date">{{ data.date.slice(5) }}</span>
        <button class="so-nav-btn" title="看明天" @click.stop="go(1)">›</button>
      </div>
    </header>

    <!-- 整卡可点：收起时只有「场景 + 难在哪」，点开才展开全部。
         夜星要「点击卡片展开查看这个场景，当小故事看的」—— 所以是整卡 hit area，
         不是那个小小的「展开」两个字。 -->
    <div
      class="so-open"
      role="button"
      tabindex="0"
      :aria-expanded="open"
      @click="open = !open"
      @keydown.enter.prevent="open = !open"
      @keydown.space.prevent="open = !open"
    >
      <h3 class="so-scene">{{ data.scene }}</h3>
      <p class="so-hook">{{ data.hook }}</p>
      <span class="so-fold">{{ open ? '收起' : '展开看怎么办' }}</span>
    </div>

    <div v-if="open" class="so-body">
      <p class="so-story">{{ data.story }}</p>

      <div class="so-note">
        <b>判断关键</b>
        <p>{{ data.judge }}</p>
      </div>

      <div class="so-note">
        <b>怎么做</b>
        <p>{{ data.do }}</p>
      </div>

      <div class="so-say">
        <div class="so-say-head">
          <b>可以怎么说</b>
          <button class="so-copy" @click.stop="copy">{{ copied ? '已复制' : '复制' }}</button>
        </div>
        <p>{{ data.say }}</p>
      </div>

      <div class="so-note so-note--cost">
        <b>代价</b>
        <p>{{ data.cost }}</p>
      </div>

      <div class="so-note so-note--trap">
        <b>别这么做</b>
        <p>{{ data.trap }}</p>
      </div>
    </div>

    <p class="so-src">
      内容为原创 · 参考《人情世故指南》
      <a href="https://kkk-bot.github.io/HowToGetAlong/" target="_blank" rel="noopener">HowToGetAlong</a>
      （10 章 77 条，个人非商业许可，本站未收录其正文）
    </p>
  </section>
</template>

<script setup>
/**
 * 工作台「每日场景」卡片（v2.46.249）
 *
 * 一处内容来源的说明：最有名的《人情世故指南》HowToGetAlong 是自定义许可，
 * 禁止未经授权收录正文，所以这里是用 AI 自写的同结构内容（详见后端 social.py 顶部注释）。
 */
import { onMounted, ref } from 'vue'
import { workbenchApi } from '@/api/workbench'

const data = ref(null)
const open = ref(false)
const copied = ref(false)
const offset = ref(0)

async function load(off = 0) {
  try {
    const res = await workbenchApi.social.today(off)
    data.value = res?.data || res || null
    offset.value = off
    open.value = false
  } catch { /* 静默失败 */ }
}

function go(delta) {
  load(offset.value + delta)
}

async function copy() {
  try {
    await navigator.clipboard.writeText(data.value.say)
    copied.value = true
    setTimeout(() => { copied.value = false }, 1600)
  } catch {
    copied.value = false
  }
}

onMounted(() => load(0))
</script>

<style scoped>
.so { padding: 16px 20px 14px; }

.so-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 8px; }
.so-title { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 700; letter-spacing: .02em; color: var(--tc-text, #0b1622); }
.so-tag {
  font-size: 10.5px; font-weight: 600; letter-spacing: .08em; padding: 2px 7px; border-radius: 6px;
  background: rgba(169, 129, 47, .14); color: var(--lj-seal, #a9812f);
}
.so-domain { font-style: normal; font-size: 11.5px; font-weight: 600; color: var(--tc-text-3, #5b6f8a); }
.so-nav { display: flex; align-items: center; gap: 2px; }
.so-nav-btn {
  width: 22px; height: 22px; border: 0; background: transparent; cursor: pointer;
  color: var(--tc-text-3, #5b6f8a); font-size: 15px; line-height: 1; border-radius: 6px;
}
.so-nav-btn:hover { background: rgba(14, 147, 184, .1); color: var(--tc-cyan, #0e93b8); }
.so-date { font-size: 11px; color: var(--tc-text-3, #5b6f8a); font-variant-numeric: tabular-nums; min-width: 38px; text-align: center; }

/* 整卡点击区 */
.so-open {
  display: block; width: 100%; text-align: left; cursor: pointer; font: inherit;
  border: 0; background: transparent; padding: 2px 0 4px; color: inherit;
}
.so-scene { margin: 0; font-size: 17px; line-height: 1.5; letter-spacing: -.01em; color: var(--tc-text, #0b1622); }
.so-open:hover .so-scene { color: var(--tc-cyan-deep, #0a708c); }
.so-hook { margin: 5px 0 0; font-size: 13px; line-height: 1.7; color: var(--tc-text-2, #46586e); }
.so-fold { display: inline-block; margin-top: 6px; font-size: 11.5px; color: var(--tc-cyan, #0e93b8); }

.so-body { margin-top: 10px; }
.so-story {
  margin: 0 0 12px; padding: 11px 13px; border-radius: 10px;
  background: rgba(15, 60, 110, .04);
  font-size: 13.5px; line-height: 1.95; color: var(--tc-text-2, #46586e); white-space: pre-wrap;
}

.so-note { display: grid; grid-template-columns: 60px minmax(0, 1fr); gap: 10px; padding: 9px 0; }
.so-note + .so-note { border-top: 1px dashed var(--tc-line, rgba(15, 60, 110, .1)); }
.so-note b {
  font-size: 11px; font-weight: 600; letter-spacing: .04em; color: var(--tc-cyan-deep, #0a708c);
  border-left: 2px solid var(--tc-cyan, #0e93b8); padding-left: 8px; line-height: 1.7;
}
.so-note p { margin: 0; font-size: 12.5px; line-height: 1.85; color: var(--tc-text-2, #46586e); }
.so-note--cost b { color: var(--tc-text-3, #5b6f8a); border-left-color: var(--tc-line-strong, rgba(15,60,110,.26)); }
.so-note--trap b { color: #b4552f; border-left-color: #c9694a; }

/* 台词是这张卡最该被复制走的东西 */
.so-say {
  margin: 10px 0; padding: 10px 13px; border-radius: 10px;
  background: var(--tc-seal-soft, rgba(199, 169, 107, .12));
  border-left: 2px solid var(--lj-seal, #a9812f);
}
.so-say-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 4px; }
.so-say-head b { font-size: 11px; font-weight: 600; letter-spacing: .06em; color: var(--lj-seal, #a9812f); }
.so-copy {
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .14)); background: transparent;
  border-radius: 6px; padding: 1px 8px; font: inherit; font-size: 10.5px; cursor: pointer;
  color: var(--tc-text-3, #5b6f8a);
}
.so-copy:hover { border-color: var(--lj-seal, #a9812f); color: var(--lj-seal, #a9812f); }
.so-say p { margin: 0; font-size: 13px; line-height: 1.9; color: var(--tc-text, #0b1622); }

.so-src { margin: 10px 0 0; font-size: 10.5px; line-height: 1.6; color: var(--tc-text-3, #5b6f8a); }
.so-src a { color: var(--tc-text-3, #5b6f8a); text-decoration: underline; text-underline-offset: 2px; }
.so-src a:hover { color: var(--tc-cyan, #0e93b8); }
</style>
