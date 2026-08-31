/**
 * 笔记内嵌图片 / PDF 的持久化引用方案。
 *
 * 核心约束：
 * - 数据库中不能保存 blob: URL（刷新即失效）；
 * - 用 data-asset-id 作为唯一引用，加载时调用鉴权 fetchBlob 取得 object URL；
 * - 渲染期 object URL 只在当前页面生命周期有效，组件销毁前必须 revoke。
 *
 * HTML 形态：
 * - 图片：<img data-asset-id="N" alt="..." class="xuanhuang-note-image" />，可附 data-asset-title
 * - PDF  ：<a href="#" data-asset-id="N" data-asset-title="..." class="xuanhuang-asset-link">📄 ...</a>
 *
 * 这些属性在编辑保存时原样保留，不依赖 src/href。
 *
 * 安全：
 * - sanitizeNoteHtml() 用明确白名单去除 <script> / <style> / <iframe> / on* / javascript: 等。
 *   允许的标签与属性固定列出，所有未在白名单的标签会被移除（保留内容文本）。
 *   所有链接 href 只允许 http/https/mailto/tel/相对锚点；data: 与 javascript: 一律拒绝。
 */

const IMG_TAG = 'IMG'
const A_TAG = 'A'

/** 允许保留的标签白名单 */
const ALLOWED_TAGS = new Set([
  'a', 'b', 'i', 'em', 'strong', 'u', 's', 'p', 'br', 'span', 'div',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'ul', 'ol', 'li',
  'blockquote', 'pre', 'code',
  'hr', 'sub', 'sup',
  'img',
])

/** 标签 → 允许的属性白名单。其它属性会被剥离。 */
const ALLOWED_ATTRS = {
  a: new Set(['href', 'title', 'target', 'rel', 'class', 'data-asset-id', 'data-asset-title']),
  img: new Set(['alt', 'class', 'data-asset-id', 'data-asset-title']),
  '*': new Set([]), // 默认无属性
}

/** 全局允许的属性（与具体标签白名单并集） */
const GLOBAL_ATTRS = new Set(['class'])

/** 安全 href scheme 白名单 */
const SAFE_URL_RE = /^(?:https?:|mailto:|tel:|\/|#|\?)/i

/** 不允许的标签（即使有内容也直接丢弃；防止 <script> / <style> / <iframe> 持久化） */
const FORBIDDEN_TAGS = new Set([
  'script', 'style', 'iframe', 'frame', 'frameset', 'object', 'embed',
  'form', 'input', 'textarea', 'select', 'button',
  'meta', 'link', 'base', 'svg', 'math', 'noscript',
])

function escapeHtml(s) {
  return String(s).replace(
    /[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]),
  )
}

/** 生成图片占位 HTML（不含 src，仅 data 属性）。 */
export function imagePlaceholderHtml(assetId, title) {
  const t = escapeHtml(title || '')
  return `<img data-asset-id="${assetId}" alt="${t}" class="xuanhuang-note-image" />`
}

/** 生成 PDF 占位 HTML。 */
export function pdfPlaceholderHtml(assetId, title) {
  const t = escapeHtml(title || '')
  return `<a href="#" data-asset-id="${assetId}" data-asset-title="${t}" class="xuanhuang-asset-link">📄 ${t}</a>&nbsp;`
}

/**
 * 扫描 editorEl 中所有 [data-asset-id] 图片，逐个通过 fetchBlob 拿 object URL。
 * 同步返回已注入的 assetId 列表。
 */
export async function hydrateNoteImages(editorEl, fetchBlob) {
  if (!editorEl) return []
  const imgs = Array.from(editorEl.querySelectorAll('img[data-asset-id]'))
  const ids = []
  for (const img of imgs) {
    const id = img.getAttribute('data-asset-id')
    if (!id) continue
    if (img.dataset.hydrated === '1') continue
    try {
      const { objectUrl } = await fetchBlob(Number(id), 'preview')
      img.src = objectUrl
      img.dataset.hydrated = '1'
      ids.push(Number(id))
    } catch {
      // 失败保留 data-asset-id，不显示 src，便于重试
    }
  }
  return ids
}

/** 释放 editorEl 内所有由 hydrateNoteImages 注入的 object URL。 */
export function revokeAllNoteImages(editorEl) {
  if (!editorEl) return 0
  const imgs = Array.from(editorEl.querySelectorAll('img[data-asset-id][data-hydrated="1"]'))
  let n = 0
  for (const img of imgs) {
    try {
      if (img.src && img.src.startsWith('blob:')) {
        URL.revokeObjectURL(img.src)
        n += 1
      }
    } catch { /* noop */ }
    delete img.dataset.hydrated
    img.removeAttribute('src')
  }
  return n
}

/** 判断 href 是否安全 scheme */
function isSafeHref(href) {
  if (!href) return false
  // 去掉前导空白
  const v = String(href).trim()
  if (!v) return false
  // javascript: / data: / vbscript: / file: 等一律拒绝
  if (/^\s*(javascript|data|vbscript|file):/i.test(v)) return false
  // 允许 http/https/mailto/tel/相对路径/锚点/查询
  return SAFE_URL_RE.test(v)
}

/** 递归清洗 DOM 节点树，返回新 fragment 内的 cleaned 子树（in-place） */
function cleanNode(node, doc) {
  // 跳过非元素节点
  if (!node) return null
  if (node.nodeType === 3 /* text */) {
    // 文本节点：保留
    return node
  }
  if (node.nodeType !== 1 /* element */) {
    // 注释/指令节点：丢弃
    return null
  }
  const tag = node.tagName.toLowerCase()
  // 完全禁止：script / style / iframe 等
  if (FORBIDDEN_TAGS.has(tag)) {
    // 整个子树丢弃
    return null
  }
  // 不在白名单：拆开保留文本内容
  if (!ALLOWED_TAGS.has(tag)) {
    // 克隆一个新容器（不常用，用 span 兜底）让子节点递归清洗
    const wrapper = doc.createElement('span')
    const children = Array.from(node.childNodes)
    for (const c of children) {
      const cleaned = cleanNode(c, doc)
      if (cleaned) wrapper.appendChild(cleaned)
    }
    return wrapper
  }

  // 在白名单：清理属性
  const el = doc.createElement(tag)
  const allowed = new Set([
    ...GLOBAL_ATTRS,
    ...(ALLOWED_ATTRS[tag] || ALLOWED_ATTRS['*']),
  ])
  // href 需要 scheme 校验
  const attrs = Array.from(node.attributes)
  for (const a of attrs) {
    const name = a.name.toLowerCase()
    // 任何 on* 事件属性一律剥离（onclick / onerror / onload / onfocus 等）
    if (name.startsWith('on')) continue
    // style 属性不允许（避免 CSS 注入）
    if (name === 'style') continue
    // formaction / srcdoc / xlink:href / data: href 等可执行属性
    if (name === 'formaction' || name === 'srcdoc' || name === 'xlink:href') continue
    if (!allowed.has(name)) continue
    // href 单独校验
    if (name === 'href') {
      if (!isSafeHref(a.value)) {
        // 不安全 → 用 # 替代，避免点击执行
        el.setAttribute('href', '#')
      } else {
        el.setAttribute('href', a.value)
      }
      continue
    }
    // target=_blank 自动补 rel=noopener noreferrer
    if (name === 'target' && /^\s*_blank\s*$/i.test(a.value)) {
      el.setAttribute('target', '_blank')
      el.setAttribute('rel', 'noopener noreferrer')
      continue
    }
    el.setAttribute(name, a.value)
  }
  // 递归清洗子节点
  for (const c of Array.from(node.childNodes)) {
    const cleaned = cleanNode(c, doc)
    if (cleaned) el.appendChild(cleaned)
  }
  return el
}

/**
 * 清洗富文本 HTML：去危险标签 / 事件属性 / 危险 URL；保留 data-asset-id 占位。
 * 返回清洗后的 HTML 字符串（不含包装 div）。
 */
export function sanitizeNoteHtml(html) {
  if (!html) return ''
  const tpl = document.createElement('template')
  tpl.innerHTML = `<div>${html}</div>`
  const root = tpl.content.firstElementChild
  if (!root) return ''
  const out = document.createElement('div')
  for (const c of Array.from(root.childNodes)) {
    const cleaned = cleanNode(c, tpl.content.ownerDocument || document)
    if (cleaned) out.appendChild(cleaned)
  }
  return out.innerHTML
}

/** 判断当前选择/光标处是否在 editorEl 内。 */
export function isAssetPlaceholder(el) {
  if (!el) return null
  if (el.tagName === IMG_TAG && el.hasAttribute('data-asset-id')) {
    return { kind: 'image', assetId: Number(el.getAttribute('data-asset-id')) }
  }
  if (
    el.tagName === A_TAG &&
    el.classList.contains('xuanhuang-asset-link') &&
    el.hasAttribute('data-asset-id')
  ) {
    return { kind: 'pdf', assetId: Number(el.getAttribute('data-asset-id')) }
  }
  return null
}