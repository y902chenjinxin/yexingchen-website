/**
 * useGameTable —— 牌类在线对局（服务端权威）的房间会话。
 *
 * 用法（等待房 / 牌桌组件内）：
 *   const t = useGameTable()
 *   await t.create('guandan', { inviteeUserIds: [2], baseStake: 100, seatCount: 4 })
 *   await t.join(roomId)              // 受邀方入座 / 重进夺回
 *   t.room / t.view                   // 房间元信息 / 服务端投影（自己的手牌 + 公开信息）
 *   t.mySeat / t.isMyTurn / t.status
 *   await t.act({ type: 'play', card_ids: [1,2] })   // 出牌
 *   await t.start() / t.rematch() / t.leave()
 *
 * 与棋类的 useGameRoom 区别：牌类是**服务端权威**，前端不做事件重放，
 * 每轮直接把 `GET /rooms/{id}` 的投影覆盖到 `view`；动作由服务端校验后回吐新投影。
 */
import { ref, computed, onBeforeUnmount } from 'vue'
import { gameTablesApi, beaconTableLeave } from '@/api/gameTables'
import { useAuthStore } from '@/stores/auth'

const POLL_MS = 1600
const HEARTBEAT_MS = 5000

export function useGameTable() {
  const auth = useAuthStore()
  const room = ref(null)
  const view = ref(null)
  const error = ref('')
  const busy = ref(false)
  const loading = ref(false)

  let pollTimer = null
  let beatTimer = null
  let inFlight = false

  const myUserId = computed(() => Number(auth.user?.id) || 0)
  const status = computed(() => room.value?.status || '')
  const gameKey = computed(() => room.value?.game_key || '')
  const mySeat = computed(() => (room.value?.my_seat ?? null))
  const seats = computed(() => room.value?.seats || [])
  const isHost = computed(() => !!room.value?.is_host)
  const phase = computed(() => view.value?.phase || '')
  const turn = computed(() => (view.value?.turn ?? null))
  const isMyTurn = computed(() => mySeat.value !== null && turn.value === mySeat.value)
  const finished = computed(() => status.value === 'finished' || phase.value === 'finished')

  function apply(payload) {
    if (!payload) return
    room.value = payload
    if ('view' in payload) view.value = payload.view
  }

  function stopPoll() { clearInterval(pollTimer); pollTimer = null }
  function stopBeat() { clearInterval(beatTimer); beatTimer = null }

  async function refresh() {
    if (!room.value?.id || inFlight) return
    inFlight = true
    try {
      const res = await gameTablesApi.state(room.value.id)
      apply(res?.data)
    } catch { /* 轮询失败静默，下轮再试 */ } finally { inFlight = false }
  }

  function startPoll(interval = POLL_MS) {
    stopPoll()
    pollTimer = setInterval(refresh, interval)
  }

  function startBeat() {
    stopBeat()
    beatTimer = setInterval(() => {
      if (room.value?.id) gameTablesApi.heartbeat(room.value.id).catch(() => {})
    }, HEARTBEAT_MS)
  }

  async function create(gameKeyStr, { inviteeUserIds = [], baseStake = 100, seatCount = null, config = {} } = {}) {
    busy.value = true
    error.value = ''
    try {
      const res = await gameTablesApi.create({
        game_key: gameKeyStr,
        invitee_user_ids: inviteeUserIds,
        base_stake: baseStake,
        seat_count: seatCount,
        config,
      })
      apply(res?.data)
      startPoll()
      startBeat()
      return room.value
    } finally { busy.value = false }
  }

  async function join(roomId, { autoJoin = false } = {}) {
    loading.value = true
    error.value = ''
    try {
      if (autoJoin) { try { await gameTablesApi.join(roomId) } catch { /* 可能已入座 */ } }
      const res = await gameTablesApi.state(roomId)
      apply(res?.data)
      startPoll()
      startBeat()
      return room.value
    } finally { loading.value = false }
  }

  async function seatOp(data) {
    if (!room.value?.id) return
    const res = await gameTablesApi.seat(room.value.id, data)
    apply(res?.data)
  }

  async function start() {
    if (!room.value?.id) return
    const res = await gameTablesApi.start(room.value.id)
    apply(res?.data)
  }

  async function act(action) {
    if (!room.value?.id) return
    busy.value = true
    try {
      const res = await gameTablesApi.act(room.value.id, action)
      apply(res?.data)
      return room.value
    } finally { busy.value = false }
  }

  async function rematch() {
    if (!room.value?.id) return
    const res = await gameTablesApi.rematch(room.value.id)
    apply(res?.data)
  }

  async function leave() {
    if (room.value?.id) { try { await gameTablesApi.leave(room.value.id) } catch { /* 忽略 */ } }
    stopPoll(); stopBeat()
  }

  /** 解散牌桌：不判输赢，已开局则退还底注（任何在座家人都可发起） */
  async function dissolve() {
    if (room.value?.id) {
      const res = await gameTablesApi.dissolve(room.value.id)
      apply(res?.data)
    }
    stopPoll(); stopBeat()
  }

  async function decline(roomId) {
    try { await gameTablesApi.decline(roomId || room.value?.id) } catch { /* 忽略 */ }
    stopPoll(); stopBeat()
  }

  function reset() {
    stopPoll(); stopBeat()
    room.value = null
    view.value = null
  }

  /** 页面关闭 / 切走兜底：只转托管 / 刷心跳，**不结束牌局**（soft=1） */
  function leaveOnUnload() {
    if (room.value?.id && ['waiting', 'playing'].includes(room.value.status)) {
      beaconTableLeave(room.value.id)
    }
  }

  onBeforeUnmount(() => { stopPoll(); stopBeat() })

  return {
    room, view, error, busy, loading,
    myUserId, status, gameKey, mySeat, seats, isHost, phase, turn, isMyTurn, finished,
    create, join, seatOp, start, act, rematch, leave, dissolve, decline, refresh, reset, leaveOnUnload,
    startPoll, stopPoll,
  }
}
