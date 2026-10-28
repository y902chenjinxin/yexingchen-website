<template>
  <teleport to="body">
    <div v-if="open" class="qw-mask" @click.self="close">
      <section class="qw-panel" role="dialog" aria-label="错题本">
        <header class="qw-head">
          <div class="qw-title">
            错题本
            <em>{{ list.length }} 条</em>
          </div>
          <div class="qw-acts">
            <button v-if="list.length" class="qw-btn ghost" @click="doClear">清空</button>
            <button class="qw-btn" @click="close">关闭</button>
          </div>
        </header>

        <div class="qw-body">
          <p v-if="!list.length" class="qw-empty">
            还没有错题。答错的题会自动收进来，隔几天回头看一遍。
          </p>

          <article v-for="it in ordered" :key="it.id" class="qw-item">
            <div class="qw-item-head">
              <span class="qw-date">{{ (it.date || '').slice(5) }}</span>
              <span v-if="it.topic" class="qw-topic">{{ it.topic }}</span>
              <button class="qw-del" title="从错题本移除" @click="del(it.id)">×</button>
            </div>

            <p class="qw-q">{{ it.q }}</p>

            <ul class="qw-opts">
              <li
                v-for="(o, i) in it.options"
                :key="i"
                class="qw-opt"
                :class="{
                  'is-ok': i === it.answer,
                  'is-bad': i === it.picked && i !== it.answer,
                }"
              >
                <span class="qw-key">{{ KEY[i] }}</span>
                <span>{{ o }}</span>
              </li>
            </ul>

            <p class="qw-why">{{ it.why }}</p>
            <p v-if="it.trick" class="qw-trick"><b>绕过这个坑</b>{{ it.trick }}</p>
          </article>
        </div>
      </section>
    </div>
  </teleport>
</template>

<script setup>
/**
 * 错题本抽屉（v2.46.273，v2.46.274 改跨设备）
 *
 * 数据来源两级：
 *   1. 打开时先读本地快照（毫秒级出内容，不空等）
 *   2. 同时请求 /api/quiz/mistakes，成功就**用服务器的替换** —— 换设备、清缓存后
 *      这里仍然是你全部的错题；接口失败（离线/未登录）就保留本地那份。
 *
 * 只读展示：题干 + 你选的（红）+ 正确答案（绿）+ 解析。
 * 不做「重做」——重做要先藏答案，而错题的价值在于**立刻看解析**，
 * 再做一遍反而多一道手续（而且选项顺序固定，第二次必然选对，学不到东西）。
 */
import { computed, ref } from 'vue'
import { workbenchApi } from '@/api/workbench'
import { readWrong, removeWrong, clearWrong } from '@/composables/useQuizWrong'

const KEY = ['A', 'B', 'C', 'D']

const emit = defineEmits(['count'])

const open = ref(false)
const list = ref([])
const syncing = ref(false)

// 新的在上：最近错的更该看
const ordered = computed(() => [...list.value].reverse())

async function show() {
  list.value = readWrong()
  open.value = true
  syncing.value = true
  try {
    const res = await workbenchApi.quiz.mistakes()
    const items = res?.data?.items
    if (Array.isArray(items)) list.value = items
  } catch { /* 接口失败：保留本地那份，不影响看题 */ }
  syncing.value = false
  emit('count', list.value.length)
}

function close() {
  open.value = false
  emit('count', list.value.length)
}

async function del(id) {
  list.value = list.value.filter(x => x.id !== id)
  removeWrong(id)
  emit('count', list.value.length)
  try { await workbenchApi.quiz.dropMistake(id) } catch { /* 本地已删，等下次同步 */ }
  if (!list.value.length) close()
}

async function doClear() {
  list.value = []
  clearWrong()
  emit('count', 0)
  try { await workbenchApi.quiz.clearMistakes() } catch { /* 同上 */ }
  close()
}

defineExpose({ show })
</script>

<style scoped>
.qw-mask {
  position: fixed; inset: 0; z-index: 2600;
  background: rgba(6, 12, 22, .46);
  display: flex; align-items: center; justify-content: center; padding: 20px;
  -webkit-backdrop-filter: blur(3px); backdrop-filter: blur(3px);
}

.qw-panel {
  width: min(560px, 100%); max-height: min(82vh, 760px);
  display: flex; flex-direction: column;
  border-radius: 18px; overflow: hidden;
  background: var(--color-bg, #fff);
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .14));
  box-shadow: 0 30px 70px -30px rgba(0, 0, 0, .5);
}

.qw-head {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 14px 18px; border-bottom: 1px solid var(--tc-line, rgba(15, 60, 110, .1));
  flex: none;
}
.qw-title { font-size: 15px; font-weight: 700; color: var(--tc-text, #0b1622); display: flex; align-items: baseline; gap: 8px; }
.qw-title em { font-style: normal; font-size: 11.5px; font-weight: 600; color: var(--tc-text-3, #5b6f8a); }
.qw-acts { display: flex; gap: 8px; }
.qw-btn {
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .16)); border-radius: 999px;
  background: transparent; cursor: pointer; padding: 4px 13px;
  font: inherit; font-size: 12px; color: var(--tc-text-2, #46586e);
}
.qw-btn:hover { border-color: var(--tc-cyan, #0e93b8); color: var(--tc-cyan-deep, #0a708c); }
.qw-btn.ghost { border-color: transparent; color: var(--tc-text-3, #5b6f8a); }

.qw-body { padding: 6px 18px 18px; overflow-y: auto; -webkit-overflow-scrolling: touch; }
.qw-empty { margin: 26px 0; text-align: center; font-size: 13px; line-height: 1.8; color: var(--tc-text-3, #5b6f8a); }

.qw-item { padding: 14px 0; border-bottom: 1px dashed var(--tc-line, rgba(15, 60, 110, .12)); }
.qw-item:last-child { border-bottom: 0; }
.qw-item-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.qw-date { font-size: 11px; color: var(--tc-text-3, #5b6f8a); font-variant-numeric: tabular-nums; }
.qw-topic {
  font-size: 10.5px; padding: 1px 7px; border-radius: 5px;
  background: rgba(15, 60, 110, .06); color: var(--tc-text-2, #46586e);
}
.qw-del {
  margin-left: auto; width: 22px; height: 22px; border: 0; border-radius: 6px;
  background: transparent; cursor: pointer; color: var(--tc-text-3, #5b6f8a); font-size: 15px; line-height: 1;
}
.qw-del:hover { background: rgba(201, 105, 74, .12); color: #b4552f; }

.qw-q { margin: 0 0 8px; font-size: 13.5px; line-height: 1.8; color: var(--tc-text, #0b1622); }

.qw-opts { list-style: none; margin: 0 0 9px; padding: 0; display: grid; gap: 5px; }
.qw-opt {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 6px 10px; border-radius: 8px;
  font-size: 12.5px; line-height: 1.65; color: var(--tc-text-2, #46586e);
  border: 1px solid transparent;
}
.qw-key {
  flex: none; width: 18px; height: 18px; border-radius: 50%;
  display: grid; place-items: center; font-size: 10.5px; font-weight: 700;
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .2)); color: var(--tc-text-3, #5b6f8a);
}
.qw-opt.is-ok { background: rgba(14, 147, 184, .09); border-color: rgba(14, 147, 184, .4); }
.qw-opt.is-ok .qw-key { background: var(--tc-cyan, #0e93b8); border-color: var(--tc-cyan, #0e93b8); color: #fff; }
.qw-opt.is-ok { font-weight: 500; }
.qw-opt.is-bad { background: rgba(201, 105, 74, .08); border-color: rgba(201, 105, 74, .4); }
.qw-opt.is-bad .qw-key { background: #c9694a; border-color: #c9694a; color: #fff; }

.qw-why {
  margin: 0; padding: 9px 12px; border-radius: 9px;
  background: rgba(15, 60, 110, .035);
  font-size: 12.5px; line-height: 1.85; color: var(--tc-text-2, #46586e); white-space: pre-wrap;
}
.qw-trick {
  margin: 7px 0 0; display: grid; grid-template-columns: 76px minmax(0, 1fr); gap: 9px;
  font-size: 12px; line-height: 1.8; color: var(--tc-text-2, #46586e);
}
.qw-trick b {
  font-size: 10.5px; font-weight: 600; color: var(--lj-seal, #a9812f);
  border-left: 2px solid var(--lj-seal, #a9812f); padding-left: 7px; line-height: 1.7;
}

@media (max-width: 560px) {
  .qw-mask { padding: 0; align-items: flex-end; }
  .qw-panel { width: 100%; max-height: 88vh; border-radius: 18px 18px 0 0; }
  .qw-body { padding: 6px 15px 22px; }
  .qw-trick { grid-template-columns: 1fr; gap: 3px; }
  .qw-trick b { border-left: 0; padding-left: 0; }
  .qw-trick b::before { content: '· '; }
}
</style>
