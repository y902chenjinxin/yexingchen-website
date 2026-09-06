// 轻量安全的 Markdown → HTML 渲染（先转义防 XSS，再应用常用行内/块级语法）
function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function inline(s) {
  if (!s) return ''
  // [text](url) 链接（转义后仅允许 http/https/mailto）
  s = s.replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
  // `code`
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>')
  // **bold** 与 *italic*
  s = s.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
  s = s.replace(/\*([^*]+)\*/g, '<i>$1</i>')
  return s
}

export function renderMarkdown(md = '') {
  if (!md) return ''
  const lines = esc(md).split(/\r?\n/)
  const out = []
  let listTag = ''
  let i = 0
  const closeList = () => {
    if (listTag) { out.push(`</${listTag}>`); listTag = '' }
  }

  for (; i < lines.length; i++) {
    const line = lines[i]
    const trimmed = line.trim()
    if (trimmed === '') { closeList(); continue }
    // 标题
    const h = trimmed.match(/^(#{1,3})\s+(.*)$/)
    if (h) {
      closeList()
      const n = h[1].length
      out.push(`<h${n}>${inline(h[2])}</h${n}>`)
      continue
    }
    // 水平线
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      closeList(); out.push('<hr/>'); continue
    }
    // 引用
    if (/^&gt;\s?/.test(trimmed) || /^>\s?/.test(trimmed)) {
      closeList()
      out.push(`<blockquote>${inline(trimmed.replace(/^(?:&gt;|>) ?/, ''))}</blockquote>`)
      continue
    }
    // 无序列表
    if (/^[-*•]\s+/.test(trimmed)) {
      if (listTag !== 'ul') { closeList(); out.push('<ul>'); listTag = 'ul' }
      out.push(`<li>${inline(trimmed.replace(/^[-*•]\s+/, ''))}</li>`)
      continue
    }
    // 有序列表
    if (/^\d+[.、)]\s+/.test(trimmed)) {
      if (listTag !== 'ol') { closeList(); out.push('<ol>'); listTag = 'ol' }
      out.push(`<li>${inline(trimmed.replace(/^\d+[.、)]\s+/, ''))}</li>`)
      continue
    }
    closeList()
    out.push(`<p>${inline(trimmed)}</p>`)
  }
  closeList()
  return out.join('\n')
}