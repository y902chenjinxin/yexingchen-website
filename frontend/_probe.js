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
/* ?g=gd&seat=1 → 用**在线投影**跑掼蛋，验证「视角跟着我的座位转」（本地单机永远坐 0 号位，
   不传 seat 是看不到旋转的）。座位名固定用「甲乙丙丁」，方便肉眼核对谁被摆到了哪一边。 */
const seatParam = params.get('seat')
const SEAT_CN = ['甲', '乙', '丙', '丁']

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

/* 牌面检视台（?g=tiles）：三门 × 1~9，上下两档尺寸（大牌 / 弃牌 mini），
   直接复用 .mj .gt-tile 的样式，所以看到的就是牌桌上的样子 */
function TileWall() {
  const size = new URLSearchParams(location.search).get('size') || 'big'
  const minis = size === 'mini'
  const suits = ['wan', 'tiao', 'tong']
  const NAME = { wan: '万', tiao: '条', tong: '筒' }
  const tileW = minis ? 26 : 56
  const gap = minis ? 4 : 10
  return () =>
    h('div', { class: 'gt-shell mj', style: 'padding:12px;display:block;min-height:0' }, [
      h('div', { style: `display:grid;grid-template-columns:repeat(9,${tileW}px);gap:${gap}px` },
        suits.flatMap((s) => [1, 2, 3, 4, 5, 6, 7, 8, 9].map((r) => h('div', {
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
   （棋盘尺寸由组件的 --mp-size 决定） */
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
      h('div', { id: 'probe-rot', class: 'gm-root is-big is-fill is-fsfit' }, [
        h('div', { class: 'gm-play is-fsfit' }, [
          h('div', { ref: stageRef, class: 'gtv-viewstage is-fs' }, [
            h('div', { class: 'gtv-viewzoom is-fs', style: style.value }, [
              seatParam === null
                ? h(Comp, { bare: true, big: true, 'game-key': key, 'initial-mode': 'p4' })
                : h(Comp, {
                    bare: true, big: true, 'game-key': key,
                    online: true,
                    'online-seat': Number(seatParam),
                    'online-view': makeOnlineView(Number(seatParam)),
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
