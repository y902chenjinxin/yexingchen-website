/**
 * 粘贴 / 拖拽 → 上传 纯函数。
 *
 * 设计原则：
 * - 不依赖 DOM/Vue/Element Plus，便于单测。
 * - 业务侧只需传入 workbenchApi.upload + workbenchApi.assets.fetchBlob + insertImage，
 *   即可复用同一鉴权上传路径。
 *
 * 支持：
 * - clipboardData.items（DataTransferItemList）取图片
 * - clipboardData.files（FileList）回退取图片
 * - dataTransfer.files（拖拽）按 MIME 过滤 image/* / application/pdf
 */

/** 从 clipboardData 取第一个图片文件；找不到返回 null。 */
export function pickImageFromClipboard(cd) {
  if (!cd) return null
  // 1) 优先 items
  if (cd.items && typeof cd.items.length === 'number') {
    for (let i = 0; i < cd.items.length; i += 1) {
      const item = cd.items[i]
      if (!item) continue
      if (item.kind === 'file' && item.type && item.type.startsWith('image/')) {
        const f = item.getAsFile ? item.getAsFile() : null
        if (f) return f
      }
    }
  }
  // 2) 回退 files
  if (cd.files && typeof cd.files.length === 'number') {
    for (let i = 0; i < cd.files.length; i += 1) {
      const f = cd.files[i]
      if (f && f.type && f.type.startsWith('image/')) return f
    }
  }
  return null
}

/** 从拖拽 dataTransfer.files 取支持的文件（图片/PDF）；返回过滤后的 File[]。 */
export function pickAcceptedFromDrop(dt) {
  const files = dt && dt.files
  if (!files || typeof files.length !== 'number') return []
  const out = []
  for (let i = 0; i < files.length; i += 1) {
    const f = files[i]
    if (!f) continue
    if (f.type && (f.type.startsWith('image/') || f.type === 'application/pdf')) {
      out.push(f)
    }
  }
  return out
}

/** 纯函数：把所有被忽略的文件名合并为一个提示字符串（避免逐个 toast 刷屏）。 */
export function summarizeIgnored(files) {
  if (!files || typeof files.length !== 'number' || !files.length) return ''
  const names = []
  for (let i = 0; i < files.length; i += 1) {
    const f = files[i]
    if (f && f.name) names.push(f.name)
  }
  return names.join('、')
}

/** 纯函数：从 clipboardData 决定走「图片上传」还是「纯文本插入」。 */
export function classifyPaste(cd) {
  const img = pickImageFromClipboard(cd)
  if (img) return { kind: 'image', file: img }
  const text = cd && cd.getData ? cd.getData('text/plain') : ''
  return { kind: 'text', text: text || '' }
}