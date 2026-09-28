/**
 * useGameRoom —— 在线对战的房间会话（轮询同步）。
 *
 * 用法（棋盘组件内）：
 *   const g = useGameRoom('gomoku', { onRemoteMove, onStatus })
 *   g.createInvite(memberUserId)     // 邀请家人 → waiting
 *   g.join(roomId)                   // 接受邀请 / 恢复对局（重放全部事件）
 *   g.send({ idx: 112 })             // 我的落子（服务端校验轮次与占位）
 *   g.state.my_turn                  // 是否轮到我（轮询驱动）
 *
 * 事件流：服务端只存动作（moves），棋盘状态由客户端重放；
 * 服务端权威项 = 轮次 / 格子占用 / 五子棋胜负。
 */
import { ref, computed, onBeforeUnmount } from 'vue'
import { gameRoomsApi } from '@/api/gameRooms'
import { useAuthStore } from '@/stores/auth'

export function useGameRoom(game, { onRemoteMove, onStatus } = {}) {
  const auth = useAuthStore()
  const room = ref(null)          // 房间元信息（status/winner/双方名字…）
  const moves = ref([])           // 全量事件（重放用）
  const lastSeq = ref(0)
  const error = ref('')
  const joining = ref(false)
  let pollTimer = null
  let seenMoveSeq = 0             // 已交给棋盘的最大 seq（onRemoteMove 只回调一次）

  const myUserId = computed(() => Number(auth.user?.id) || 0)
  const status = computed(() => room.value?.status || '')
  const mySeat = computed(() => room.value?.my_seat || 'black')
  const myTurn = computed(() => !!room.value?.my_turn)
  const opponentName = computed(() =>
    room.value ? (room.value.owner_id === myUserId.value ? room.value.invitee_name : room.value.owner_name) : '')

  function stopPoll() { clearInterval(pollTimer); pollTimer = null }
  function startPoll(interval = 1600) {
    stopPoll()
    pollTimer = setInterval(poll, interval)
  }

  async function poll() {
    if (!room.value?.id) return
    try {
      const res = await gameRoomsApi.state(room.value.id, lastSeq.value)
      const d = res?.data || {}
      room.value = { ...room.value, ...d, moves: undefined }
      const fresh = d.moves || []
      moves.value.push(...fresh)
      for (const m of fresh) {
        if (m.seq > seenMoveSeq && m.user_id !== myUserId.value) {
          seenMoveSeq = m.seq
          onRemoteMove?.(m.action, m.user_id)
        } else if (m.seq > seenMoveSeq) {
          seenMoveSeq = m.seq   // 自己的动作（乐观应用过）也推进游标
        }
      }
      onStatus?.({ status: d.status, winner_id: d.winner_id, my_turn: d.my_turn })
    } catch { /* 轮询失败静默，下轮再试 */ }
  }

  async function createInvite(inviteeUserId, first = 'me') {
    error.value = ''
    const res = await gameRoomsApi.create({ game, invitee_user_id: inviteeUserId, first })
    room.value = res?.data || null
    moves.value = []
    lastSeq.value = 0
    seenMoveSeq = 0
    startPoll()
    return room.value
  }

  /** 接受邀请（受邀方）或恢复/进入已有房间 */
  async function join(roomId, { autoAccept = false } = {}) {
    joining.value = true
    error.value = ''
    try {
      if (autoAccept) {
        try { await gameRoomsApi.accept(roomId) } catch { /* 可能已接受过 */ }
      }
      const res = await gameRoomsApi.state(roomId, 0)
      const d = res?.data || {}
      room.value = { ...d, moves: undefined }
      moves.value = d.moves || []
      lastSeq.value = d.last_seq || 0
      seenMoveSeq = d.last_seq || 0
      // 重放全部事件（对方与自己的都重放，保证棋盘与服务器一致）
      for (const m of moves.value) onRemoteMove?.(m.action, m.user_id)
      startPoll()
      return room.value
    } finally {
      joining.value = false
    }
  }

  async function send(action) {
    if (!room.value?.id) return
    const res = await gameRoomsApi.move(room.value.id, action)
    lastSeq.value = Math.max(lastSeq.value, res?.data?.seq || 0)
    seenMoveSeq = Math.max(seenMoveSeq, res?.data?.seq || 0)
    if (res?.data?.status === 'finished') {
      room.value.status = 'finished'
      room.value.winner_id = res?.data?.winner_id
      onStatus?.({ status: 'finished', winner_id: res?.data?.winner_id })
    }
  }

  async function finish(winnerId) {
    if (!room.value?.id) return
    const res = await gameRoomsApi.finish(room.value.id, winnerId)
    if (res?.data) { room.value = { ...room.value, ...res.data, moves: undefined } }
  }

  async function decline(roomId) { await gameRoomsApi.decline(roomId) }
  async function cancel() { if (room.value?.id) await gameRoomsApi.decline(room.value.id); reset() }
  async function resign() { if (room.value?.id) await gameRoomsApi.resign(room.value.id); stopPoll() }

  function reset() {
    stopPoll()
    room.value = null
    moves.value = []
    lastSeq.value = 0
    seenMoveSeq = 0
  }

  onBeforeUnmount(stopPoll)
  return {
    room, moves, status, mySeat, myTurn, myUserId, opponentName, error, joining,
    createInvite, join, send, finish, decline, cancel, resign,
    startPoll, stopPoll, reset,
  }
}
