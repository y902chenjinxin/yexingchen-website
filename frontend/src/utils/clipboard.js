/**
 * 统一的「复制到剪贴板」—— 含降级方案与用户反馈（v2.40.20）。
 *
 * 为什么要有这个文件：`navigator.clipboard` 在**非 HTTPS、权限被拒、旧内核**下会直接抛错。
 * 以前各工具页的 catch 里写的是「/* 忽略 *\/」，用户点了「复制」像没反应（见
 * docs/ai/TOOL_POLISH_AUDIT_20260927.md 的 A9）。
 *
 * 策略：Clipboard API → 失败降级 textarea + `execCommand('copy')` → 再失败给明确提示，
 * 不让用户猜「到底复制成功没有」。
 */
import { ElMessage } from 'element-plus'

/** 老办法兜底：建一个不可见的 textarea 选中后 execCommand('copy') */
function legacyCopy(text) {
  const ta = document.createElement('textarea')
  ta.value = text
  ta.setAttribute('readonly', '')
  ta.style.position = 'fixed'
  ta.style.top = '-1000px'
  ta.style.left = '-1000px'
  ta.style.opacity = '0'
  document.body.appendChild(ta)
  ta.select()
  ta.setSelectionRange(0, ta.value.length)
  let ok = false
  try { ok = document.execCommand('copy') } catch { ok = false }
  ta.remove()
  return ok
}

/**
 * 复制文本并给出提示。
 * @param {string} text 要复制的内容
 * @param {string} [okMsg] 成功提示文案
 * @returns {Promise<boolean>} 是否成功（调用方可据此决定后续动作）
 */
export async function copyText(text, okMsg = '已复制') {
  const val = String(text ?? '')
  if (!val) {
    ElMessage.warning('没有可复制的内容')
    return false
  }
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(val)
      ElMessage.success(okMsg)
      return true
    }
  } catch { /* 落到下面的降级方案 */ }
  if (legacyCopy(val)) {
    ElMessage.success(okMsg)
    return true
  }
  ElMessage.warning('复制失败 —— 请长按或手动选中文本复制')
  return false
}

/**
 * 复制图片（目前仅二维码用）。剪贴板图片 API 支持面窄，失败时提示改用下载。
 * @param {string} dataUrl png 的 dataURL
 */
export async function copyImage(dataUrl) {
  try {
    const blob = await (await fetch(dataUrl)).blob()
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
    ElMessage.success('已复制到剪贴板')
    return true
  } catch {
    ElMessage.warning('当前浏览器不支持复制图片，请用「下载 PNG」')
    return false
  }
}
