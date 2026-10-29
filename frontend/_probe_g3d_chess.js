/* 3D 棋类本地渲染探针（v2.46.277）
 *
 * 目的：3D 透视下「棋盘投影多大、有没有被顶栏压住、棋子字能不能看清」
 * 这些只能看真实渲染，靠读代码推不出来。
 *
 * 用法：/?g=xiangqi | /?g=gomoku
 * 暴露 window.__probe.{ ref, setup, describe } 供 playwright 调用。
 */
import { createApp, h, ref, onMounted } from 'vue'
import Xiangqi3DBoard from '@/components/games3d/Xiangqi3DBoard.vue'
import Gomoku3DBoard from '@/components/games3d/Gomoku3DBoard.vue'
import '@/assets/styles/games3d.css'

const which = new URLSearchParams(location.search).get('g') === 'gomoku' ? 'gomoku' : 'xiangqi'
const comp = which === 'gomoku' ? Gomoku3DBoard : Xiangqi3DBoard
const boardRef = ref(null)

/* 五子棋摆一个中盘：黑 5 子斜线 + 白 4 子交错，都靠中心，能看清重叠关系 */
const GOMOKU_SEQ = [
  [7, 7, 1], [8, 8, 2], [7, 8, 1], [8, 7, 2], [6, 6, 1],
  [8, 9, 2], [6, 7, 1], [9, 6, 2], [5, 8, 1],
]

const App = {
  setup() {
    onMounted(() => {
      window.__probe = {
        game: which,
        ref: boardRef,
        setup() {
          const vm = boardRef.value
          if (!vm) return 'no ref'
          if (which === 'gomoku') {
            vm.restart()
            for (const [x, y, c] of GOMOKU_SEQ) vm.drop(y * 15 + x, c)
            return `摆 ${GOMOKU_SEQ.length} 手`
          }
          // 象棋：初始局面 + 红炮二平五（走一步，验证选中/落点渲染）
          vm.restart()
          vm.doMove(7 * 9 + 1, 7 * 9 + 4)
          return '红炮二平五'
        },
        /** 选中一个子，看落点提示渲染 */
        /** 点一个红子（用真实 DOM 点击，命中判断与玩家一致） */
        tapRed() {
          const vm = boardRef.value
          if (!vm) return 'no ref'
          if (which === 'xiangqi') {
            // 红马在 (7,9) → 下标 9*9+7 = 88
            const el = [...document.querySelectorAll('.xq3-piece')].find(p => p.__vueParentComponent)
            void el
            const hit = document.querySelectorAll('.xq3-piece')[88]
            void hit
            const all = [...document.querySelectorAll('.xq3-piece')]
            const target = all.find(p => p.textContent.trim() === '马' && p.classList.contains('red'))
            if (target) { target.click(); return 'clicked 马' }
            return 'not found'
          }
          return 'n/a'
        },
        /** 真实点击一个命中层，验证 3D 下的可点性 */
        tapHit() {
          const sel = which === 'gomoku' ? '.gk3-hit' : '.xq3-hit'
          const el = document.querySelector(sel)
          if (!el) return 'no hit'
          const before = document.querySelectorAll(which === 'gomoku' ? '.gk3-stone' : '.xq3-piece').length
          el.click()
          const after = document.querySelectorAll(which === 'gomoku' ? '.gk3-stone' : '.xq3-piece').length
          return `点击 ${sel}：${before} → ${after}`
        },
        describe() {
          const q = s => document.querySelector(s)
          const rect = el => {
            if (!el) return null
            const r = el.getBoundingClientRect()
            return { top: Math.round(r.top), left: Math.round(r.left), w: Math.round(r.width), h: Math.round(r.height), bottom: Math.round(r.bottom) }
          }
          const slab = q(which === 'gomoku' ? '.gk3-top' : '.xq3-top')   // 量顶面：slab 只是定位锚点（0×0）
          const topbar = q('.g3d-topbar')
          const self = q('.gt3-seat.gt3-self')
          const pieces = [...document.querySelectorAll(which === 'gomoku' ? '.gk3-stone' : '.xq3-piece')]
          const rects = pieces.map(p => p.getBoundingClientRect())
          return {
            game: which,
            viewport: { w: innerWidth, h: innerHeight },
            stage: rect(q('.g3d-stage')),
            slab: rect(slab),
            topbar: rect(topbar),
            selfHud: rect(self),
            pieceCount: pieces.length,
            pieceBox: rects.length
              ? {
                  minTop: Math.round(Math.min(...rects.map(r => r.top))),
                  maxBottom: Math.round(Math.max(...rects.map(r => r.bottom))),
                  avgW: Math.round(rects.reduce((s, r) => s + r.width, 0) / rects.length),
                }
              : null,
            hitCount: document.querySelectorAll(which === 'gomoku' ? '.gk3-hit' : '.xq3-hit').length,
            dotCount: document.querySelectorAll('.xq3-dot').length,
            winRing: document.querySelectorAll('.is-win').length,
            texts: [...document.querySelectorAll(which === 'gomoku' ? '.gk3-star' : '.xq3-river')].length,
          }
        },
      }
    })
    return () => h(comp, { ref: boardRef, showTopbar: true })
  },
}

createApp(App).mount(document.getElementById('probe'))
