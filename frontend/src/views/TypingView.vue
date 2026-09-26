<template>
  <IslandInnerBase type="tool" title="打字测速" subtitle="60 秒 · 中英双模式 · 本地记录">
    <div class="ty-tool">
      <div class="ty-tabs">
        <button class="ty-tab" :class="{ active: mode === 'en' }" @click="setMode('en')">英文</button>
        <button class="ty-tab" :class="{ active: mode === 'zh' }" @click="setMode('zh')">中文句子</button>
      </div>

      <div class="ty-stats">
        <div class="ty-stat"><b>{{ stats.wpm }}</b><span>{{ mode === 'en' ? 'WPM' : '字/分' }}</span></div>
        <div class="ty-stat"><b>{{ stats.acc }}%</b><span>正确率</span></div>
        <div class="ty-stat"><b>{{ stats.left }}</b><span>剩余秒</span></div>
      </div>

      <div v-if="!running && !finished" class="ty-ready">
        <button class="ty-btn primary" @click="start">开始 60 秒挑战</button>
        <div class="ty-hint">点击开始后输入框自动聚焦，打完自动换下一句/词</div>
      </div>

      <div v-if="running || finished" class="ty-board glass-card">
        <div class="ty-target">
          <span
            v-for="(ch, i) in targetChars"
            :key="i"
            class="ty-ch"
            :class="{ done: i < typedLen, wrong: i < typedLen && wrongAt(i) }"
          >{{ ch }}</span>
        </div>
        <input
          ref="inputEl"
          v-model="typed"
          class="ty-input"
          :disabled="!running"
          autocomplete="off"
          autocapitalize="off"
          spellcheck="false"
          @input="onType"
        >
      </div>

      <div v-if="finished" class="ty-result glass-card">
        {{ mode === 'en' ? 'WPM' : '字/分' }} <b>{{ stats.wpm }}</b> · 正确率 <b>{{ stats.acc }}%</b> · 共 {{ stats.chars }} 字符
        <button class="ty-btn primary" @click="start">再来一次</button>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, reactive, computed, onBeforeUnmount, nextTick } from 'vue'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'

const EN_WORDS = ('the be to of and a in that have i it for not on with he as you do at this but his by from they we say her she or an will my one all would there their what so up out if about who get which go me when make can like time no just him know take people into year your good some could them see other than then now look only come its over think also back after use two how our work first well way even new want because any these give day most us is are was were been has had did said each tell does set three still small large point end read need land home hand large must big high such follow act why ask men change went light kind off need house picture try us again animal mother world near build self earth father head stand own page should country found answer school grow study still learn plant cover food sun four state keep eye never last let thought city tree cross farm hard start might story saw far sea draw left late run press close night real life few north open seem together next white children begin got walk example ease paper often always music those both mark book letter until mile river car feet care second group carry took rain eat room friend began idea fish mountain stop once base hear horse cut sure watch color face wood main enough plain girl usual young ready above ever red list though feel talk bird soon body dog family direct leave song measure door product black short numeral class wind question happen complete ship area half rock order fire south problem piece told knew pass since top whole king space heard best hour better true during hundred five remember step early hold west ground interest reach fast verb sing listen table travel less morning ten simple several vowel toward war lay against pattern slow center love person money serve appear road map science rule govern pull cold notice voice fall power town fine certain fly unit lead cry dark machine note wait plan figure star box noun field rest correct able pound done beauty drive stood contain front teach week final gave green oh quick develop sleep warm free minute strong special mind behind clear tail produce fact street inch lot nothing course stay wheel full force blue object decide surface deep moon island foot yet busy test record boat common gold possible plane age dry wonder laugh thousand ago ran check game shape yes hot miss brought heat snow bed bring sit perhaps fill east weight language among').split(' ')
const ZH_SENTS = [
  '玄黄是我的个人网站，记录生活也记录工作。',
  '键盘敲击的声音，是程序员的雨声。',
  '把复杂的事情做简单，把简单的事情做到极致。',
  '时间不语，却回答了所有问题。',
  '山高路远，看世界，也找自己。',
  '代码写完只是开始，跑通才是结束。',
  '生活嘛，开心最重要，其他都是锦上添花。',
  '少刷手机，多敲键盘，多用脑子。',
  '夜色再深，也挡不住想回家的路。',
  '把每一个平凡的日子，过成值得记住的样子。',
  '慢慢来，比较快。',
  '种一棵树最好的时间是十年前，其次是现在。',
]

const mode = ref('en')
const running = ref(false)
const finished = ref(false)
const typed = ref('')
const target = ref('')
const inputEl = ref(null)
const stats = reactive({ wpm: 0, acc: 0, left: 60, chars: 0 })

let timerId = 0
let deadline = 0
let totalTyped = 0, correctTyped = 0, piecesDone = 0

const targetChars = computed(() => target.value.split(''))
const typedLen = computed(() => typed.value.length)
function wrongAt(i) {
  // 中文整句逐字比对；英文按已输入串比对
  return typed.value[i] !== target.value[i]
}

function pick() {
  if (mode.value === 'en') {
    const words = Array.from({ length: 12 }, () => EN_WORDS[Math.floor(Math.random() * EN_WORDS.length)])
    return words.join(' ')
  }
  return ZH_SENTS[Math.floor(Math.random() * ZH_SENTS.length)]
}

function setMode(m) {
  if (running.value) return
  mode.value = m
  finished.value = false
  typed.value = ''
  target.value = ''
}

function start() {
  running.value = true; finished.value = false
  typed.value = ''; totalTyped = 0; correctTyped = 0; piecesDone = 0
  stats.chars = 0; stats.wpm = 0; stats.acc = 100
  target.value = pick()
  deadline = Date.now() + 60000
  stats.left = 60
  clearInterval(timerId)
  timerId = setInterval(tick, 500)
  nextTick(() => inputEl.value?.focus())
}

function tick() {
  const left = Math.max(0, Math.round((deadline - Date.now()) / 1000))
  stats.left = left
  updateLive()
  if (left <= 0) finish()
}

function onType() {
  if (!running.value) return
  // 命中整段：换下一段
  if (typed.value === target.value) {
    correctTyped += target.value.length
    totalTyped += target.value.length
    piecesDone++
    stats.chars = totalTyped
    typed.value = ''
    target.value = pick()
    updateLive()
    return
  }
  // 超出目标长度（打错了没修正）：裁掉，防止刷字符数
  if (typed.value.length > target.value.length) typed.value = typed.value.slice(0, target.value.length)
  updateLive()
}

function updateLive() {
  const elapsedMin = Math.max(0.01, (60000 - (deadline - Date.now())) / 60000)
  const chars = piecesDone * targetLenBaseline() + typed.value.length
  const unit = mode.value === 'en' ? 5 : 1   // 英文 5 字符 = 1 word
  const correctNow = [...typed.value].filter((ch, i) => ch === target.value[i]).length
  const correctTotal = correctTyped + correctNow
  stats.chars = chars
  stats.wpm = Math.round(chars / unit / elapsedMin)
  const typedAll = totalTyped + typed.value.length
  stats.acc = typedAll ? Math.round((correctTotal / typedAll) * 100) : 100
}
function targetLenBaseline() { return 0 }

function finish() {
  clearInterval(timerId)
  running.value = false
  finished.value = true
  updateLive()
}

onBeforeUnmount(() => clearInterval(timerId))
</script>

<style scoped>
.ty-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.ty-tab {
  padding: 8px 22px; border-radius: 999px; border: 1px solid var(--dp-line, rgba(0,0,0,.1));
  background: transparent; color: var(--dp-text2, #45505b); cursor: pointer; font-size: 13.5px;
}
.ty-tab.active { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
.ty-stats { display: flex; gap: 30px; margin-bottom: 16px; }
.ty-stat { text-align: center; }
.ty-stat b { font-size: 26px; color: var(--yq-gold, #c7a96b); font-variant-numeric: tabular-nums; }
.ty-stat span { display: block; font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
.ty-ready { text-align: center; padding: 30px 0; display: flex; flex-direction: column; gap: 12px; align-items: center; }
.ty-btn {
  padding: 10px 26px; border-radius: 10px; font-size: 14px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text, #18202a);
}
.ty-btn.primary { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
.ty-hint { font-size: 12px; color: var(--dp-text3, #8a8f98); }
.ty-board { padding: 20px; display: flex; flex-direction: column; gap: 16px; }
.ty-target { font-size: 20px; line-height: 2; letter-spacing: .02em; word-break: break-all; color: var(--dp-text3, #8a8f98); min-height: 96px; }
.ty-ch.done { color: var(--dp-text, #18202a); }
.ty-ch.wrong { color: #e5484d; background: rgba(229,72,77,.12); border-radius: 3px; }
.ty-input {
  width: 100%; padding: 12px 14px; border-radius: 10px; font-size: 16px;
  border: 1px solid var(--dp-line, rgba(0,0,0,.12)); background: var(--dp-surface, #fff); color: var(--dp-text, #18202a);
}
.ty-result { padding: 16px 20px; font-size: 14.5px; color: var(--dp-text, #18202a); display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.ty-result b { color: var(--yq-gold, #c7a96b); font-size: 18px; }
</style>
