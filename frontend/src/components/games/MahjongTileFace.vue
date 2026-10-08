<template>
  <!--
    麻将牌面 · 纯矢量（v2.46.1 重绘）

    旧版问题（夜星反馈）：
      · 万 —— 上方汉字数字 56px、下方「萬」52px 且基线压到 y=126，
        字身一路顶出 140 的 viewBox 被裁掉一截 → 看着「数字大、文字小」；
      · 条 —— 3/5/7 条的竹节行距不等（间隙 10 / 2 / 2），整张牌「上面挤、下面空」；
      · 筒 —— 蓝绿都压得很灰（#1c4e8a / #1c6b41），十几种排布在同一屏里几乎同色。

    本版：万牌按「上数字 / 下萬字」重排并让萬字明显更大；条牌改为等距网格；
    筒牌按传统牌面的「红 / 墨绿 / 蓝」三色规则重排（详见下方 TONG_LAYOUT 注释），
    而不是每张牌单色或随意配蓝绿。
    坐标一律以 viewBox 100×140 为准，实际尺寸由外层 .gt-tile 决定，故怎么缩放都清晰。
  -->
  <svg class="mj-face" viewBox="0 0 100 140" aria-hidden="true" focusable="false">
    <!-- ===== 万：上「汉字数字」小、下「萬」大（真实麻将的比例，萬字占下半张） ===== -->
    <template v-if="suit === 'wan'">
      <text class="f-num" x="50" y="41">{{ NUM_CN[rank] }}</text>
      <text class="f-wan" x="50" y="101">萬</text>
    </template>

    <!-- ===== 筒：圆点阵（外彩环 + 白瓷底 + 彩心，仿铜钱的钱肉/方孔） ===== -->
    <template v-else-if="suit === 'tong'">
      <template v-for="(d, i) in tongDots" :key="i">
        <!-- 空心彩环：白底 + 粗彩描边（一筒的外/内两环、其余牌的主环） -->
        <circle
          v-if="!d.solid"
          :cx="d.x" :cy="d.y" :r="d.r"
          fill="#fffdf7" :stroke="d.c" :stroke-width="d.sw"
        />
        <!-- 实心圆：一筒的红色圆心 -->
        <circle v-if="d.solid" :cx="d.x" :cy="d.y" :r="d.r" :fill="d.c" />
        <!-- 彩心：默认取半径一半；ring:true 的环不再点心（一筒靠叠环出花纹） -->
        <circle
          v-else-if="!d.ring"
          :cx="d.x" :cy="d.y" :r="d.dot || d.r * 0.5"
          :fill="d.c"
        />
      </template>
    </template>

    <!-- ===== 条：竹节条（1 条是幺鸡；5 条中心、7 条顶上一根为红） ===== -->
    <template v-else-if="suit === 'tiao'">
      <!-- 幺鸡：一只鸟（1 条） -->
      <g v-if="rank === 1" class="f-bird">
        <path d="M36 104 C16 118 12 130 24 132 C30 133 36 126 42 116 Z" fill="#15803f" />
        <path d="M40 100 C22 110 20 122 32 124 C38 125 44 116 48 108 Z" fill="#2ba055" />
        <ellipse cx="52" cy="80" rx="19" ry="25" fill="#15803f" />
        <ellipse cx="45" cy="82" rx="10" ry="16" fill="#2ba055" />
        <circle cx="54" cy="48" r="12.5" fill="#15803f" />
        <path d="M64 44 L79 50 L64 55 Z" fill="#e0a52a" />
        <circle cx="57" cy="44" r="3" fill="#fffdf7" />
        <circle cx="58" cy="44" r="1.5" fill="#171717" />
        <path d="M48 30 C52 20 60 20 63 27" fill="none" stroke="#d02f28" stroke-width="4" stroke-linecap="round" />
        <line x1="47" y1="104" x2="43" y2="124" stroke="#e0a52a" stroke-width="3.4" stroke-linecap="round" />
        <line x1="58" y1="104" x2="62" y2="124" stroke="#e0a52a" stroke-width="3.4" stroke-linecap="round" />
        <line x1="36" y1="125" x2="50" y2="125" stroke="#e0a52a" stroke-width="3" stroke-linecap="round" />
        <line x1="55" y1="125" x2="69" y2="125" stroke="#e0a52a" stroke-width="3" stroke-linecap="round" />
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
            stroke="rgba(255,255,255,.55)" stroke-width="2"
          />
          <line
            :x1="s.x - s.w / 2 + 2" :x2="s.x + s.w / 2 - 2"
            :y1="s.y + s.h / 6" :y2="s.y + s.h / 6"
            stroke="rgba(255,255,255,.55)" stroke-width="2"
          />
          <line
            :x1="s.x" :x2="s.x" :y1="s.y - s.h / 2 + 3" :y2="s.y + s.h / 2 - 3"
            stroke="rgba(0,0,0,.18)" stroke-width="1.6"
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

/* 高饱和三色：旧值（#1c4e8a / #1c6b41 / #b3261e）在深绿桌布上发灰，
   十几种筒子排布挤在一起时几乎分不出谁是谁 */
const BLUE = '#1657c9'
const GREEN = '#0b8a4d'
const RED = '#d21f26'

/**
 * 筒子圆点阵：{x, y, r, c, sw} + 可选 ring / solid / dot。
 *
 * 配色依据（v2.46.3 按传统牌面重排，不再是「每张牌单色或蓝绿随便配」）：
 *  · 中文维基「麻将牌 / 麻雀牌」筒子一节：二筒由绿蓝色圆垂直组成；
 *    三筒为蓝、红、绿的圆排成斜线；四筒两蓝两绿对角；五筒＝四筒＋中心红；
 *    六筒顶部两个绿圆、底部四个红圆；七筒顶部三个绿圆斜排、底部四个红圆；
 *    八筒八个蓝圆（2×4）；九筒三行，由顶至底为蓝、红、绿。
 *  · 百度百科「筒子」条目：传统用红色与墨绿交替染筒，**唯四筒和八筒不着红**。
 *  → 两张资料合并后，1/2/3/5/6/7/9 都带红，只有 4/8 是纯蓝绿，本表即按此落地。
 *  · 一筒是「大饼」：一个多色同心大圆，外红环 + 内绿环 + 红心。
 *  · 二筒「眼镜」：上红下绿两圆（夜星记忆的配色，也符合「除四/八筒都带红」）。
 */
const TONG_LAYOUT = {
  1: [
    { x: 50, y: 70, r: 34, c: RED, sw: 9, ring: true },
    { x: 50, y: 70, r: 20, c: GREEN, sw: 7, ring: true },
    { x: 50, y: 70, r: 7.5, c: RED, solid: true },
  ],
  2: [
    { x: 50, y: 40, r: 19, c: RED, sw: 6 },
    { x: 50, y: 100, r: 19, c: GREEN, sw: 6 },
  ],
  3: [
    { x: 26, y: 32, r: 15.5, c: BLUE, sw: 5.4 },
    { x: 50, y: 70, r: 15.5, c: RED, sw: 5.4 },
    { x: 74, y: 108, r: 15.5, c: GREEN, sw: 5.4 },
  ],
  4: [
    { x: 30, y: 42, r: 16, c: BLUE, sw: 5.4 },
    { x: 70, y: 42, r: 16, c: GREEN, sw: 5.4 },
    { x: 30, y: 98, r: 16, c: GREEN, sw: 5.4 },
    { x: 70, y: 98, r: 16, c: BLUE, sw: 5.4 },
  ],
  5: [
    { x: 30, y: 40, r: 13, c: BLUE, sw: 4.8 },
    { x: 70, y: 40, r: 13, c: GREEN, sw: 4.8 },
    { x: 50, y: 70, r: 13, c: RED, sw: 4.8 },
    { x: 30, y: 100, r: 13, c: GREEN, sw: 4.8 },
    { x: 70, y: 100, r: 13, c: BLUE, sw: 4.8 },
  ],
  6: [
    { x: 32, y: 30, r: 16, c: GREEN, sw: 5.4 },
    { x: 68, y: 30, r: 16, c: GREEN, sw: 5.4 },
    { x: 32, y: 76, r: 13.5, c: RED, sw: 4.8 },
    { x: 68, y: 76, r: 13.5, c: RED, sw: 4.8 },
    { x: 32, y: 114, r: 13.5, c: RED, sw: 4.8 },
    { x: 68, y: 114, r: 13.5, c: RED, sw: 4.8 },
  ],
  7: [
    { x: 24, y: 26, r: 12, c: GREEN, sw: 4.4 },
    { x: 50, y: 46, r: 12, c: GREEN, sw: 4.4 },
    { x: 76, y: 66, r: 12, c: GREEN, sw: 4.4 },
    { x: 30, y: 94, r: 11, c: RED, sw: 4.2 },
    { x: 70, y: 94, r: 11, c: RED, sw: 4.2 },
    { x: 30, y: 124, r: 11, c: RED, sw: 4.2 },
    { x: 70, y: 124, r: 11, c: RED, sw: 4.2 },
  ],
  8: [
    { x: 32, y: 26, r: 12, c: BLUE, sw: 4.4 },
    { x: 68, y: 26, r: 12, c: BLUE, sw: 4.4 },
    { x: 32, y: 56, r: 12, c: BLUE, sw: 4.4 },
    { x: 68, y: 56, r: 12, c: BLUE, sw: 4.4 },
    { x: 32, y: 86, r: 12, c: BLUE, sw: 4.4 },
    { x: 68, y: 86, r: 12, c: BLUE, sw: 4.4 },
    { x: 32, y: 116, r: 12, c: BLUE, sw: 4.4 },
    { x: 68, y: 116, r: 12, c: BLUE, sw: 4.4 },
  ],
  9: [
    { x: 26, y: 34, r: 12, c: BLUE, sw: 4.4 },
    { x: 50, y: 34, r: 12, c: BLUE, sw: 4.4 },
    { x: 74, y: 34, r: 12, c: BLUE, sw: 4.4 },
    { x: 26, y: 70, r: 12, c: RED, sw: 4.4 },
    { x: 50, y: 70, r: 12, c: RED, sw: 4.4 },
    { x: 74, y: 70, r: 12, c: RED, sw: 4.4 },
    { x: 26, y: 106, r: 12, c: GREEN, sw: 4.4 },
    { x: 50, y: 106, r: 12, c: GREEN, sw: 4.4 },
    { x: 74, y: 106, r: 12, c: GREEN, sw: 4.4 },
  ],
}

const tongDots = computed(() => TONG_LAYOUT[props.rank] || TONG_LAYOUT[1])

/** 竹节条：{x, y, w, h, c}。
 *  行距一律取「(140 - 2×14) / 行数」，上下留白各 14 —— 旧版 3/5/7 条各行间距
 *  分别为 10 / 2 / 2，整张牌重心偏上，看着「分布不均匀」。 */
const TIAO_LAYOUT = {
  2: [{ x: 34, y: 70, h: 64 }, { x: 66, y: 70, h: 64 }],
  3: [
    { x: 50, y: 38, h: 40 },
    { x: 32, y: 102, h: 40 }, { x: 68, y: 102, h: 40 },
  ],
  4: [
    { x: 34, y: 42, h: 44 }, { x: 66, y: 42, h: 44 },
    { x: 34, y: 98, h: 44 }, { x: 66, y: 98, h: 44 },
  ],
  5: [
    { x: 32, y: 38, h: 30 }, { x: 68, y: 38, h: 30 },
    { x: 50, y: 70, h: 30, red: true },
    { x: 32, y: 102, h: 30 }, { x: 68, y: 102, h: 30 },
  ],
  6: [
    { x: 34, y: 32, h: 28 }, { x: 66, y: 32, h: 28 },
    { x: 34, y: 70, h: 28 }, { x: 66, y: 70, h: 28 },
    { x: 34, y: 108, h: 28 }, { x: 66, y: 108, h: 28 },
  ],
  7: [
    { x: 50, y: 28, h: 22, red: true },
    { x: 34, y: 56, h: 22 }, { x: 66, y: 56, h: 22 },
    { x: 34, y: 84, h: 22 }, { x: 66, y: 84, h: 22 },
    { x: 34, y: 112, h: 22 }, { x: 66, y: 112, h: 22 },
  ],
  8: [
    { x: 34, y: 28, h: 22 }, { x: 66, y: 28, h: 22 },
    { x: 34, y: 56, h: 22 }, { x: 66, y: 56, h: 22 },
    { x: 34, y: 84, h: 22 }, { x: 66, y: 84, h: 22 },
    { x: 34, y: 112, h: 22 }, { x: 66, y: 112, h: 22 },
  ],
  9: [
    { x: 26, y: 32, h: 30 }, { x: 50, y: 32, h: 30 }, { x: 74, y: 32, h: 30 },
    { x: 26, y: 70, h: 30 }, { x: 50, y: 70, h: 30 }, { x: 74, y: 70, h: 30 },
    { x: 26, y: 108, h: 30 }, { x: 50, y: 108, h: 30 }, { x: 74, y: 108, h: 30 },
  ],
}

const tiaoSticks = computed(() => {
  const rows = TIAO_LAYOUT[props.rank] || TIAO_LAYOUT[2]
  return rows.map((s, i) => ({
    ...s,
    w: Math.max(12, Math.min(16, s.h * 0.5)),
    c: s.red ? RED : (i % 2 === 1 ? '#0d8a5c' : '#12945f'),
  }))
})
</script>

<style scoped>
.mj-face { display: block; width: 100%; height: 100%; }
/* 万：数字在上（36px），「萬」在下（56px）—— 旧版两者都是 5x px 且萬字被下缘裁掉，
   于是观感成了「数字大、文字小」 */
.f-num {
  font-size: 36px; font-weight: 700; fill: #17457f;
  text-anchor: middle; dominant-baseline: central;
  font-family: "Songti SC", "SimSun", "Noto Serif SC", "STSong", serif;
}
.f-wan {
  font-size: 56px; font-weight: 700; fill: #c62828;
  text-anchor: middle; dominant-baseline: central;
  font-family: "Songti SC", "SimSun", "Noto Serif SC", "STSong", serif;
}
</style>
