<template>
  <!-- v2.46.115 翻页时钟（夜星：参考截图做时分秒展示，挂手机端工作台首页）
       经典 flip clock 结构：每张卡上下半各一份当前值 + 翻转中的两份下一值，
       翻页时上半绕底边翻下（变暗）、下半绕顶边翻上（恢复），中缝分割线模拟纸牌折痕。
       参考 GitHub Yuezi32/flipClock 的四层翻牌原理，视觉按玄黄移动端语言重做。 -->
  <div class="mfc" aria-label="当前时间">
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
            <div class="mfc-half mfc-up"><span>{{ digits[gi * 2 + k].cur }}</span></div>
            <div class="mfc-half mfc-down"><span>{{ digits[gi * 2 + k].cur }}</span></div>
            <template v-if="digits[gi * 2 + k].flipping">
              <div class="mfc-half mfc-up mfc-flip-up"><span>{{ digits[gi * 2 + k].next }}</span></div>
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

/* 六位数字：HH MM SS 各两位，独立管理翻转态 */
const digits = reactive(
  Array.from({ length: 6 }, () => ({ cur: '0', next: '0', flipping: false }))
)
const dateText = ref('')

const WEEK = '日一二三四五六'
const FLIP_MS = 620                 // 与 CSS 两段式翻页总时长对齐
const reduced =
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

const pad = (n) => String(n).padStart(2, '0')

let timer = null

function sync() {
  const d = new Date()
  const s = pad(d.getHours()) + pad(d.getMinutes()) + pad(d.getSeconds())
  dateText.value = `${d.getMonth() + 1} 月 ${d.getDate()} 日 · 星期${WEEK[d.getDay()]}`
  for (let i = 0; i < 6; i++) {
    const v = s[i]
    if (digits[i].cur === v) continue
    if (reduced) { digits[i].cur = v; continue }
    digits[i].next = v
    digits[i].flipping = true
    const idx = i
    setTimeout(() => {
      digits[idx].cur = digits[idx].next
      digits[idx].flipping = false
    }, FLIP_MS)
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
/* ===== v2.46.115 翻页时钟 =====
   黑卡白字（经典 flip clock 语言，亮/暗两套主题下都成立）；
   尺寸走 CSS 变量，窄屏（<360）自动缩一档；鸿蒙 WebView 的 3D transform 支持良好。 */
.mfc {
  --mfc-w: 42px; --mfc-h: 62px; --mfc-fs: 36px; --mfc-r: 10px; --mfc-gap: 5px;
  margin-top: 18px; padding: 16px 20px 18px; border-radius: 24px;
  background: linear-gradient(168deg, #171922 0%, #0b0c11 64%);
  border: 1px solid rgba(255, 255, 255, .07);
  box-shadow: 0 18px 38px -18px rgba(8, 10, 20, .55), inset 0 1px 0 rgba(255, 255, 255, .06);
  display: flex; flex-direction: column; align-items: center; gap: 13px;
  animation: mfc-rise .5s cubic-bezier(.2, .8, .2, 1) both;
}
.mfc-date {
  font-size: 12px; letter-spacing: .14em; color: rgba(255, 255, 255, .55);
  font-variant-numeric: tabular-nums;
}
.mfc-clock { display: flex; align-items: center; gap: 10px; }
.mfc-group { display: flex; gap: var(--mfc-gap); }
.mfc-colon { display: flex; flex-direction: column; gap: 9px; padding: 0 1px; }
.mfc-colon i { width: 6px; height: 6px; border-radius: 50%; background: rgba(255, 255, 255, .85); }

/* 单张翻牌：perspective 给翻转层提供景深 */
.mfc-card { position: relative; width: var(--mfc-w); height: var(--mfc-h); perspective: 260px; }
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
/* 翻转层：上半翻下（同时变暗）、下半延迟翻上（恢复），两段合计 620ms */
.mfc-flip-up {
  z-index: 3; transform-origin: center bottom;
  animation: mfc-up .3s cubic-bezier(.55, .06, .68, .19) forwards;
}
.mfc-flip-down {
  z-index: 4; transform-origin: center top;
  animation: mfc-down .3s .3s cubic-bezier(.22, .61, .36, 1) backwards;
}
@keyframes mfc-up {
  from { transform: rotateX(0deg); filter: brightness(1); }
  to { transform: rotateX(-90deg); filter: brightness(.55); }
}
@keyframes mfc-down {
  from { transform: rotateX(90deg); filter: brightness(.55); }
  to { transform: rotateX(0deg); filter: brightness(1); }
}
@keyframes mfc-rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }

/* 窄屏（<360）缩一档，保证三组 + 冒号放得下 */
@media (max-width: 360px) {
  .mfc { --mfc-w: 37px; --mfc-h: 55px; --mfc-fs: 31px; --mfc-r: 9px; padding: 14px 16px 16px; }
}
/* 动效降级：无翻页动画，数字直接切换 */
@media (prefers-reduced-motion: reduce) {
  .mfc { animation: none; }
  .mfc-flip-up, .mfc-flip-down { animation-duration: .001s; animation-delay: 0s; }
}
</style>
