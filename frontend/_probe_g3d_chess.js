/* 3D 棋类本地渲染探针（v2.46.277）
 *
 * 目的：3D 透视下「棋盘投影多大、有没有被顶栏压住、棋子字能不能看清」
 * 这些只能看真实渲染，靠读代码推不出来。
 *
 * 用法：/?g=xiangqi | /?g=gomoku
 * 暴露 window.__probe.{ ref, setup, describe } 供 playwright 调用。
 */
import { createApp, h, ref, onMounted } from 'vue'
import { createPinia } from 'pinia'
import Xiangqi3DBoard from '@/components/games3d/Xiangqi3DBoard.vue'
import Gomoku3DBoard from '@/components/games3d/Gomoku3DBoard.vue'
import '@/assets/styles/games3d.css'

const qs = new URLSearchParams(location.search)
const which = qs.get('g') === 'gomoku' ? 'gomoku' : 'xiangqi'
/** 在线模式：没有登录态时后端会 401，正好验证「邀请面板」的渲染与布局 */
const onlineMode = qs.get('online') === '1'
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
        /** 测 AI：真实走一步，量「耗时」和「期间主线程还画了多少帧」。
         *  主线程被同步搜索占住时帧数会掉到个位数；Worker 正常 40+ 帧。
         *  象棋从「选中马」之后的落点开始走，否则点的只是选子不算一手。 */
        async measureAI() {
          const isG = which === 'gomoku'
          const sel = isG ? '.gk3-stone' : '.xq3-piece'
          const before = document.querySelectorAll(sel).length
          const target = document.querySelector(isG ? '.gk3-hit' : '.xq3-hit')
          if (!target) return { error: 'no target to click' }
          const t0 = performance.now()
          let frames = 0
          let run = true
          const tick = () => { if (run) { frames++; requestAnimationFrame(tick) } }
          requestAnimationFrame(tick)
          target.click()
          await new Promise(r => setTimeout(r, 100))   // 让「思考中」先亮起来
          let done = false
          while (performance.now() - t0 < 8000) {
            await new Promise(r => setTimeout(r, 40))
            if (isG) {
              if (document.querySelectorAll(sel).length >= before + 2) { done = true; break }
            } else {
              const t = document.querySelector('.g3d-title i')?.textContent || ''
              if (t.includes('轮到') && !t.includes('思考')) { done = true; break }
            }
          }
          run = false
          return { ms: Math.round(performance.now() - t0), frames, done }
        },
        /** 切到困难档：直接调组件的 setDiff（点按钮会循环，很难点准） */
        setHard() {
          const vm = boardRef.value
          if (!vm?.setDiff) return 'no setDiff'
          vm.setDiff('hard')
          return vm.getDiff ? vm.getDiff() : 'hard'
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
    return () => h(comp, { ref: boardRef, showTopbar: true, online: onlineMode })
  },
}

/* useGameRoom 内部要用 auth store（拿当前用户 id），探针必须装 pinia，
   否则组件一挂载就报 getActivePinia —— 真实应用在 main.js 里已经 use 过了 */
createApp(App).use(createPinia()).mount(document.getElementById('probe'))
