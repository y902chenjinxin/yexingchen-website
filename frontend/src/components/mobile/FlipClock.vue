<template>
  <!-- v2.46.116 翻页时钟（夜星：时分秒工具，挂 /tool/flipclock 工具页，首页不展示）
       经典四层翻牌（GitHub 主流 flip clock 标准结构，参考 Yuezi32/flipClock 原理）：
       ① 静态上半 = 新值：翻页开始即更新（此刻被翻转层挡住看不见）；
       ② 翻转上半 = 旧值，绕底边 0→-90° 倒下，倒完露出静态新上半（不再延后）；
       ③ 延迟 .3s 翻转下半 = 新值，绕顶边 90°→0° 翻上，盖住静态旧下半；
       ④ .6s 收尾移除翻转层，上下半均新值，稳态。
       性能（鸿蒙 WebView 实测向）：动画只走 transform + opacity 合成属性；
       明暗变化用子层黑色遮罩 opacity，不用 filter brightness（filter 每帧
       重绘整卡，是 v2.46.115 卡顿的主因）；翻转层仅存活 600ms，will-change
       随之回收，不长期占层。 -->
  <div class="mfc" :class="'is-' + size" aria-label="当前时间">
    <div class="mfc-date">{{ dateText }}</div>
    <div class="mfc-clock" role="timer">
      <template v-for="(g, gi) in [0, 1, 2]" :key="gi">
        <div class="mfc-group">
          <div
            v-for="k in [0, 1]"
            :key="k"
            class="mfc-card"
            :class="{ 'is-flip': digits[gi * 2 + k].flipping }"
          >
            <div class="mfc-half mfc-up"><span>{{ digits[gi * 2 + k].next }}</span></div>
            <div class="mfc-half mfc-down"><span>{{ digits[gi * 2 + k].cur }}</span></div>
            <template v-if="digits[gi * 2 + k].flipping">
              <div class="mfc-half mfc-up mfc-flip-up"><span>{{ digits[gi * 2 + k].flipFrom }}</span></div>
              <div class="mfc-half mfc-down mfc-flip-down"><span>{{ digits[gi * 2 + k].next }}</span></div>
            </template>
          </div>
        </div>
        <div v-if="gi < 2" class="mfc-colon" aria-hidden="true"><i></i><i></i></div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'

defineProps({
  // sm：紧凑嵌入（首页/宫格用）；lg：工具页大尺寸
  size: { type: String, default: 'sm' },
})

/* 六位数字：HH MM SS 各两位，独立管理翻转态。
   cur = 当前显示值（静态下半用它）；next = 目标值（静态上半用它，翻页开始即新）；
   flipFrom = 翻页开始时的旧值快照（翻转上半用它——不随 cur 响应式变动，
   否则 300ms 静态下半切新时会带着倒下的旧卡片一起跳文本，虽已 edge-on 不可见，
   白触发一次文本重渲染）。 */
const digits = reactive(
  Array.from({ length: 6 }, () => ({ cur: '0', next: '0', flipFrom: '0', flipping: false }))
)
const dateText = ref('')

const WEEK = '日一二三四五六'
const HALF_MS = 300                 // 单段翻页时长（上倒下 .3s + 下翻上 .3s）
const FLIP_MS = HALF_MS * 2         // 总时长 600ms < 1s 翻页间隔，同一位不会叠翻
const reduced =
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

const pad = (n) => String(n).padStart(2, '0')

let timer = null

function sync() {
  const d = new Date()
  const s = pad(d.getHours()) + pad(d.getMinutes()) + pad(d.getSeconds())
  const dt = `${d.getMonth() + 1} 月 ${d.getDate()} 日 · 星期${WEEK[d.getDay()]}`
  if (dt !== dateText.value) dateText.value = dt
  for (let i = 0; i < 6; i++) {
    const v = s[i]
    if (digits[i].cur === v) continue
    // 0-300ms 窗口内 250ms tick 会再次命中（cur 尚未切新）：同目标翻转已在途中，跳过
    if (digits[i].flipping && digits[i].next === v) continue
    if (reduced) { digits[i].cur = v; digits[i].next = v; continue }
    digits[i].flipFrom = digits[i].cur
    digits[i].next = v
    digits[i].flipping = true
    const idx = i
    // 静态上半此刻已是 next（新）被挡住；300ms 旧上半倒完，静态下半切新，
    // 与正在翻入的翻转下半（也是新）同值无缝；600ms 收尾移除翻转层。
    setTimeout(() => { digits[idx].cur = v }, HALF_MS)
    setTimeout(() => { digits[idx].flipping = false }, FLIP_MS)
  }
}

onMounted(() => {
  sync()
  // 250ms 轮询 + 值对比：天然对齐整秒、无累积漂移（1s interval 会漂移跳秒）
  timer = setInterval(sync, 250)
})

onBeforeUnmount(() => {
  clearInterval(timer)
})
</script>

<style scoped>
/* ===== v2.46.116 翻页时钟 =====
   黑卡白字（经典 flip clock 语言，亮/暗两套主题下都成立）；
   尺寸走 CSS 变量（sm/lg 两档），窄屏自动缩一档；鸿蒙 WebView 3D transform 支持良好。 */
.mfc {
  display: flex; flex-direction: column; align-items: center; gap: 13px;
  padding: 16px 20px 18px; border-radius: 24px; max-width: 100%; box-sizing: border-box;
  background: linear-gradient(168deg, #171922 0%, #0b0c11 64%);
  border: 1px solid rgba(255, 255, 255, .07);
  box-shadow: 0 18px 38px -18px rgba(8, 10, 20, .55), inset 0 1px 0 rgba(255, 255, 255, .06);
  animation: mfc-rise .5s cubic-bezier(.2, .8, .2, 1) both;
}
.mfc.is-sm { --mfc-w: 42px; --mfc-h: 62px; --mfc-fs: 36px; --mfc-r: 10px; --mfc-gap: 5px; }
/* lg：工具页大尺寸。按 IslandInnerBase 移动端可用宽（390 屏≈358px / 360 屏≈328px）分三档，
   保证三组 + 冒号不横向溢出（v2.46.116 探针实测 390 视口曾溢出 98px）。 */
.mfc.is-lg { --mfc-w: 52px; --mfc-h: 76px; --mfc-fs: 44px; --mfc-r: 12px; --mfc-gap: 7px; padding: 22px 24px 24px; gap: 16px; }
.mfc-date {
  font-size: 12px; letter-spacing: .14em; color: rgba(255, 255, 255, .55);
  font-variant-numeric: tabular-nums;
}
.mfc.is-lg .mfc-date { font-size: 14px; }
.mfc-clock { display: flex; align-items: center; gap: 12px; }
.mfc.is-lg .mfc-clock { gap: 14px; }
.mfc-group { display: flex; gap: var(--mfc-gap); }
.mfc-colon { display: flex; flex-direction: column; gap: 9px; padding: 0 1px; }
.mfc-colon i { width: 6px; height: 6px; border-radius: 50%; background: rgba(255, 255, 255, .85); }
.mfc.is-lg .mfc-colon { gap: 11px; }
.mfc.is-lg .mfc-colon i { width: 7px; height: 7px; }

/* 单张翻牌：perspective 给翻转层提供景深 */
.mfc-card { position: relative; width: var(--mfc-w); height: var(--mfc-h); perspective: 300px; }
.mfc-half {
  position: absolute; left: 0; width: 100%; height: 50%; overflow: hidden;
  background: linear-gradient(180deg, #1b1d26, #12141b);
  backface-visibility: hidden; -webkit-backface-visibility: hidden;
}
.mfc-up { top: 0; border-radius: var(--mfc-r) var(--mfc-r) 0 0; box-shadow: inset 0 1px 0 rgba(255, 255, 255, .05); }
.mfc-down { bottom: 0; border-radius: 0 0 var(--mfc-r) var(--mfc-r); box-shadow: inset 0 -1px 0 rgba(0, 0, 0, .5); }
/* 数字用整卡高的 span：上半 top:0 / 下半 bottom:0，拼接后数字正好居中于整卡 */
.mfc-half span {
  position: absolute; left: 0; width: 100%; height: var(--mfc-h); line-height: var(--mfc-h);
  text-align: center; font-size: var(--mfc-fs); font-weight: 800; color: #fff;
  font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", "Segoe UI", Arial, sans-serif;
  font-variant-numeric: tabular-nums; letter-spacing: -.02em;
}
.mfc-up span { top: 0; }
.mfc-down span { bottom: 0; }
/* 中缝：纸牌折痕 */
.mfc-card::after {
  content: ""; position: absolute; top: calc(50% - .5px); left: 0; right: 0; height: 1px;
  background: rgba(0, 0, 0, .55); z-index: 5; pointer-events: none;
}
/* 翻转层：只活 600ms，will-change 随之回收。
   上半 = 旧值绕底边倒下；下半 = 新值绕顶边翻上（.3s 错峰 = 等上半倒完，物理时序）。 */
.mfc-flip-up, .mfc-flip-down { will-change: transform; }
.mfc-flip-up {
  z-index: 3; transform-origin: center bottom;
  animation: mfc-up .3s cubic-bezier(.55, .06, .68, .19) forwards;
}
.mfc-flip-down {
  z-index: 4; transform-origin: center top;
  animation: mfc-down .3s .3s cubic-bezier(.22, .61, .36, 1) backwards;
}
/* 明暗变化：子层黑遮罩 opacity 动画（合成属性）；不用 filter brightness（每帧重绘掉帧） */
.mfc-flip-up::after, .mfc-flip-down::after {
  content: ""; position: absolute; inset: 0; background: #000; opacity: 0; pointer-events: none;
}
.mfc-flip-up::after { animation: mfc-dim .3s cubic-bezier(.55, .06, .68, .19) forwards; }
.mfc-flip-down::after { animation: mfc-undim .3s .3s cubic-bezier(.22, .61, .36, 1) forwards; }
@keyframes mfc-up {
  from { transform: rotateX(0deg); }
  to { transform: rotateX(-90deg); }
}
@keyframes mfc-down {
  from { transform: rotateX(90deg); }
  to { transform: rotateX(0deg); }
}
@keyframes mfc-dim { from { opacity: 0; } to { opacity: .45; } }
@keyframes mfc-undim { from { opacity: .45; } to { opacity: 0; } }
@keyframes mfc-rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }

/* 窄屏缩档，保证三组 + 冒号放得下 */
@media (max-width: 360px) {
  .mfc.is-sm { --mfc-w: 37px; --mfc-h: 55px; --mfc-fs: 31px; --mfc-r: 9px; padding: 14px 16px 16px; }
}
/* lg 三档：≤430（大手机 390）总宽≈348 ≤ 可用 358；≤380（小手机 360）总宽≈313 ≤ 可用 328 */
@media (max-width: 430px) {
  .mfc.is-lg { --mfc-w: 44px; --mfc-h: 65px; --mfc-fs: 38px; padding: 16px 14px 18px; }
  .mfc.is-lg .mfc-clock { gap: 11px; }
  .mfc.is-lg .mfc-colon { gap: 9px; }
  .mfc.is-lg .mfc-colon i { width: 6px; height: 6px; }
}
@media (max-width: 380px) {
  .mfc.is-lg { --mfc-w: 40px; --mfc-h: 59px; --mfc-fs: 35px; padding: 14px 12px 16px; }
  .mfc.is-lg .mfc-clock { gap: 10px; }
}
/* 动效降级：无翻页动画，数字直接切换 */
@media (prefers-reduced-motion: reduce) {
  .mfc { animation: none; }
  .mfc-flip-up, .mfc-flip-down { animation-duration: .001s; animation-delay: 0s; }
  .mfc-flip-up::after, .mfc-flip-down::after { animation-duration: .001s; animation-delay: 0s; }
}
</style>
