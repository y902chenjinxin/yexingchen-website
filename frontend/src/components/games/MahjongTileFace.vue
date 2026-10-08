<template>
  <!--
    麻将牌面 · 纯矢量

    设计依据（对照真实牌面；v2.46.8 按中文维基「麻将牌 · 條子」重排条子的排列与配色）：
      · 万 —— **顶部蓝色的是中文数字，底部红色的是「萬」字**；
        且「大多数麻将牌，伍萬都采用大写数字「伍」」。所以本版：数字化（一…九，五用伍）
        置于上方、蓝色；「萬」置于下方、红色，字身略大于数字化（约 1.3 : 1，真牌即如此）。
      · 条 —— **2/3/4/6/8 条只有绿色；5 条中心一根、7 条最顶一根、9 条中间一「列」（不是行）为红**；
        1 条是幺鸡。排列：3 条上一下二、6 条上三下三、7 条上 1 中 3 下 3、9 条 3×3；
        **8 条最特别**：每组是「左右两根竖条 + 中间两根斜条拼成尖」—— 上组尖朝上（「∧」＝倒 M／W）、
        下组尖朝下（「∨」＝M），故俗称「坦克」「BMW」「脚开开」。
      · 筒 —— 见 TONG_LAYOUT（红 / 墨绿 / 蓝三色传统排布，唯四筒八筒不着红）。
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
      <!-- 竹节条（2~9 条）：一根竹子 = 绿身 + 中段竹节暗线 + 左侧高光。
           八条的「斜条」靠 rot 绕自身中心旋转（节点线随组一起转，仍是垂直于竹身）。 -->
      <g v-else>
        <g
          v-for="(s, i) in tiaoSticks" :key="i"
          :transform="s.rot ? `rotate(${s.rot} ${s.x} ${s.y})` : undefined"
        >
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

    <!-- ===== 字（箭牌）：红中 / 发财 / 白板（v2.46.15 新增，样式对照传统牌面） =====
         · 红中 —— 大红「中」字居中；
         · 发财 —— 墨绿「發」（繁体，真牌即繁体）；
         · 白板 —— 传统是「空板」：蓝色矩形框（多层框最常见），中间什么都不印。 -->
    <template v-else-if="suit === 'zi'">
      <text v-if="rank === 1" class="f-zhong" x="50" y="72">中</text>
      <text v-else-if="rank === 2" class="f-fa" x="50" y="72">發</text>
      <g v-else>
        <rect x="24" y="31" width="52" height="78" rx="4" fill="none" stroke="#1657c9" stroke-width="5" />
        <rect x="35" y="42" width="30" height="56" rx="2" fill="none" stroke="#1657c9" stroke-width="2.5" />
      </g>
    </template>
  </svg>
</template>

<script setup>
/** 麻将牌面（矢量）。只负责画，不管尺寸与边框 —— 外层 .gt-tile 决定尺寸。 */
import { computed } from 'vue'

const props = defineProps({
  suit: { type: String, required: true },   // wan | tiao | tong | zi
  rank: { type: Number, required: true },   // 1..9；zi 只用 1..3（中/發/白）
})

/* 万：传统牌「伍萬」用大写数字「伍」，其余用一二三四六七八九 */
const NUM_CN = { 1: '一', 2: '二', 3: '三', 4: '四', 5: '伍', 6: '六', 7: '七', 8: '八', 9: '九' }

/* 高饱和三色（筒 / 条共用）：在深绿桌布上不发灰。
   条用的绿单独取「竹青」#0f9152 —— 旧值 #0b8a4d 偏墨，缩到手机弃牌尺寸（16×22）时
   整张牌发暗，看着像脏绿块（夜星：「条牌的颜色不对劲」）。 */
const BLUE = '#1657c9'
const GREEN = '#0f9152'
const RED = '#d42a2a'

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
 *
 * 【v2.46.8 按传统牌面重排】依据中文维基「麻将牌 · 條子」：
 *   · 排列 —— 二條／四條／五條／九條与同数字的**筒子相同**（即 1×2 / 2×2 / 2×2+心 / 3×3）；
 *     三條上一下二；六條上三下三；七條分三行（上 1、中 3、下 3）；
 *     **八條**：每组 4 根 = 左右 2 根「竖条」+ 中间 2 根「斜条」拼成一个尖，
 *     上组尖朝上（「∧」）、下组尖朝下（「∨」）—— 即维基所谓「顶四倒 M 形、底四 M 形」，
 *     俗称「坦克 / BMW / 脚开开」。（v2.46.9 修正：v2.46.8 版把 8 根全画成竖条、
 *     只做「内外上下错位」，远看像四个散块，与真牌的斜条尖形不符。）
 *   · 配色 —— **二、三、四、六、八条只有绿色**；五條中心那根、七條最顶那根、
 *     **九條中间那一列（直行，三根）** 为红色。
 *   · 一根竹子 = 绿身 + 左侧竖向高光 + 中段竹节暗线；斜条由 `rot` 绕自身中心旋转。
 */
const TIAO_LAYOUT = {
  2: [{ x: 50, y: 42, h: 52 }, { x: 50, y: 100, h: 52 }],
  3: [
    { x: 50, y: 34, h: 38 },
    { x: 26, y: 104, h: 38 }, { x: 74, y: 104, h: 38 },
  ],
  4: [
    { x: 30, y: 40, h: 46 }, { x: 70, y: 40, h: 46 },
    { x: 30, y: 104, h: 46 }, { x: 70, y: 104, h: 46 },
  ],
  5: [
    { x: 30, y: 36, h: 32 }, { x: 70, y: 36, h: 32 },
    { x: 50, y: 70, h: 32, red: true },
    { x: 30, y: 104, h: 32 }, { x: 70, y: 104, h: 32 },
  ],
  // 六條：上三下三（3 列 × 2 行）—— 旧版是 2 列 × 3 行，看着像「八条」
  6: [
    { x: 26, y: 38, h: 46 }, { x: 50, y: 38, h: 46 }, { x: 74, y: 38, h: 46 },
    { x: 26, y: 104, h: 46 }, { x: 50, y: 104, h: 46 }, { x: 74, y: 104, h: 46 },
  ],
  // 七條：上 1、中 3、下 3（旧版是 1 + 三个「两列行」，重心散）
  7: [
    { x: 50, y: 28, h: 24, red: true },
    { x: 26, y: 72, h: 24 }, { x: 50, y: 72, h: 24 }, { x: 74, y: 72, h: 24 },
    { x: 26, y: 114, h: 24 }, { x: 50, y: 114, h: 24 }, { x: 74, y: 114, h: 24 },
  ],
  // 八條：每组 4 根 = 左右 2 根**通高竖条** + 中间 2 根**短斜条**拼成一个尖。
  //   上组「倒 M（W）」：斜条在上方交汇，尖朝上 —— 左斜条 rotate(+32)、右斜条 rotate(-32)；
  //   下组「M」：斜条在下方交汇，尖朝下 —— 左右互换（左 rotate(-32)、右 rotate(+32)）。
  //   比例取自官方牌面（Wikimedia「0308八條.svg」，实测）：竖条占**整组高度**，
  //   斜条约 32° 张开、只占**上 2/3**，尖端落在中轴、末端伸到竖条内侧附近。
  8: [
    // 上组（尖朝上）
    { x: 19, y: 42, h: 52, w: 13 }, { x: 81, y: 42, h: 52, w: 13 },
    { x: 41.65, y: 39.1, h: 31.5, w: 12, rot: 32 }, { x: 58.35, y: 39.1, h: 31.5, w: 12, rot: -32 },
    // 下组（尖朝下，镜像）
    { x: 19, y: 98, h: 52, w: 13 }, { x: 81, y: 98, h: 52, w: 13 },
    { x: 41.65, y: 100.9, h: 31.5, w: 12, rot: -32 }, { x: 58.35, y: 100.9, h: 31.5, w: 12, rot: 32 },
  ],
  // 九條：3×3，**中间那一列**（三根）为红
  9: [
    { x: 26, y: 34, h: 30 }, { x: 50, y: 34, h: 30, red: true }, { x: 74, y: 34, h: 30 },
    { x: 26, y: 72, h: 30 }, { x: 50, y: 72, h: 30, red: true }, { x: 74, y: 72, h: 30 },
    { x: 26, y: 110, h: 30 }, { x: 50, y: 110, h: 30, red: true }, { x: 74, y: 110, h: 30 },
  ],
}

/** 各条数的「竹子粗细」系数（默认 0.52 = 竹宽约等于半根长）。
 *  6/7 两张要横向塞 3 列，按默认系数会连成一片（间隙只剩 4~5px），单独收细一档。
 *  8 条直接写死 `w`（竖条 13 / 斜条 12.5）—— 它要同时避开竖条的边和斜条的旋转外扩，
 *  用系数算不出两组都合适的值。 */
const TIAO_W_FACTOR = { 6: 0.46, 7: 0.46 }

const tiaoSticks = computed(() => {
  const rows = TIAO_LAYOUT[props.rank] || TIAO_LAYOUT[2]
  const f = TIAO_W_FACTOR[props.rank] || 0.52
  return rows.map((s) => {
    const w = s.w || Math.max(10, Math.min(17, s.h * f))
    return {
      ...s,
      w,
      c: s.red ? RED : GREEN,
      hi: s.red ? 'rgba(255,255,255,.46)' : 'rgba(255,255,255,.4)',
      node: s.red ? 'rgba(104,10,14,.46)' : 'rgba(4,72,38,.52)',
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
/* 字牌：红中（大红）/ 发财（墨绿「發」）—— 与萬同族衬线，白板是纯框不走字体 */
.f-zhong {
  font-size: 64px; font-weight: 700; fill: #c62828;
  text-anchor: middle; dominant-baseline: central;
  font-family: "Songti SC", "STSong", "SimSun", "Noto Serif CJK SC", "Source Han Serif SC", "HarmonyOS Sans SC", serif;
}
.f-fa {
  font-size: 56px; font-weight: 700; fill: #0f9152;
  text-anchor: middle; dominant-baseline: central;
  font-family: "Songti SC", "STSong", "SimSun", "Noto Serif CJK SC", "Source Han Serif SC", "HarmonyOS Sans SC", serif;
}
</style>
