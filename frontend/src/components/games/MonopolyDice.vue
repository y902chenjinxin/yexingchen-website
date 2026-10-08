<template>
  <!--
    大富翁骰子 · 纯 SVG 圆点（v2.46）

    旧版直接拿 Unicode 字符 `⚀⚁⚂⚃⚄⚅` 当骰子：字重随系统字体漂移、没有立体感，
    掷骰时只有父级一个 0.32s 的轻微抖动 —— 玩家几乎感觉不到「在掷」。
    这里改成白瓷骰子：牌身三层投影做厚度、内凹圆点，掷骰期间 3D 翻滚 +
    面快速跳变（70ms 一次），落定时弹跳一下。父组件只负责把最终点数传进来。
  -->
  <div class="mdy" :class="{ 'is-rolling': rolling, 'is-landed': landed }" aria-hidden="true">
    <span class="mdy-body"></span>
    <svg class="mdy-pips" viewBox="0 0 100 100" focusable="false">
      <circle v-for="(p, i) in pips" :key="i" :cx="p[0]" :cy="p[1]" r="10.5" />
    </svg>
  </div>
</template>

<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  value: { type: Number, default: 1 },
  rolling: { type: Boolean, default: false },
})

/** 各点数圆点位置（100×100 视图坐标） */
const PIPS = {
  1: [[50, 50]],
  2: [[30, 30], [70, 70]],
  3: [[27, 27], [50, 50], [73, 73]],
  4: [[30, 30], [70, 30], [30, 70], [70, 70]],
  5: [[30, 30], [70, 30], [50, 50], [30, 70], [70, 70]],
  6: [[30, 25], [70, 25], [30, 50], [70, 50], [30, 75], [70, 75]],
}

const face = ref(props.value || 1)
const landed = ref(false)
let spinTimer = null
let landTimer = null

function stopSpin() {
  if (spinTimer) { clearInterval(spinTimer); spinTimer = null }
}

watch(() => props.rolling, (v) => {
  if (v) {
    landed.value = false
    stopSpin()
    // 掷骰期间面快速跳变，配合 CSS 翻滚 —— 只转不换面会显得「假」
    spinTimer = setInterval(() => { face.value = 1 + Math.floor(Math.random() * 6) }, 70)
    return
  }
  stopSpin()
  face.value = props.value || 1
  landed.value = true
  clearTimeout(landTimer)
  landTimer = setTimeout(() => { landed.value = false }, 440)
}, { immediate: true })

watch(() => props.value, (v) => { if (!props.rolling) face.value = v || 1 })

onBeforeUnmount(() => {
  stopSpin()
  clearTimeout(landTimer)
})

const pips = computed(() => PIPS[face.value] || PIPS[1])
</script>

<style scoped>
.mdy {
  position: relative;
  width: var(--mdy-size, 46px); height: var(--mdy-size, 46px);
  transform-origin: 50% 50%;
}
.mdy-body {
  position: absolute; inset: 0; border-radius: 22%;
  background: linear-gradient(168deg, #fffefb 0%, #f5f1e6 56%, #ddd5c2 100%);
  box-shadow:
    inset 0 2px 0 rgba(255, 255, 255, .95),
    inset 0 -7px 13px -7px rgba(125, 115, 88, .4),
    0 3px 0 #c3baa2,
    0 6px 0 #aca289,
    0 14px 20px -10px rgba(0, 0, 0, .78);
}
.mdy-pips { position: absolute; inset: 0; width: 100%; height: 100%; }
.mdy-pips circle {
  fill: #2b3a33;
  /* 内凹感：点上再叠一层浅色偏移，模拟凹坑受光 */
  filter: drop-shadow(0 .6px .6px rgba(255, 255, 255, .5));
}

/* 掷骰：3D 翻滚（旋转 + 轻微缩放，模拟空中翻转） */
.mdy.is-rolling { animation: mdy-tumble .46s cubic-bezier(.45, .05, .55, .95) infinite; }
@keyframes mdy-tumble {
  0% { transform: rotate(0deg) scale(1); }
  20% { transform: rotate(80deg) scale(1.09); }
  40% { transform: rotate(170deg) scale(.95); }
  60% { transform: rotate(250deg) scale(1.07); }
  80% { transform: rotate(330deg) scale(.96); }
  100% { transform: rotate(360deg) scale(1); }
}
/* 落定：放大 → 压扁 → 回弹 */
.mdy.is-landed { animation: mdy-land .42s cubic-bezier(.3, 1.7, .5, 1) both; }
@keyframes mdy-land {
  0% { transform: scale(1.34) rotate(-9deg); }
  55% { transform: scale(.93) rotate(3deg); }
  100% { transform: scale(1) rotate(0deg); }
}

@media (prefers-reduced-motion: reduce) {
  .mdy.is-rolling, .mdy.is-landed { animation: none; }
}
</style>
