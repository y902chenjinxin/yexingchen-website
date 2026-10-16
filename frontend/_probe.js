/**
 * 棋牌渲染沙盒（本地开发用，不在任何路由里引用，也不进生产入口）
 *
 * 目的：把牌桌组件按 **APK 手机竖屏全屏** 的真实链路挂起来，用本地 Chromium 截图看效果。
 *   DOM/类名/全屏规则全部复刻 GamesView.vue（.gm-root.is-fsfit > .gm-fsfit >
 *   .gtv-viewstage.is-fs > .gtv-viewzoom.is-fs > 组件），缩放交给 usePinchZoom 本身，
 *   所以看到的就是线上同一套 CSS。
 *
 * 用法：npx vite --port 5199   然后打开 /_probe.html?g=mp（大富翁）/ ?g=mj（麻将）
 */
import { createApp, h, ref, onMounted, nextTick } from 'vue'
import { createPinia } from 'pinia'

/* 与 main.js 保持同一套样式（顺序一致），否则牌面会因缺 .gt-tile 基础样式而错位 */
import 'element-plus/dist/index.css'
import '@/assets/styles/main.css'
import '@/assets/styles/xiuxian-theme.css'
import '@/assets/styles/mobile-list.css'
import '@/assets/styles/mobile-ab-theme.css'
import '@/assets/styles/mobile-deink.css'
import '@/assets/styles/mobile-native-glass.css'
import '@/assets/styles/mobile-product.css'
import '@/assets/styles/desktop-theme-night.css'
import '@/assets/styles/desktop-theme-day.css'
import '@/assets/styles/desktop-product.css'
import '@/assets/styles/tool-mobile.css'
import '@/assets/styles/game-table.css'

import MahjongBoard from '@/components/games/MahjongBoard.vue'
import MonopolyBoard from '@/components/games/MonopolyBoard.vue'
import GuandanBoard from '@/components/games/GuandanBoard.vue'
import MahjongTileFace from '@/components/games/MahjongTileFace.vue'
import { usePinchZoom } from '@/composables/usePinchZoom'
import * as G from '@/utils/games/guandan.js'

const COMPONENTS = { mj: MahjongBoard, mp: MonopolyBoard, gd: GuandanBoard }
const params = new URLSearchParams(location.search)
const key = params.get('g') || 'mp'
const Comp = COMPONENTS[key] || MonopolyBoard
/* ?nofs=1 → **不进全屏等比缩放链路**，直接按「桌面/窄屏布局」挂载。
   手机自带浏览器走的是桌面版 viewport 1280，此时 `is-fsfit` 不生效、`.mp` 用的是
   自己那套 `min-height: 640px` —— 夜星截到的「横屏底部被遮挡」就是这个形态。
   没有这条分支，本地沙盒永远复现不出那个 bug。 */
const nofs = params.get('nofs') === '1'
/* ?g=gd&seat=1 → 用**在线投影**跑掼蛋，验证「视角跟着我的座位转」（本地单机永远坐 0 号位，
   不传 seat 是看不到旋转的）。座位名固定用「甲乙丙丁」，方便肉眼核对谁被摆到了哪一边。 */
const seatParam = params.get('seat')
const SEAT_CN = ['甲', '乙', '丙', '丁']
/* ?mode=solo → 用 **本地单人练习**（1 真人 + 3 AI）挂载。默认 'p4' 是「四家都是真人」的
   本地同屏形态（定缺/出牌都等人点），跑规则回归时必须换成 solo 才能让 AI 自己推进。 */
const MODE = params.get('mode') || 'p4'
/* 暴露组件实例给自动化脚本（本地沙盒专用，不进生产入口）：
   规则回归脚本据此直接读写组件状态、调用内部方法，把一局牌快进到想验的那个瞬间。 */
const compRef = ref(null)
if (typeof window !== 'undefined') window.__probeComp = compRef

function makeOnlineView(seat) {
  const dealt = G.deal(2)
  // 固定塞 6 张黑桃 3~8 进我的手牌 → 一定有同花顺可点（否则随机手牌常常没同花顺，
  // 「汇总到最左」这条就没法稳定取证）
  const hand = dealt[seat].slice()
  const extra = [3, 4, 5, 6, 7, 8].map((r, i) => ({ id: 9000 + i, suit: '♠', rank: r, joker: null }))
  hand.splice(0, 6, ...extra)
  return {
    phase: 'playing',
    turn: (seat + 1) % 4,
    level: 2,
    round_no: 2,
    team_levels: [3, 2],
    me: { hand, tribute_pending: false, tribute_options: [], return_options: [] },
    players: [0, 1, 2, 3].map((s) => ({
      seat: s, rank: 0, hand_count: dealt[s].length, team: G.TEAM_OF[s],
    })),
    target: null,
    last_play: null,
    history: [],
  }
}

/* ?g=mj&seat=1 → 麻将**在线投影**：按服务端 view() 的真实形状合成（绝对座位，
   不做任何旋转 —— 旋转必须由组件的 povSeat 投影完成），验证「下=自己、
   左=上家、右=下家」。对家固定塞一组碰、每家 3 张弃牌，肉眼可核对。
   ?dis=N → 每家 N 张弃牌（中盘复现弃牌区布局，v2.46.97 弃牌区重排用）。 */
function makeMjOnlineView(seat) {
  let id = 8000
  const T = (suit, rank) => ({ id: id++, suit, rank })
  const disN = Number(new URLSearchParams(location.search).get('dis') || 3)
  const DIS_POOL = [
    ['m', 9], ['p', 1], ['s', 7], ['m', 4], ['t', 2], ['p', 8], ['m', 1],
    ['s', 3], ['t', 7], ['p', 5], ['m', 6], ['s', 9], ['t', 5], ['p', 3],
    ['m', 2], ['s', 5], ['t', 8], ['p', 6], ['m', 8], ['s', 1], ['t', 4],
  ]
  const hand = [
    T('m', 1), T('m', 2), T('m', 3), T('m', 5), T('m', 6), T('m', 7), T('m', 9),
    T('p', 1), T('p', 2), T('p', 3), T('p', 7), T('p', 8), T('p', 9),
  ]
  const players = [0, 1, 2, 3].map((s) => ({
      seat: s,
      hand_count: 13,
      melds: s === (seat + 2) % 4 ? [{ type: 'pong', tile: { id: 770, suit: 'm', rank: 8 }, from: seat }] : [],
      discards: Array.from({ length: disN }, (_, i) => T(DIS_POOL[(s * 7 + i) % DIS_POOL.length][0], DIS_POOL[(s * 7 + i) % DIS_POOL.length][1])),
      missing: 's',
      is_turn: false,
      hu: false,
      hu_info: null,
      score: 0,
  }))
  /* v2.46.97：last_discard 必须引用真实弃牌（旧值 id 799 不在任何弃牌里，
     freshDiscardId 永远匹配不上 → is-last 常驻高亮在探针里验不了） */
  const lastSeat = (seat + 1) % 4
  const lastTile = players[lastSeat].discards[disN - 1]
  return {
    phase: 'playing',
    turn: (seat + 1) % 4,
    dealer: 0,
    round_no: 2,
    wall_left: 55,
    players,
    me: { seat, hand, melds: [], missing: 's', last_draw: null, options: [] },
    claim: null,
    last_discard: { seat: lastSeat, tile: lastTile },
    history: [],
    logs: ['1 号位打出 7条'],
    result: null,
  }
}

/* 牌面检视台（?g=tiles）：三门 × 1~9，上下两档尺寸（大牌 / 弃牌 mini），
   直接复用 .mj .gt-tile 的样式，所以看到的就是牌桌上的样子 */
function TileWall() {
  const size = new URLSearchParams(location.search).get('size') || 'big'
  const minis = size === 'mini'
  const suits = ['wan', 'tiao', 'tong', 'zi']
  const NAME = { wan: '万', tiao: '条', tong: '筒', zi: '字' }
  const tileW = minis ? 26 : 56
  const gap = minis ? 4 : 10
  return () =>
    h('div', { class: 'gt-shell mj', style: 'padding:12px;display:block;min-height:0' }, [
      h('div', { style: `display:grid;grid-template-columns:repeat(9,${tileW}px);gap:${gap}px` },
        suits.flatMap((s) => (s === 'zi' ? [1, 2, 3] : [1, 2, 3, 4, 5, 6, 7, 8, 9]).map((r) => h('div', {
          style: 'display:flex;flex-direction:column;gap:3px;align-items:center',
          key: s + r,
        }, [
          h('span', {
            class: ['gt-tile', `is-${s}`, minis ? 'mini' : ''],
            style: minis ? '' : 'width:56px;height:78px',
          }, [h(MahjongTileFace, { suit: s, rank: r })]),
          h('span', { style: 'font-size:10px;color:#cfe3da' }, NAME[s] + r),
        ])))),
    ])
}

/* ---- 从 GamesView.vue 抄来的全屏层规则（把 :deep() 展开成普通后代选择器） ---- */
const FS_CSS = `
.gtv-viewstage.is-fs {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  overflow: hidden; touch-action: none; overscroll-behavior: none;
}
.gtv-viewstage.is-fs .gt-landscape { height: 100%; }
.gtv-viewstage.is-fs .gt-shell { width: 100%; height: 100%; min-height: 0; min-width: 0; }
.gtv-viewstage.is-fs .gd-top,
.gtv-viewstage.is-fs .mj-top { display: none; }
.gtv-viewstage.is-fs .mp {
  grid-template-columns: minmax(0, 1fr) clamp(140px, 20%, 210px);
  grid-template-rows: minmax(0, 1fr);
  padding: 8px; gap: 8px;
  height: 100%;
  min-height: 0;
}
.gtv-viewstage.is-fs .mp-boardwrap { min-height: 0; }
/* 注意：这里**不能**再覆盖 .mp-board 的宽高，与 GamesView 保持一致
   （棋盘尺寸由组件的 --mp-w / --mp-h 决定） */
`
const st = document.createElement('style')
st.textContent = FS_CSS
document.head.appendChild(st)

const app = createApp({
  setup() {
    if (key === 'tiles') return () => h(TileWall())
    const stageRef = ref(null)
    const { style, bind, measure, reset } = usePinchZoom(stageRef, () => true)
    let tries = 0
    async function settle() {
      await nextTick()
      if (nofs) return          // 不走缩放链路，无需 bind / measure
      bind(stageRef.value)
      // 牌桌是异步组件，外壳挂上要几帧
      const timer = setInterval(() => {
        measure()
        if (++tries > 30) clearInterval(timer)
      }, 120)
      setTimeout(() => { measure(); reset() }, 400)
    }
    onMounted(settle)
    return () =>
      h('div', { id: 'probe-rot', class: 'gm-root is-big is-fill' + (nofs ? '' : ' is-fsfit') }, [
        nofs
          ? h('div', { class: 'gm-play' }, [
              h(Comp, { ref: compRef, bare: true, big: true, 'game-key': key, 'initial-mode': MODE }),
            ])
          : h('div', { class: 'gm-play is-fsfit' }, [
              h('div', { ref: stageRef, class: 'gtv-viewstage is-fs' }, [
                h('div', { class: 'gtv-viewzoom is-fs', style: style.value }, [
                  seatParam === null
                    ? h(Comp, { ref: compRef, bare: true, big: true, 'game-key': key, 'initial-mode': MODE })
                    : h(Comp, {
                        ref: compRef,
                        bare: true, big: true, 'game-key': key,
                        online: true,
                        'online-seat': Number(seatParam),
                        'online-view': key === 'mj'
                          ? makeMjOnlineView(Number(seatParam))
                          : makeOnlineView(Number(seatParam)),
                        'seat-names': SEAT_CN,
                      }),
                ]),
              ]),
            ]),
      ])
  },
})
app.use(createPinia())
app.mount('#probe')
