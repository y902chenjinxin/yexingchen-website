/* 3D 掼蛋「在线投影」渲染探针（本地，仅开发用）
 * 目的：不开 4 个账号也能验证——
 *   ① 我坐 2 号位时，手牌仍画在屏幕下方、其他三家按 povSeat 转到上/左/右
 *   ② 中央出牌区用 last_play 的牌（不是本地 AI 的）
 *   ③ 进贡面板能出现、提示文案与倒计时正常
 * 用法：vite dev 起来后打开 /_probe_online3d.html
 */
import { createApp, h, reactive } from 'vue'
import '@/assets/styles/games3d.css'
import Board from '@/components/games3d/Guandan3DBoard.vue'

const SUITS = ['♠', '♥', '♣', '♦']
let uid = 1
const card = (rank, suit) => ({ id: uid++, rank, suit })
const hand = []
for (const r of [14, 13, 12, 11, 10, 9, 9, 8, 7, 5]) hand.push(card(r, SUITS[r % 4]))

const lastCards = [card(8, '♥'), card(8, '♠')]

const view = reactive({
  phase: 'playing',
  turn: 2,
  level: 2,
  level_text: '2',
  team_levels: [2, 3],
  round_no: 2,
  players: [
    { seat: 0, hand_count: 12, finished: false, rank: 0, is_turn: false, team: 0 },
    { seat: 1, hand_count: 9, finished: false, rank: 0, is_turn: false, team: 1 },
    { seat: 2, hand_count: 10, finished: false, rank: 0, is_turn: true, team: 0 },
    { seat: 3, hand_count: 8, finished: false, rank: 0, is_turn: false, team: 1 },
  ],
  me: { seat: 2, hand, tribute_pending: false, return_pending: false },
  target: { seat: 1, cards: lastCards, pattern: { type: 'pair', len: 2, key: 802, bomb_level: 0 } },
  last_play: { seat: 1, cards: lastCards, pattern: { type: 'pair', len: 2, key: 802, bomb_level: 0 } },
  pass_count: 0,
  history: [],
  tribute: null,
  result: null,
})

const props = reactive({
  online: true,
  onlineView: view,
  onlineSeat: 2,
  showTopbar: false,
  seatNames: ['阿明', '小刘', '夜星', '阿华'],
  deadlineAt: new Date(Date.now() + 45000).toISOString(),
})

window.__probe = {
  setGift(kind) {
    // kind: 'tribute' | 'return' | ''
    if (kind === 'tribute') {
      view.phase = 'tribute'
      view.me = { seat: 2, hand, tribute_pending: true, tribute_to: 1, tribute_options: hand.slice(0, 6), return_pending: false }
    } else if (kind === 'return') {
      view.phase = 'return'
      view.me = { seat: 2, hand, tribute_pending: false, return_pending: true, return_options: hand.slice(2) }
    } else {
      view.phase = 'playing'
      view.me = { seat: 2, hand, tribute_pending: false, return_pending: false }
    }
  },
}

createApp({ render: () => h(Board, props) }).mount('#probe')
