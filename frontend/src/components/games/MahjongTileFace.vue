<template>
  <!--
    麻将牌面 · 纯矢量（v2.46）

    旧版牌面只有「数字 + 花色字」（`5万`），不像麻将。这里按传统牌面画：
      · 万 = 上汉字数字 + 下红「萬」
      · 筒 = 标准排布的圆点阵（外圈 + 内点），1 筒是大花心
      · 条 = 竹节条（5 条中心、7 条顶上一根为红），1 条是幺鸡（鸟）
    viewBox 固定 100×140（麻将牌 1:1.4），实际尺寸由外层 .gt-tile 决定，故怎么缩放都清晰。
  -->
  <svg class="mj-face" viewBox="0 0 100 140" aria-hidden="true" focusable="false">
    <!-- ===== 万 ===== -->
    <template v-if="suit === 'wan'">
      <text class="f-num" x="50" y="66">{{ NUM_CN[rank] }}</text>
      <text class="f-wan" x="50" y="126">萬</text>
    </template>

    <!-- ===== 筒 ===== -->
    <template v-else-if="suit === 'tong'">
      <g v-for="(d, i) in tongDots" :key="i">
        <circle :cx="d.x" :cy="d.y" :r="d.r" fill="#fbf8ef" :stroke="d.c" :stroke-width="d.sw || 5" />
        <circle :cx="d.x" :cy="d.y" :r="(d.r) * 0.42" :fill="d.c" />
      </g>
    </template>

    <!-- ===== 条 ===== -->
    <template v-else-if="suit === 'tiao'">
      <!-- 幺鸡：一只鸟（1 条） -->
      <g v-if="rank === 1" class="f-bird">
        <path d="M36 104 C16 118 12 130 24 132 C30 133 36 126 42 116 Z" fill="#1c6b41" />
        <path d="M40 100 C22 110 20 122 32 124 C38 125 44 116 48 108 Z" fill="#2f8f52" />
        <ellipse cx="52" cy="80" rx="19" ry="25" fill="#1c6b41" />
        <ellipse cx="45" cy="82" rx="10" ry="16" fill="#2f8f52" />
        <circle cx="54" cy="48" r="12.5" fill="#1c6b41" />
        <path d="M64 44 L79 50 L64 55 Z" fill="#d8a12a" />
        <circle cx="57" cy="44" r="3" fill="#fbf8ef" />
        <circle cx="58" cy="44" r="1.5" fill="#171717" />
        <path d="M48 30 C52 20 60 20 63 27" fill="none" stroke="#b3261e" stroke-width="4" stroke-linecap="round" />
        <line x1="47" y1="104" x2="43" y2="124" stroke="#d8a12a" stroke-width="3.4" stroke-linecap="round" />
        <line x1="58" y1="104" x2="62" y2="124" stroke="#d8a12a" stroke-width="3.4" stroke-linecap="round" />
        <line x1="36" y1="125" x2="50" y2="125" stroke="#d8a12a" stroke-width="3" stroke-linecap="round" />
        <line x1="55" y1="125" x2="69" y2="125" stroke="#d8a12a" stroke-width="3" stroke-linecap="round" />
      </g>
      <!-- 竹节条（2~9 条） -->
      <g v-else>
        <g v-for="(s, i) in tiaoSticks" :key="i">
          <rect
            :x="s.x - s.w / 2" :y="s.y - s.h / 2" :width="s.w" :height="s.h"
            :rx="s.w / 2.4" :fill="s.c"
          />
          <line
            :x1="s.x - s.w / 2 + 2" :x2="s.x + s.w / 2 - 2"
            :y1="s.y - s.h / 6" :y2="s.y - s.h / 6"
            stroke="rgba(255,255,255,.5)" stroke-width="2"
          />
          <line
            :x1="s.x - s.w / 2 + 2" :x2="s.x + s.w / 2 - 2"
            :y1="s.y + s.h / 6" :y2="s.y + s.h / 6"
            stroke="rgba(255,255,255,.5)" stroke-width="2"
          />
          <line
            :x1="s.x" :x2="s.x" :y1="s.y - s.h / 2 + 3" :y2="s.y + s.h / 2 - 3"
            stroke="rgba(0,0,0,.16)" stroke-width="1.6"
          />
        </g>
      </g>
    </template>
  </svg>
</template>

<script setup>
/** 麻将牌面（矢量）。只负责画，不管尺寸与边框 —— 外层 .gt-tile 决定尺寸。 */
import { computed } from 'vue'

const props = defineProps({
  suit: { type: String, required: true },   // wan | tiao | tong
  rank: { type: Number, required: true },   // 1..9
})

const NUM_CN = { 1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九' }

const BLUE = '#1c4e8a'
const GREEN = '#1c6b41'
const RED = '#b3261e'

/** 每筒排布：{x, y, r}；颜色按行交错（传统筒子蓝绿相间，1 筒为红绿花心） */
const TONG_LAYOUT = {
  1: [{ x: 50, y: 70, r: 27, sw: 7, c: RED }, { x: 50, y: 70, r: 17, sw: 5, c: GREEN }],
  2: [{ x: 50, y: 44 }, { x: 50, y: 96 }].map((d) => ({ ...d, r: 16, c: BLUE })),
  3: [{ x: 26, y: 34 }, { x: 50, y: 70 }, { x: 74, y: 106 }].map((d) => ({ ...d, r: 15, c: GREEN })),
  4: [{ x: 30, y: 44 }, { x: 70, y: 44 }, { x: 30, y: 96 }, { x: 70, y: 96 }].map((d) => ({ ...d, r: 15, c: BLUE })),
  5: [
    { x: 30, y: 42 }, { x: 70, y: 42 }, { x: 50, y: 70 }, { x: 30, y: 98 }, { x: 70, y: 98 },
  ].map((d) => ({ ...d, r: 14, c: BLUE })),
  6: [
    { x: 30, y: 36 }, { x: 70, y: 36 },
    { x: 30, y: 70 }, { x: 70, y: 70 },
    { x: 30, y: 104 }, { x: 70, y: 104 },
  ].map((d, i) => ({ ...d, r: 13, c: i < 2 ? GREEN : BLUE })),
  7: [
    { x: 27, y: 32 }, { x: 50, y: 50 }, { x: 73, y: 68 },
    { x: 30, y: 94 }, { x: 70, y: 94 }, { x: 30, y: 118 }, { x: 70, y: 118 },
  ].map((d, i) => ({ ...d, r: 10.5, c: i < 3 ? GREEN : BLUE })),
  8: [
    { x: 30, y: 30 }, { x: 70, y: 30 },
    { x: 30, y: 57 }, { x: 70, y: 57 },
    { x: 30, y: 84 }, { x: 70, y: 84 },
    { x: 30, y: 111 }, { x: 70, y: 111 },
  ].map((d, i) => ({ ...d, r: 11, c: i % 4 < 2 ? GREEN : BLUE })),
  9: [
    { x: 26, y: 36 }, { x: 50, y: 36 }, { x: 74, y: 36 },
    { x: 26, y: 70 }, { x: 50, y: 70 }, { x: 74, y: 70 },
    { x: 26, y: 104 }, { x: 50, y: 104 }, { x: 74, y: 104 },
  ].map((d, i) => ({ ...d, r: 11.5, c: i % 3 === 1 ? GREEN : BLUE })),
}

const tongDots = computed(() => TONG_LAYOUT[props.rank] || TONG_LAYOUT[1])

/** 竹节条：{x, y, w, h, c}。5 条中心、7 条顶上为红（传统配色） */
const TIAO_LAYOUT = {
  2: [{ x: 36, y: 70, h: 56 }, { x: 64, y: 70, h: 56 }],
  3: [{ x: 50, y: 36, h: 46 }, { x: 34, y: 98, h: 46 }, { x: 66, y: 98, h: 46 }],
  4: [{ x: 36, y: 42, h: 46 }, { x: 64, y: 42, h: 46 }, { x: 36, y: 98, h: 46 }, { x: 64, y: 98, h: 46 }],
  5: [
    { x: 34, y: 40, h: 40 }, { x: 66, y: 40, h: 40 },
    { x: 50, y: 70, h: 42, red: true },
    { x: 34, y: 100, h: 40 }, { x: 66, y: 100, h: 40 },
  ],
  6: [
    { x: 36, y: 32, h: 34 }, { x: 64, y: 32, h: 34 },
    { x: 36, y: 70, h: 34 }, { x: 64, y: 70, h: 34 },
    { x: 36, y: 108, h: 34 }, { x: 64, y: 108, h: 34 },
  ],
  7: [
    { x: 50, y: 28, h: 28, red: true },
    { x: 36, y: 62, h: 24 }, { x: 64, y: 62, h: 24 },
    { x: 36, y: 88, h: 24 }, { x: 64, y: 88, h: 24 },
    { x: 36, y: 114, h: 24 }, { x: 64, y: 114, h: 24 },
  ],
  8: [
    { x: 36, y: 30, h: 26 }, { x: 64, y: 30, h: 26 },
    { x: 36, y: 58, h: 26 }, { x: 64, y: 58, h: 26 },
    { x: 36, y: 86, h: 26 }, { x: 64, y: 86, h: 26 },
    { x: 36, y: 114, h: 26 }, { x: 64, y: 114, h: 26 },
  ],
  9: [
    { x: 25, y: 36, h: 30 }, { x: 50, y: 36, h: 30 }, { x: 75, y: 36, h: 30 },
    { x: 25, y: 70, h: 30 }, { x: 50, y: 70, h: 30 }, { x: 75, y: 70, h: 30 },
    { x: 25, y: 104, h: 30 }, { x: 50, y: 104, h: 30 }, { x: 75, y: 104, h: 30 },
  ],
}

const tiaoSticks = computed(() => {
  const rows = TIAO_LAYOUT[props.rank] || TIAO_LAYOUT[2]
  return rows.map((s, i) => ({
    ...s,
    w: Math.max(11, Math.min(16, s.h * 0.46)),
    c: s.red ? RED : (i % 2 === 1 ? '#1c6b41' : '#227a4a'),
  }))
})
</script>

<style scoped>
.mj-face { display: block; width: 100%; height: 100%; }
.f-num {
  font-size: 56px; font-weight: 700; fill: #1c3f6e;
  text-anchor: middle; dominant-baseline: central;
  font-family: "Songti SC", "SimSun", "Noto Serif SC", "STSong", serif;
}
.f-wan {
  font-size: 52px; font-weight: 700; fill: #b3261e;
  text-anchor: middle; dominant-baseline: central;
  font-family: "Songti SC", "SimSun", "Noto Serif SC", "STSong", serif;
}
</style>
