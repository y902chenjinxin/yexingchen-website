/* 3D 麻将「在线投影」渲染探针（本地，仅开发用）
 * 验证：我坐 1 号位时手牌在下方、其余三家按 povSeat 转；牌河/副露按座位摆；
 *      服务端 options 决定底部按钮（discard 只显示出牌；pong/kong/pass 出反应键）。
 * 用法：vite dev 起后打开 /_probe_online3d_mj.html
 */
import { createApp, h, reactive } from 'vue'
import '@/assets/styles/games3d.css'
import Board from '@/components/games3d/Mahjong3DBoard.vue'

const SUITS = ['m', 's', 'p']
let uid = 1
const tile = (suit, rank) => ({ id: uid++, suit, rank })

const hand = [tile('m', 1), tile('m', 1), tile('m', 2), tile('s', 3), tile('s', 4),
  tile('s', 5), tile('p', 7), tile('p', 7), tile('p', 9), tile('m', 5), tile('m', 6),
  tile('s', 9), tile('z', 1)]

const view = reactive({
  phase: 'playing',
  turn: 1,
  players: [
    { seat: 0, hand_count: 13, melds: [], discards: [tile('m', 9), tile('p', 2)], hu: false, ting: false, score: 0 },
    { seat: 1, hand_count: 13, melds: [], discards: [tile('s', 1)], hu: false, ting: false, score: 0 },
    { seat: 2, hand_count: 13, melds: [{ type: 'pong', tile: tile('p', 5) }], discards: [tile('m', 3)], hu: false, ting: true, score: 0 },
    { seat: 3, hand_count: 13, melds: [], discards: [tile('z', 2), tile('z', 3)], hu: false, ting: false, score: 0 },
  ],
  me: { seat: 1, hand, melds: [], last_draw: { id: 999, suit: 'm', rank: 8 }, options: ['discard'] },
  last_discard: { seat: 3, tile: { id: 998, suit: 'z', rank: 3 } },
  result: null,
})

const props = reactive({
  online: true,
  onlineView: view,
  onlineSeat: 1,
  showTopbar: false,
  seatNames: ['阿明', '夜星', '小刘', '阿华'],
})

window.__probe = {
  react(kinds) {
    view.me = { ...view.me, options: kinds }
  },
}

createApp({ render: () => h(Board, props) }).mount('#probe')
