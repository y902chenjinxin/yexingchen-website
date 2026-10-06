/**
 * useUndoGuard —— 悔棋防连悔（本地对局）。
 *
 * 规则（v2.44.3）：同一方悔棋一次后，必须等**对手**走出真实一手才能再悔；
 * 自己接着走一手**不算**解锁（否则「悔→走→悔→走」可无限刷）。
 * 在线对局由服务端下发的 `undo_blocked` 权威判定，本地（单机 AI / 同屏双人）
 * 没有服务端，用本 composable 维持同一口径。
 *
 * 用法：
 *   const guard = useUndoGuard()
 *   // 每次落子后：guard.noteMove(color)   —— 只有对手动了才解锁
 *   // 悔棋按钮置灰：guard.blocked(color)
 *   // 悔棋成功后：guard.markUndo(color)
 *   // 重开 / 换局：guard.reset()
 */
import { ref } from 'vue'

export function useUndoGuard() {
  const lastUndoKey = ref('')

  /** 记下「刚刚悔棋的是哪一方」 */
  function markUndo(key) {
    if (key !== '' && key != null) lastUndoKey.value = String(key)
  }

  /** 某一方落子：只有当它不是「刚悔棋的那一方」时才解锁 */
  function noteMove(key) {
    const k = key == null ? '' : String(key)
    if (k && lastUndoKey.value && k !== lastUndoKey.value) lastUndoKey.value = ''
  }

  /** 这一方是否被禁止悔棋（上一次悔棋就是它，对手还没动） */
  function blocked(key) {
    const k = key == null ? '' : String(key)
    return !!k && !!lastUndoKey.value && k === lastUndoKey.value
  }

  function reset() { lastUndoKey.value = '' }

  return { lastUndoKey, markUndo, noteMove, blocked, reset }
}
