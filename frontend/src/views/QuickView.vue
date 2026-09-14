<template>
  <div class="qk-page">
    <div class="lj-bg" aria-hidden="true">
      <div class="lj-paper-texture"></div>
      <div class="lj-wash w1"></div>
      <div class="lj-wash w2"></div>
    </div>

    <div class="qk-inner">
      <!-- 返回 + 页头 -->
      <div class="qk-topbar">
        <BackButton />
        <span class="qk-crumb" @click="$router.push('/workbench')">工作台</span>
      </div>

      <header class="qk-head">
        <h1 class="qk-title">闪念 · 日记</h1>
        <p class="qk-sub">随手记下念头，按天汇成时间线</p>
      </header>

      <!-- 速记输入 -->
      <section class="qk-capture glass">
        <textarea
          v-model="draft"
          class="qk-capture-input"
          rows="2"
          placeholder="此刻想到什么，随手记下来…（支持语音）"
          maxlength="2000"
          @keydown.meta.enter.prevent="save"
          @keydown.ctrl.enter.prevent="save"
        ></textarea>
        <div class="qk-capture-foot">
          <VoiceInputButton @result="onVoice" class="qk-voice" />
          <span class="qk-count">{{ draft.length }} / 2000</span>
          <button class="qk-btn primary" :disabled="saving || !draft.trim()" @click="save">记下来</button>
        </div>
      </section>

      <!-- 日期快速跳转 -->
      <div class="qk-days" v-if="timeline.length">
        <button
          v-for="t in timeline"
          :key="t.day"
          class="qk-day"
          :class="{ active: t.day === t.day }"
          @click="scrollToDay(t.day)"
        >{{ dayShort(t.day) }}</button>
      </div>

      <!-- 时间线 -->
      <p v-if="loading" class="qk-loading">装载中…</p>
      <section v-else-if="timeline.length" class="qk-timeline">
        <div v-for="g in timeline" :key="g.day" class="qk-daygroup" :id="'day-' + g.day">
          <div class="qk-dayhead">
            <span class="qk-daytitle">
              <span class="qk-daynum">{{ dayNum(g.day) }}</span>
              <span class="qk-daysub">{{ g.date_label }}</span>
            </span>
            <span class="qk-daycount">{{ g.items.length }} 条</span>
          </div>
          <div class="qk-items">
            <article v-for="item in g.items" :key="item.id" class="qk-item glass">
              <div class="qk-item-time">{{ fmtTime(item.created_at) }}</div>
              <p class="qk-item-text">{{ item.content }}</p>
              <button class="qk-item-del" title="删除" @click="del(item)">🗑</button>
            </article>
          </div>
        </div>
      </section>
      <p v-else class="qk-empty">还没有记录，写点什么吧。</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import BackButton from '@/components/BackButton.vue'
import VoiceInputButton from '@/components/VoiceInputButton.vue'
import { quickApi } from '@/api/quick'

const draft = ref('')
const saving = ref(false)
const loading = ref(true)
const timeline = ref([])

function fmtTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
function dayNum(day) {
  return (day || '--').slice(-2)
}
function dayShort(day) {
  const a = (day || '').split('-')
  if (a.length < 3) return day || ''
  return `${Number(a[1])}月${Number(a[2])}日`
}
function scrollToDay(day) {
  document.getElementById('day-' + day)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function onVoice(text) {
  draft.value = draft.value.trim() ? `${draft.value.trim()}\n${text}` : text
}
async function save() {
  const text = draft.value.trim()
  if (!text) return
  saving.value = true
  try {
    await quickApi.create(text)
    draft.value = ''
    await load()
  } finally {
    saving.value = false
  }
}
async function del(item) {
  await quickApi.remove(item.id)
  await load()
}
async function load() {
  loading.value = true
  try {
    const res = await quickApi.list({ days: 14 })
    timeline.value = res.data.timeline || []
  } catch (e) {
    /* 保持空态 */
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.qk-page {
  position: relative; min-height: 100vh; padding-top: 84px; box-sizing: border-box;
  color: var(--lj-text); font-family: var(--font-serif); overflow-x: hidden;
}
.qk-inner { position: relative; z-index: 1; max-width: 760px; margin: 0 auto; padding: 0 24px 60px; }

.lj-bg { position: absolute; inset: 0; z-index: 0; pointer-events: none; overflow: hidden;
  background:
    radial-gradient(ellipse 60% 40% at 18% 6%, var(--glow-rain), transparent 60%),
    radial-gradient(ellipse 50% 40% at 85% 30%, var(--glow-gold), transparent 60%),
    var(--lj-bg); }
.lj-paper-texture { position: absolute; inset: 0; opacity: .5;
  background:
    repeating-linear-gradient(0deg, rgba(127,168,163,.02) 0 1px, transparent 1px 5px),
    repeating-linear-gradient(90deg, rgba(127,168,163,.014) 0 1px, transparent 1px 7px); }
.lj-wash { position: absolute; border-radius: 50%; filter: blur(80px); opacity: .4;
  background: radial-gradient(circle, rgba(127,168,163,.14), transparent 70%); animation: qk-drift 30s ease-in-out infinite; }
.lj-wash.w1 { width: 440px; height: 380px; top: 10%; left: -6%; }
.lj-wash.w2 { width: 400px; height: 340px; bottom: 4%; right: -5%; animation-delay: 8s; }
@keyframes qk-drift { 0%,100% { transform: translate(0,0); } 50% { transform: translate(32px,-18px); } }
@media (prefers-reduced-motion: reduce) { .lj-wash { animation: none; } }

.glass { background: var(--lj-glass); -webkit-backdrop-filter: var(--lj-glass-blur); backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line); box-shadow: var(--glass-highlight), var(--glass-shadow); }

.qk-topbar { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.qk-crumb { font-size: 13px; color: var(--lj-text-3); cursor: pointer; letter-spacing: .08em; }
.qk-crumb:hover { color: var(--lj-dai); }

.qk-head { margin-bottom: 20px; }
.qk-title { margin: 0; font-size: 30px; font-weight: 600; letter-spacing: .1em; }
.qk-sub { margin: 8px 0 0; font-size: 12.5px; color: var(--lj-text-2); letter-spacing: .16em; }

.qk-capture { border-radius: 18px; padding: 16px 18px; margin-bottom: 18px; }
.qk-capture-input { width: 100%; min-height: 52px; resize: vertical; border: none; outline: none;
  background: transparent; color: var(--lj-text); font-family: var(--font-serif); font-size: 15px; line-height: 1.6; }
.qk-capture-input::placeholder { color: var(--lj-text-3); }
.qk-capture-foot { display: flex; align-items: center; gap: 12px; margin-top: 8px; }
.qk-count { margin-left: auto; font-size: 11px; color: var(--lj-text-3); }

.qk-btn { border: none; cursor: pointer; border-radius: 10px; font-family: var(--font-serif);
  padding: 9px 18px; transition: all .22s; color: var(--lj-text); }
.qk-btn.primary { background: linear-gradient(135deg, rgba(127,168,163,.55), rgba(199,169,107,.4)); color: #fff; }
.qk-btn.primary:disabled { opacity: .5; cursor: not-allowed; }
.qk-btn.primary:not(:disabled):hover { filter: brightness(1.05); }

.qk-days { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
.qk-day { padding: 5px 12px; border-radius: 999px; border: 1px solid var(--lj-line); background: var(--lj-glass);
  color: var(--lj-text-2); font-family: var(--font-serif); font-size: 12.5px; cursor: pointer; transition: all .2s; }
.qk-day:hover { border-color: var(--lj-dai); color: var(--lj-dai); }

.qk-loading, .qk-empty { text-align: center; padding: 60px 0; color: var(--lj-text-3); letter-spacing: .2em; }

.qk-timeline { display: flex; flex-direction: column; gap: 28px; position: relative; }
.qk-timeline::before { content: ""; position: absolute; top: 6px; bottom: 6px; left: 7px; width: 2px;
  background: linear-gradient(var(--lj-dai), rgba(127,168,163,.06)); }

.qk-daygroup { position: relative; padding-left: 30px; }
.qk-dayhead { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 10px; }
.qk-daytitle { display: flex; align-items: baseline; gap: 10px; }
.qk-daynum { width: 16px; height: 16px; border-radius: 50%; background: var(--lj-dai); color: #fff;
  font-size: 10px; display: inline-flex; align-items: center; justify-content: center; position: absolute; left: 0; top: 2px; }
.qk-daysub { font-size: 14px; font-weight: 600; letter-spacing: .08em; }
.qk-daycount { font-size: 11px; color: var(--lj-text-3); }

.qk-items { display: flex; flex-direction: column; gap: 10px; }
.qk-item { position: relative; border-radius: 14px; padding: 12px 46px 12px 14px; }
.qk-item-time { font-size: 11px; color: var(--lj-text-3); margin-bottom: 4px; letter-spacing: .06em; }
.qk-item-text { margin: 0; font-size: 14px; line-height: 1.7; color: var(--lj-text);
  white-space: pre-wrap; word-break: break-word; }
.qk-item-del { position: absolute; top: 10px; right: 10px; width: 28px; height: 28px; border-radius: 8px;
  border: 1px solid transparent; background: transparent; color: var(--lj-text-3); cursor: pointer; opacity: 0; transition: all .2s; }
.qk-item:hover .qk-item-del { opacity: 1; }
.qk-item-del:hover { border-color: var(--lj-vermilion); color: var(--lj-vermilion); }

@media (max-width: 560px) { .qk-inner { padding: 0 16px 40px; } }
</style>