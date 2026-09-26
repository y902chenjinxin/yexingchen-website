<template>
  <IslandInnerBase type="tool" title="代码美化图" subtitle="贴代码 · 出分享图 · 纯本地渲染">
    <div class="cs-tool">
      <div class="cs-opts">
        <label class="cs-opt">语言
          <select v-model="lang">
            <option value="js">JavaScript</option>
            <option value="python">Python</option>
            <option value="json">JSON</option>
            <option value="sql">SQL</option>
          </select>
        </label>
        <label class="cs-opt">主题
          <select v-model="theme">
            <option value="dark">玄夜（深）</option>
            <option value="light">宣纸（浅）</option>
          </select>
        </label>
        <label class="cs-opt">标题
          <input v-model="title" class="cs-title-input" placeholder="文件名（选填）">
        </label>
      </div>

      <textarea v-model="code" class="cs-input" rows="9" placeholder="粘贴代码……" spellcheck="false"></textarea>

      <div class="cs-preview-wrap">
        <div ref="shotEl" class="cs-shot" :class="theme">
          <div class="cs-bar">
            <span class="cs-dot r"></span><span class="cs-dot y"></span><span class="cs-dot g"></span>
            <span class="cs-file">{{ title || ({ js: 'index.js', python: 'main.py', json: 'data.json', sql: 'query.sql' }[lang]) }}</span>
          </div>
          <pre class="cs-code"><code v-html="highlighted"></code></pre>
        </div>
      </div>

      <div class="cs-actions">
        <button class="cs-btn primary" :disabled="!code.trim()" @click="download">下载 PNG</button>
        <button class="cs-btn" :disabled="!code.trim()" @click="copyImage">复制图片</button>
      </div>
      <div class="cs-note">本地渲染：代码不出浏览器。深浅两主题、四种语言高亮。</div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed } from 'vue'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import { ElMessage } from 'element-plus'

const code = ref('')
const lang = ref('js')
const theme = ref('dark')
const title = ref('')
const shotEl = ref(null)

/* ---- 轻量 tokenizer：注释 / 字符串 / 关键字 / 数字 ---- */
const KW = {
  js: /\b(const|let|var|function|return|if|else|for|while|class|new|import|from|export|default|async|await|try|catch|throw|typeof|this|null|undefined|true|false)\b/g,
  python: /\b(def|return|if|elif|else|for|while|class|import|from|as|with|try|except|raise|lambda|None|True|False|and|or|not|in|is|pass|yield|self)\b/g,
  json: /\b(true|false|null)\b/g,
  sql: /\b(SELECT|FROM|WHERE|INSERT|INTO|UPDATE|DELETE|JOIN|LEFT|RIGHT|INNER|ON|GROUP|BY|ORDER|LIMIT|AS|AND|OR|NOT|NULL|CREATE|TABLE|INDEX|VALUES|SET|DISTINCT|COUNT|SUM|AVG)\b/gi,
}
function esc(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') }

function highlight(src, langKey) {
  let out = esc(src)
  // 注释（优先于关键字）
  const comments = []
  // eslint-disable-next-line no-control-regex
  out = out.replace(/(#.*$|\/\/.*$|\/\*[\s\S]*?\*\/|--.*$)/gm, m => { comments.push(m); return `\u0000C${comments.length - 1}\u0000` })
  // 字符串
  const strings = []
  out = out.replace(/(&quot;.*?&quot;|'[^']*'|"[^"]*"|`[^`]*`)/g, m => { strings.push(m); return `\u0000S${strings.length - 1}\u0000` })
  // 关键字 + 数字
  out = out.replace(KW[langKey] || KW.js, m => `<span class="k">${m}</span>`)
  out = out.replace(/\b(\d+(?:\.\d+)?)\b/g, m => `<span class="n">${m}</span>`)
  // 还原（\u0000 是占位控制符，源码里不会出现）
  // eslint-disable-next-line no-control-regex
  out = out.replace(/\u0000S(\d+)\u0000/g, (_, i) => `<span class="s">${strings[i]}</span>`)
  // eslint-disable-next-line no-control-regex
  out = out.replace(/\u0000C(\d+)\u0000/g, (_, i) => `<span class="c">${comments[i]}</span>`)
  return out
}

const highlighted = computed(() => highlight(code.value || '  // 在左边粘贴代码，这里实时高亮\n  console.log("hello xuanhuang")', lang.value))

function renderToCanvas() {
  const el = shotEl.value
  const rect = el.getBoundingClientRect()
  const scale = 2
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${rect.width * scale}" height="${rect.height * scale}">
    <foreignObject width="100%" height="100%">
      <div xmlns="http://www.w3.org/1999/xhtml" style="width:${rect.width}px;height:${rect.height}px;">
        ${el.outerHTML}
      </div>
    </foreignObject>
  </svg>`
  const img = new Image()
  return new Promise((resolve, reject) => {
    img.onload = () => {
      const cv = document.createElement('canvas')
      cv.width = rect.width * scale; cv.height = rect.height * scale
      cv.getContext('2d').drawImage(img, 0, 0)
      resolve(cv)
    }
    img.onerror = reject
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg)
  })
}

async function download() {
  try {
    const cv = await renderToCanvas()
    const a = document.createElement('a')
    a.href = cv.toDataURL('image/png')
    a.download = `code-${Date.now()}.png`
    a.click()
  } catch { ElMessage.warning('导出失败，请截图代替') }
}
async function copyImage() {
  try {
    const cv = await renderToCanvas()
    const blob = await new Promise(r => cv.toBlob(r, 'image/png'))
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
    ElMessage.success('已复制到剪贴板')
  } catch { ElMessage.warning('当前浏览器不支持复制图片，请下载 PNG') }
}
</script>

<style scoped>
.cs-opts { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }
.cs-opt { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--dp-text2, #45505b); }
.cs-opt select, .cs-title-input {
  padding: 6px 10px; border-radius: 8px; border: 1px solid var(--dp-line, rgba(0,0,0,.14));
  background: var(--dp-surface, #fff); color: var(--dp-text, #18202a); font-size: 13px;
}
.cs-input {
  width: 100%; padding: 12px 14px; border-radius: 10px; font-size: 13.5px; font-family: var(--font-mono, ui-monospace, Menlo, monospace);
  border: 1px solid var(--dp-line, rgba(0,0,0,.12)); background: var(--dp-surface, #fff); color: var(--dp-text, #18202a);
  resize: vertical; margin-bottom: 16px;
}
.cs-preview-wrap { overflow-x: auto; padding-bottom: 6px; }
.cs-shot { border-radius: 12px; overflow: hidden; width: max-content; max-width: 100%; box-shadow: 0 6px 24px rgba(0,0,0,.18); }
.cs-bar { display: flex; align-items: center; gap: 7px; padding: 10px 14px; }
.cs-dot { width: 11px; height: 11px; border-radius: 50%; }
.cs-dot.r { background: #ff5f57; } .cs-dot.y { background: #febc2e; } .cs-dot.g { background: #28c840; }
.cs-file { margin-left: 8px; font-size: 12px; opacity: .7; font-family: var(--font-mono, ui-monospace, Menlo, monospace); }
.cs-code { margin: 0; padding: 16px 18px; overflow-x: auto; font-size: 13.5px; line-height: 1.75; font-family: var(--font-mono, ui-monospace, Menlo, monospace); }
/* 深主题：玄夜 */
.cs-shot.dark { background: #14181f; }
.cs-shot.dark .cs-bar { background: #1b212b; } .cs-shot.dark .cs-file { color: #9aa5b1; }
.cs-shot.dark .cs-code { color: #d5dbe3; }
.cs-shot.dark .k { color: #c792ea; } .cs-shot.dark .s { color: #a8d08d; }
.cs-shot.dark .n { color: #f2b179; } .cs-shot.dark .c { color: #5d6b7c; font-style: italic; }
/* 浅主题：宣纸 */
.cs-shot.light { background: #faf6ec; }
.cs-shot.light .cs-bar { background: #f0e8d5; } .cs-shot.light .cs-file { color: #8a7a55; }
.cs-shot.light .cs-code { color: #3d3527; }
.cs-shot.light .k { color: #8e4aa0; } .cs-shot.light .s { color: #43702c; }
.cs-shot.light .n { color: #b35c1e; } .cs-shot.light .c { color: #9a8f78; font-style: italic; }
.cs-actions { display: flex; gap: 10px; margin-top: 14px; }
.cs-btn {
  padding: 9px 22px; border-radius: 10px; font-size: 13.5px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text, #18202a);
}
.cs-btn.primary { background: var(--yq-gold, #c7a96b); border-color: var(--yq-gold, #c7a96b); color: #fff; font-weight: 600; }
.cs-btn:disabled { opacity: .5; cursor: not-allowed; }
.cs-note { margin-top: 10px; font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
</style>
