/**
 * 分级触觉反馈（APP_design.md #13 · v2.46.33）
 *
 * Android WebView 支持 navigator.vibrate；iOS Safari 不支持（静默 no-op）。
 * 规范分档：轻点 light / 确认 medium / 错误 heavy；与视觉反馈同步（调用点紧跟状态变化）。
 *
 * 用法：
 *   import { haptic } from '@/utils/haptic'
 *   haptic.light()                       // Tab 切换、轻点
 *   haptic.medium()                      // 保存成功、确认
 *   haptic.heavy()                       // 删除、校验失败
 */
function fire(pattern) {
  try {
    if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(pattern)
  } catch { /* 不支持则静默 */ }
}

export const haptic = {
  light: () => fire(8),
  medium: () => fire(18),
  heavy: () => fire(32),
  /** 双击节奏：成功提示（配合视觉成功态） */
  success: () => fire([10, 40, 14]),
  /** 三段急促：错误/警告 */
  error: () => fire([10, 30, 10, 30, 14]),
}
