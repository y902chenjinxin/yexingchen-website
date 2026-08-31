/**
 * 全局 Vitest setup：兜底清理任何跨文件 / 跨测试残留。
 *
 * 历史痛点：
 * - URL.createObjectURL / URL.revokeObjectURL 在 fetch-blob / assets-view 中被直接覆盖未还原
 *   → 后续测试拿到 vi.fn() 返回的假 blob: URL；
 * - localStorage 未在 afterEach 清 → fetch-blob 写的 token 残留到 assistant-view；
 * - HTMLAnchorElement.prototype.click 在 assets-view 中被覆盖；
 * - module 缓存（特别是 element-plus / pinia）跨文件共享副作用。
 *
 * 这里做：
 * 1. 每个测试前重置核心全局 stub；
 * 2. 每个测试后强制清 localStorage / sessionStorage；
 * 3. 在所有文件 require/setup 之前预加载，避免其它测试先污染。
 */
import { afterEach, beforeEach, vi } from 'vitest'

const REAL_URL_CREATE = URL.createObjectURL
const REAL_URL_REVOKE = URL.revokeObjectURL
const REAL_CLICK = HTMLAnchorElement.prototype.click

beforeEach(() => {
  // 在每个 case 之前，把全局被测全局对象恢复成 jsdom 默认实现
  // 避免某测试用 global.URL.createObjectURL = vi.fn(...) 覆盖后污染后续 case
  try {
    URL.createObjectURL = REAL_URL_CREATE
  } catch { /* noop */ }
  try {
    URL.revokeObjectURL = REAL_REVOKE
  } catch { /* noop */ }
  try {
    HTMLAnchorElement.prototype.click = REAL_CLICK
  } catch { /* noop */ }
  // 切回真实 timer（防止某测试 useFakeTimers 后忘记 useRealTimers）
  vi.useRealTimers()
  // 清掉假本地存储 / 会话存储
  try {
    localStorage.clear()
  } catch { /* noop */ }
  try {
    sessionStorage.clear()
  } catch { /* noop */ }
  // 清掉 location.hash / history
  if (typeof window !== 'undefined' && window.history && window.history.replaceState) {
    try {
      window.history.replaceState(null, '', '/')
    } catch { /* noop */ }
  }
})

afterEach(() => {
  try {
    URL.createObjectURL = REAL_URL_CREATE
  } catch { /* noop */ }
  try {
    URL.revokeObjectURL = REAL_URL_REVOKE
  } catch { /* noop */ }
  try {
    HTMLAnchorElement.prototype.click = REAL_CLICK
  } catch { /* noop */ }
  try {
    localStorage.clear()
  } catch { /* noop */ }
  try {
    sessionStorage.clear()
  } catch { /* noop */ }
  vi.useRealTimers()
})