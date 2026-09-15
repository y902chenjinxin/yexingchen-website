import { ref } from 'vue'
import { defineStore } from 'pinia'

/**
 * 界面偏好（按用户隔离，存 localStorage）。
 *
 * 目前只有「桌宠是否展示」一项：需求是默认展示，可在个人中心关掉，
 * 关掉后刷新/换页都不再出现（此前只有「音乐页隐藏」这种按路由的硬编码规则）。
 *
 * 为什么按用户分键：这是个人口味，家里成员共用一台设备时不该互相覆盖。
 * 为什么在模块加载时就同步 hydrate：避免「关了桌宠的人每次进站先闪一下鲸鱼」，
 * 期间先用「上次登录的用户」的偏好顶着，bindUser 拿到真实 uid 后再归位。
 */

const KEY_PREFIX = 'xh_ui_prefs_v1'
const LAST_UID_KEY = `${KEY_PREFIX}_last_uid`

const keyOf = (uid) => (uid == null ? `${KEY_PREFIX}_guest` : `${KEY_PREFIX}_u${uid}`)

function read(uid) {
  try {
    const raw = localStorage.getItem(keyOf(uid))
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function write(uid, data) {
  try {
    localStorage.setItem(keyOf(uid), JSON.stringify(data))
  } catch {
    /* 隐私模式 / 配额满：静默降级为「本次会话有效」 */
  }
}

export const usePrefsStore = defineStore('prefs', () => {
  // 默认展示
  const petVisible = ref(true)
  // 当前偏好归属的用户 id（null = 尚未绑定 / 未登录）
  const boundUid = ref(null)

  function applyPrefs(uid) {
    const saved = read(uid)
    petVisible.value = saved?.petVisible !== false
  }

  // 模块加载即同步 hydrate：先用上次登录用户的偏好，避免桌宠闪现
  const lastUid = localStorage.getItem(LAST_UID_KEY)
  applyPrefs(lastUid ? Number(lastUid) : null)

  function persist() {
    write(boundUid.value, { petVisible: petVisible.value })
    try {
      localStorage.setItem(LAST_UID_KEY, boundUid.value == null ? '' : String(boundUid.value))
    } catch {
      /* 同上 */
    }
  }

  /** 登录后 / 切换账号时调用。 */
  function bindUser(uid) {
    const next = uid == null ? null : Number(uid)
    if (next === null) {
      // 首帧或已登出：保留模块加载时按「上次登录用户」hydrate 的值，
      // 否则会把已关闭桌宠的用户重置为默认，导致每次进站闪一下鲸鱼
      boundUid.value = null
      return
    }
    if (boundUid.value === next) return
    boundUid.value = next
    applyPrefs(next)
  }

  function setPetVisible(visible) {
    petVisible.value = !!visible
    persist()
  }

  function togglePet() {
    setPetVisible(!petVisible.value)
  }

  return { petVisible, boundUid, bindUser, setPetVisible, togglePet }
})
