<template>
  <!--
    麻将牌面 · 纯矢量

    设计依据（对照真实牌面，v2.46.4 重绘万 / 条；筒牌 v2.46.3 已对齐传统配色，本版不动）：
      · 万 —— 中文维基《麻将牌》：**顶部蓝色的是中文数字，底部红色的是「萬」字**；
        且「大多数麻将牌，伍萬都采用大写数字「伍」」。所以本版：数字化（一…九，五用伍）
        置于上方、蓝色；「萬」置于下方、红色，字身略大于数字化（约 1.3 : 1，真牌即如此）。
      · 条 —— 竹节条：偶数条全绿，奇数的 5 条中心、7 条顶上一根为红；1 条是幺鸡。
        旧版用两种几乎同色的绿交替（#0d8a5c / #12945f），小尺寸下看着是「花花的脏斑」，
        本版统一成一支竹子的画法：绿身 + 中段竹节暗线 + 左侧高光，红的那根单独上色。
      · 筒 —— 见 TONG_LAYOUT（红 / 墨绿 / 蓝三色传统排布）。
    坐标一律以 viewBox 100×140 为准，实际尺寸由外层 .gt-tile 决定，故怎么缩放都清晰。
  -->
  <svg class="mj-face" viewBox="0 0 100 140" aria-hidden="true" focusable="false">
    <!-- ===== 万：上「蓝数字」下「红萬」 ===== -->
    <template v-if="suit === 'wan'">
      <text class="f-num" x="50" y="38">{{ NUM_CN[rank] }}</text>
      <text class="f-wan" x="50" y="100">萬</text>
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
        <path d="M48 30 C52 20 60 20 63 27" fill="none" stroke="#d21f26" stroke-width="4" stroke-linecap="round" />
        <line x1="47" y1="104" x2="43" y2="124" stroke="#e0a52a" stroke-width="3.4" stroke-linecap="round" />
        <line x1="58" y1="104" x2="62" y2="124" stroke="#e0a52a" stroke-width="3.4" stroke-linecap="round" />
        <line x1="36" y1="125" x2="50" y2="125" stroke="#e0a52a" stroke-width="3" stroke-linecap="round" />
        <line x1="55" y1="125" x2="69" y2="125" stroke="#e0a52a" stroke-width="3" stroke-linecap="round" />
      </g>
      <!-- 竹节条（2~9 条）：一根竹子 = 绿身 + 中段竹节暗线 + 左侧高光 -->
      <g v-else>
        <g v-for="(s, i) in tiaoSticks" :key="i">
          <rect
            :x="s.x - s.w / 2" :y="s.y - s.h / 2" :width="s.w" :height="s.h"
            :rx="s.w / 2.06" :fill="s.c"
          />
          <!-- 左侧竖向高光：让圆柱有体积感（细到 1px 也还能看出「竹子」而不是「色块」） -->
          <line
            :x1="s.x - s.w * 0.22" :x2="s.x - s.w * 0.22"
            :y1="s.y - s.h / 2 + s.w * 0.55" :y2="s.y + s.h / 2 - s.w * 0.55"
            :stroke="s.hi" :stroke-width="Math.max(1.2, s.w * 0.16)" stroke-linecap="round"
          />
          <!-- 竹节：中段一道深色横线（真牌上就是这一道把一根竹子分成两节） -->
          <line
            :x1="s.x - s.w * 0.34" :x2="s.x + s.w * 0.34"
            :y1="s.y" :y2="s.y"
            :stroke="s.node" :stroke-width="Math.max(1.4, s.w * 0.2)" stroke-linecap="round"
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

/* 万：传统牌「伍萬」用大写数字「伍」，其余用一二三四六七八九 */
const NUM_CN = { 1: '一', 2: '二', 3: '三', 4: '四', 5: '伍', 6: '六', 7: '七', 8: '八', 9: '九' }

/* 高饱和三色（筒 / 条共用）：在深绿桌布上不发灰 */
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

/**
 * 竹节条：{x, y, h}（+ 可选 red）。
 * 行距一律取「(140 − 2×14) / 行数」，上下留白各 14 —— 旧版 3/5/7 条各行间距
 * 分别为 10 / 2 / 2，整张牌重心偏上，看着「分布不均匀」。
 * 规则：2/3/4/6/8/9 全绿；5 条中心一根红；7 条顶上一根红（传统牌面）。
 */
const TIAO_LAYOUT = {
  2: [{ x: 50, y: 42, h: 52 }, { x: 50, y: 100, h: 52 }],
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
  return rows.map((s) => {
    const w = Math.max(12, Math.min(17, s.h * 0.52))
    return {
      ...s,
      w,
      // 全部同一支绿：旧版两种几乎同色的绿交替，小尺寸下像脏斑
      c: s.red ? RED : GREEN,
      hi: s.red ? 'rgba(255,255,255,.42)' : 'rgba(255,255,255,.34)',
      node: s.red ? 'rgba(96,10,14,.42)' : 'rgba(4,66,34,.5)',
    }
  })
})
</script>

<style scoped>
.mj-face { display: block; width: 100%; height: 100%; }
/* 万：上「数字化」（蓝，本字号的 0.76 倍），下「萬」（红，略大）—— 真牌即上小下大 */
.f-num {
  font-size: 44px; font-weight: 700; fill: #14549e;
  text-anchor: middle; dominant-baseline: central;
  font-family: "Songti SC", "STSong", "SimSun", "Noto Serif CJK SC", "Source Han Serif SC", "HarmonyOS Sans SC", serif;
}
.f-wan {
  font-size: 58px; font-weight: 700; fill: #c62828;
  text-anchor: middle; dominant-baseline: central;
  font-family: "Songti SC", "STSong", "SimSun", "Noto Serif CJK SC", "Source Han Serif SC", "HarmonyOS Sans SC", serif;
}
</style>
