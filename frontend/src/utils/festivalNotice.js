/**
 * 假期 / 调休补班的浏览器通知（v2.40.20）。
 *
 * 说明白它的能力边界：**这是本地通知，不是推送** —— 只有你打开玄黄（任意页面）时才会检查并提醒。
 * 想做到「App 没开也收到」需要 Web Push + 服务端推送通道，目前没做（见 docs/ISSUES.md）。
 *
 * 三种提醒（每天各最多一次，按「日期 + 类型」去重）：
 *   1. 假期首日        —— 「中秋节放假第一天」
 *   2. 调休补班日      —— 「今天要上班」
 *   3. 放假前一天      —— 「明天放假」
 *
 * 未经用户同意**不主动请求权限**（免得一进站就弹框）：开关放在「摸鱼日历」页里。
 */
import { fishCalendar } from '@/api/toolkit'

const ON_KEY = 'festival_notice_on'
const SENT_KEY = 'festival_notice_sent'

export function noticeSupported() {
  return typeof window !== 'undefined' && 'Notification' in window
}

export function noticeEnabled() {
  return localStorage.getItem(ON_KEY) === '1'
}

export function setNoticeEnabled(on) {
  localStorage.setItem(ON_KEY, on ? '1' : '0')
}

export function noticePermission() {
  return noticeSupported() ? Notification.permission : 'unsupported'
}

/**
 * 开启开关时调用：申请通知权限。
 * @returns {Promise<'granted'|'denied'|'default'|'unsupported'>}
 */
export async function requestNoticePermission() {
  if (!noticeSupported()) return 'unsupported'
  if (Notification.permission === 'granted' || Notification.permission === 'denied') {
    return Notification.permission
  }
  try { return await Notification.requestPermission() } catch { return 'denied' }
}

function readSent() {
  try { return JSON.parse(localStorage.getItem(SENT_KEY) || '{}') } catch { return {} }
}

/** 清掉 30 天前的去重记录，别让 localStorage 无限长 */
function pruneSent(sent) {
  const cutoff = Date.now() - 30 * 86400000
  Object.keys(sent).forEach((k) => { if (Number(sent[k]) < cutoff) delete sent[k] })
  return sent
}

function fire(sent, key, title, body) {
  if (sent[key]) return false
  try {
    // eslint-disable-next-line no-new
    new Notification(title, { body, icon: '/icons/icon-192.png', badge: '/icons/icon-192.png' })
  } catch { return false }
  sent[key] = Date.now()
  return true
}

/**
 * 检查并（按需）发通知。可在 App 挂载时调用一次；静默失败，绝不打扰用户。
 * @returns {Promise<string[]>} 本次实际发出的通知 key（便于自测）
 */
export async function checkFestivalNotice() {
  if (!noticeEnabled() || !noticeSupported() || Notification.permission !== 'granted') return []
  let d = null
  try {
    d = (await fishCalendar())?.data || null
  } catch { return [] }
  if (!d?.date) return []

  const sent = pruneSent(readSent())
  const today = d.date
  const t = d.today || {}
  const out = []

  if (t.kind === 'holiday' && Number(t.day_index) === 1) {
    if (fire(sent, `${today}-start`, '假期开始', `${t.name}放假第一天，共 ${t.days} 天 · 祝休息愉快`)) out.push('start')
  }
  if (t.kind === 'makeup') {
    if (fire(sent, `${today}-makeup`, '今天要上班', `调休补班日（为 ${t.name} 放假）`)) out.push('makeup')
  }
  const nh = d.next_holiday
  if (nh && !nh.in_progress && Number(nh.days_left) === 1) {
    if (fire(sent, `${today}-eve`, '明天放假', `${nh.name}还有 1 天 · 放假 ${nh.days} 天`)) out.push('eve')
  }

  localStorage.setItem(SENT_KEY, JSON.stringify(sent))
  return out
}

/** 摸鱼日历页的开关状态文案 */
export function noticeStatusText() {
  if (!noticeSupported()) return '当前浏览器不支持通知'
  if (!noticeEnabled()) return '开启后：放假 / 补班当天在浏览器里提醒你（需站点开着）'
  const p = noticePermission()
  if (p === 'granted') return '已开启：放假首日 / 补班日 / 放假前一天会提醒（站点打开时生效）'
  if (p === 'denied') return '浏览器已拒绝通知权限，请在地址栏权限设置里允许'
  return '已记录开关，但通知权限未授予'
}
