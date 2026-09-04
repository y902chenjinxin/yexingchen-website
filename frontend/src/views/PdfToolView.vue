<template>
  <IslandInnerBase type="tool" title="PDF 工具" subtitle="纯前端处理 · 文件本地完成 · 即时销毁">
    <div class="pdf-tool">
      <!-- 头部：隐私徽章 + Tab -->
      <div class="pt-head">
        <span class="pt-badge">🔒 隐私保护：文件本地处理，即时销毁</span>
      </div>
      <div class="pt-tabs">
        <button
          v-for="t in tabs"
          :key="t.key"
          class="pt-tab"
          :class="{ active: tab === t.key }"
          :disabled="processing"
          @click="switchTab(t.key)"
        >{{ t.label }}</button>
      </div>

      <div v-show="!processing" class="pt-body">
        <!-- Tab A：图片转 PDF -->
        <div v-show="tab === 'a'">
          <div class="dropzone" :class="{ dragging }" @dragover.prevent="dragging = true" @dragleave="dragging = false" @drop.prevent="onDrop($event, 'a')" @click="trigUpload('a')">
            <div class="dz-icon">🖼️</div>
            <div class="dz-text">拖拽图片到这里，或点击选择文件</div>
            <div class="dz-hint">支持格式：JPG、PNG、BMP、WEBP（单文件≤10MB，最多20个）</div>
          </div>

          <div v-if="aList.length" class="file-list">
            <div v-for="(f, i) in aList" :key="'a' + i" class="file-row">
              <span class="fr-idx">{{ i + 1 }}</span>
              <span class="fr-name" :title="f.name">{{ f.name }}</span>
              <span class="fr-size">{{ sizeStr(f.size) }}</span>
              <span class="fr-status" :class="f.error ? 'err' : ''">{{ f.error || '待处理' }}</span>
              <span class="fr-ops">
                <button class="op" :disabled="i === 0 || processing" @click="move('a', i, -1)">上移</button>
                <button class="op" :disabled="i === aList.length - 1 || processing" @click="move('a', i, 1)">下移</button>
                <button class="op danger" @click="removeAt('a', i)">删除</button>
              </span>
            </div>
          </div>

          <div class="opt-grid">
            <label class="opt">页面尺寸
              <select v-model="aOpt.pageSize">
                <option value="a4">A4</option>
                <option value="original">原图自适应</option>
              </select>
            </label>
            <label class="opt">方向
              <select v-model="aOpt.orientation">
                <option value="auto">自动</option>
                <option value="portrait">纵向</option>
                <option value="landscape">横向</option>
              </select>
            </label>
            <label class="opt">边距
              <select v-model="aOpt.margin">
                <option value="none">无</option>
                <option value="narrow">窄</option>
                <option value="wide">宽</option>
              </select>
            </label>
          </div>
        </div>

        <!-- Tab B：PDF 转图片 -->
        <div v-show="tab === 'b'">
          <div class="dropzone" :class="{ dragging }" @dragover.prevent="dragging = true" @dragleave="dragging = false" @drop.prevent="onDrop($event, 'b')" @click="trigUpload('b')">
            <div class="dz-icon">📄</div>
            <div class="dz-text">拖拽 PDF 到这里，或点击选择文件</div>
            <div class="dz-hint">提取每一页为高清 JPG；多页自动打包为 ZIP（单文件≤10MB）</div>
          </div>
          <div v-if="bList.length" class="file-list">
            <div v-for="(f, i) in bList" :key="'b' + i" class="file-row">
              <span class="fr-idx">{{ i + 1 }}</span>
              <span class="fr-name" :title="f.name">{{ f.name }}</span>
              <span class="fr-size">{{ sizeStr(f.size) }}</span>
              <span class="fr-status" :class="f.error ? 'err' : ''">{{ f.error || '待处理' }}</span>
              <span class="fr-ops"><button class="op danger" @click="removeAt('b', i)">删除</button></span>
            </div>
          </div>
          <div class="opt-grid">
            <label class="opt">分辨率
              <select v-model="bOpt.dpi">
                <option :value="150">标准 150 DPI</option>
                <option :value="300">高清 300 DPI</option>
              </select>
            </label>
          </div>
        </div>

        <!-- Tab C：PDF 合并与拆分 -->
        <div v-show="tab === 'c'">
          <div class="dropzone" :class="{ dragging }" @dragover.prevent="dragging = true" @dragleave="dragging = false" @drop.prevent="onDrop($event, 'c')" @click="trigUpload('c')">
            <div class="dz-icon">📚</div>
            <div class="dz-text">拖拽 PDF 到这里，或点击选择文件</div>
            <div class="dz-hint">合并：调整顺序合并为一个 PDF；拆分：按页码范围提取（单文件≤10MB）</div>
          </div>
          <div v-if="cList.length" class="file-list">
            <div v-for="(f, i) in cList" :key="'c' + i" class="file-row">
              <span class="fr-idx">{{ i + 1 }}</span>
              <span class="fr-name" :title="f.name">{{ f.name }}</span>
              <span class="fr-size">{{ sizeStr(f.size) }}</span>
              <span class="fr-status" :class="f.error ? 'err' : ''">{{ f.error || '待处理' }}</span>
              <span class="fr-ops">
                <button class="op" :disabled="i === 0 || processing" @click="move('c', i, -1)">上移</button>
                <button class="op" :disabled="i === cList.length - 1 || processing" @click="move('c', i, 1)">下移</button>
                <button class="op danger" @click="removeAt('c', i)">删除</button>
              </span>
            </div>
          </div>
          <label class="opt-inline">合并生成的 PDF 文件名
            <input v-model="cOpt.mergedName" class="text-input" placeholder="merged.pdf" />
          </label>
          <label class="opt-inline">页码范围（拆分，如 <code>1-3,5</code>）
            <input v-model="cOpt.range" class="text-input" placeholder="1-3,5" />
          </label>
          <div class="range-ops">
            <button class="mini-btn" :disabled="!cList.length || processing" @click="doMerge">合并 PDF</button>
            <button class="mini-btn" :disabled="cList.length !== 1 || processing" @click="doSplitPdf">拆分 PDF</button>
            <button class="mini-btn" :disabled="cList.length !== 1 || processing" @click="doSplitText">提取为文本</button>
          </div>
        </div>
      </div>

      <!-- 底部固定操作栏 -->
      <div class="pt-actionbar">
        <div class="pt-summary" v-if="currentList.length">
          <span>已选 <b>{{ currentList.length }}</b> 项</span>
          <span>共 {{ sizeStr(currentList.reduce((s, f) => s + f.size, 0)) }}</span>
        </div>
        <div class="pt-summary" v-else>未选择文件</div>
        <button class="pt-run" :disabled="!currentList.length || processing" @click="run()">
          {{ processing ? '处理中…' : '开始处理并下载' }}
        </button>
      </div>

      <!-- 处理进度 -->
      <div v-if="processing" class="pt-progress">
        <div class="pt-progress-bar"><div class="pt-progress-fill" :style="{ width: progress + '%' }"></div></div>
        <span class="pt-progress-text">{{ statusText }}</span>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, reactive, computed, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import IslandInnerBase from './islands/IslandInnerBase.vue'

const tabs = [
  { key: 'a', label: '🖼 图片转 PDF' },
  { key: 'b', label: '📄 PDF 转图片' },
  { key: 'c', label: '📚 合并与拆分' }
]
const tab = ref('a')
const dragging = ref(false)
const processing = ref(false)
const progress = ref(0)
const statusText = ref('')

const aList = ref([])
const bList = ref([])
const cList = ref([])
const aOpt = reactive({ pageSize: 'a4', orientation: 'auto', margin: 'none' })
const bOpt = reactive({ dpi: 150 })
const cOpt = reactive({ mergedName: 'merged.pdf', range: '' })

const currentList = computed(() =>
  tab.value === 'a' ? aList.value : tab.value === 'b' ? bList.value : cList.value
)

let uploadInput = null
function ensureInput() {
  if (uploadInput) return uploadInput
  uploadInput = document.createElement('input')
  uploadInput.type = 'file'
  uploadInput.multiple = true
  uploadInput.style.display = 'none'
  return uploadInput
}
function trigUpload(kind) {
  const inp = ensureInput()
  const accept = kind === 'a' ? 'image/jpeg,image/png,image/bmp,image/webp' : 'application/pdf'
  inp.accept = accept
  inp.onchange = () => {
    const files = Array.from(inp.files || [])
    addFiles(kind, files)
    inp.value = ''
  }
  inp.click()
}
function onDrop(e, kind) {
  dragging.value = false
  addFiles(kind, Array.from(e.dataTransfer?.files || []))
}

const VALID_IMG = ['image/jpeg', 'image/png', 'image/bmp', 'image/webp']
const MAX_SIZE = 10 * 1024 * 1024
const MAX_COUNT = 20

function addFiles(kind, files) {
  const target = kind === 'a' ? aList.value : kind === 'b' ? bList.value : cList.value
  if (!files.length) return
  for (const f of files) {
    if (target.length >= MAX_COUNT) { ElMessage.warning(`最多 ${MAX_COUNT} 个文件，已停止添加`); break }
    if (!f.size || f.size === 0) { ElMessage.error('文件损坏或为空'); continue }
    if (f.size > MAX_SIZE) { ElMessage.error(`「${f.name}」超过 10MB 上限，已拒绝`); continue }
    if (kind === 'a') {
      if (VALID_IMG.indexOf(f.type) < 0) { ElMessage.error(`「${f.name}」不支持的文件类型`); continue }
    } else if (!/application\/pdf|\.pdf$/i.test(f.type || f.name)) {
      ElMessage.error(`「${f.name}」不支持的文件类型`); continue
    }
    target.push({ name: f.name, size: f.size, file: f, error: '' })
  }
}

function move(kind, i, d) {
  const target = kind === 'a' ? aList.value : kind === 'c' ? cList.value : null
  if (!target) return
  const j = i + d
  if (j < 0 || j >= target.length) return
  ;[target[i], target[j]] = [target[j], target[i]]
}
function removeAt(kind, i) {
  const target = kind === 'a' ? aList.value : kind === 'b' ? bList.value : cList.value
  target.splice(i, 1)
}
function switchTab(k) { tab.value = k }

function sizeStr(n) {
  if (n == null) return '-'
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB'
  return (n / 1024 / 1024).toFixed(2) + ' MB'
}

/* ---------------- CDN 库按需加载 ---------------- */
let libsPromise = null
function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = src; s.async = true
    s.onload = () => resolve()
    s.onerror = () => reject(new Error('资源加载失败：' + src))
    document.head.appendChild(s)
  })
}
async function ensureLibs(kind) {
  if (!libsPromise) {
    libsPromise = (async () => {
      if (!window.pdfjsLib) {
        await Promise.all([
          loadScript('https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.min.js'),
          loadScript('https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js')
        ])
      }
      window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js'
      if (!window.PDFLib) await loadScript('https://unpkg.com/pdf-lib@1.17.1/dist/pdf-lib.min.js')
      if (!window.JSZip) await loadScript('https://unpkg.com/jszip@3.10.1/dist/jszip.min.js')
    })()
  }
  await libsPromise
}

/* ---------------- 工具函数 ---------------- */
function arrayBuffer(file) { return file.arrayBuffer() }

async function loadImageDims(bytes, mime) {
  const blob = new Blob([bytes], { type: mime })
  const url = URL.createObjectURL(blob)
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => resolve({ w: img.naturalWidth, h: img.naturalHeight, url, img })
    img.onerror = () => { URL.revokeObjectURL(url); resolve(null) }
    img.src = url
  })
}

// 返回 { embedType: 'jpg'|'png', bytes }，必要时压缩/转码
async function prepareImage(f, dim) {
  const raw = new Uint8Array(await arrayBuffer(f.file))
  let bytes = raw
  let type = f.type
  // 仅 jpeg 直接嵌入；其余（含超大）走 canvas 转 PNG（可压缩）
  const needsCanvas = dim.w > 4000 || dim.h > 4000 || !(f.type === 'image/jpeg')
  if (needsCanvas) {
    let confirmCompress = false
    if (dim.w > 4000 || dim.h > 4000) {
      try {
        await ElMessageBox.confirm(
          '图片分辨率过高，是否强制压缩至 2000px 生成 PDF？',
          '图片过大',
          { confirmButtonText: '压缩', cancelButtonText: '跳过', type: 'warning' }
        )
        confirmCompress = true
      } catch { return { embedType: null } }
    }
    const maxDim = confirmCompress ? 2000 : Math.max(dim.w, dim.h)
    const scale = confirmCompress
      ? 2000 / Math.max(dim.w, dim.h)
      : 1
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(dim.w * scale)
    canvas.height = Math.round(dim.h * scale)
    const ctx = canvas.getContext('2d')
    const tx = new Image(); tx.src = dim.url
    await new Promise((r) => { tx.onload = r })
    ctx.drawImage(tx, 0, 0, canvas.width, canvas.height)
    bytes = await new Promise((r) => canvas.toBlob((b) => b.arrayBuffer().then((ab) => r(new Uint8Array(ab))), 'image/png'))
    type = 'image/png'
  }
  return { embedType: type === 'image/jpeg' ? 'jpg' : 'png', bytes }
}

function downloadBytes(bytes, filename, mime) {
  const blob = new Blob([bytes], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename
  document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1500)
}

/* ---------------- 真正执行入口 ---------------- */
async function run() {
  if (!currentList.value.length) { ElMessage.warning('请先上传文件'); return }
  if (tab.value === 'a') {
    try { await ensureLibs(); await buildImagesPdf() }
    catch (e) { showFatal(e) }
  } else if (tab.value === 'b') {
    try { await ensureLibs(); await buildPdfImages() }
    catch (e) { showFatal(e) }
  } else {
    ElMessage.warning('请在「合并与拆分」区点击具体操作按钮')
  }
}

function showFatal(e) {
  ElMessage.error(e?.message || '处理出错，请重试')
  processing.value = false
  progress.value = 0
  statusText.value = ''
}

async function buildImagesPdf() {
  processing.value = true
  progress.value = 0
  statusText.value = '准备 PDF 文档…'
  const pdfDoc = await window.PDFLib.PDFDocument.create()
  const list = aList.value
  const total = list.length
  for (let idx = 0; idx < total; idx++) {
    const f = list[idx]
    f.error = ''
    try {
      statusText.value = `处理图片 ${idx + 1}/${total}：${f.name}`
      const raw = await arrayBuffer(f.file)
      const dim = await loadImageDims(raw, f.file.type)
      if (!dim) throw new Error('图片解码失败')
      const prep = await prepareImage(f, dim)
      if (!prep.embedType) { f.error = '已跳过'; progress.value = Math.round(((idx + 1) / total) * 100); continue }
      const img = new Image(); img.src = dim.url; await new Promise((r) => (img.onload = r))
      const iw = img.naturalWidth || dim.w
      const ih = img.naturalHeight || dim.h
      const embedded = prep.embedType === 'jpg'
        ? await pdfDoc.embedJpg(prep.bytes)
        : await pdfDoc.embedPng(prep.bytes)
      const margin = aOpt.margin === 'none' ? 0 : aOpt.margin === 'narrow' ? 20 : 50
      let pageW, pageH
      if (aOpt.pageSize === 'original') {
        pageW = iw + margin * 2
        pageH = ih + margin * 2
      } else {
        let w = 595, h = 842
        const orient = aOpt.orientation === 'auto' ? (ih > iw ? 'portrait' : 'landscape') : aOpt.orientation
        if (orient === 'landscape') { w = 842; h = 595 }
        pageW = w; pageH = h
      }
      const page = pdfDoc.addPage([pageW, pageH])
      const cw = pageW - margin * 2
      const ch = pageH - margin * 2
      const scale = Math.min(cw / embedded.width, ch / embedded.height)
      const dw = embedded.width * scale
      const dh = embedded.height * scale
      page.drawImage(embedded, {
        x: margin + (cw - dw) / 2,
        y: margin + (ch - dh) / 2,
        width: dw,
        height: dh
      })
    } catch (e) {
      f.error = '处理失败'
    }
    progress.value = Math.round(((idx + 1) / total) * 100)
  }
  statusText.value = '生成并下载 PDF…'
  const bytes = await pdfDoc.save()
  downloadBytes(bytes, '多图片合并.pdf', 'application/pdf')
  clearList('a')
  statusText.value = '完成'
  ElMessage.success('完成，文件已下载')
  processing.value = false
}

async function buildPdfImages() {
  processing.value = true
  const f = bList.value[0]
  f.error = ''
  progress.value = 0
  try {
    statusText.value = `解析 PDF：${f.name}`
    const data = await arrayBuffer(f.file)
    let pdf
    try {
      const task = window.pdfjsLib.getDocument({ data })
      pdf = await task.promise
    } catch (e) {
      if (e && (e.name === 'PasswordException')) {
        f.error = '该 PDF 已加密，请先解除密码再试'
        ElMessage.error(f.error)
        return
      }
      throw e
    }
    const scale = (bOpt.dpi || 150) / 72
    const pages = pdf.numPages
    const zip = new window.JSZip()
    let failed = false
    for (let i = 1; i <= pages; i++) {
      statusText.value = `转换第 ${i}/${pages} 页…`
      const page = await pdf.getPage(i)
      const viewport = page.getViewport({ scale })
      const canvas = document.createElement('canvas')
      canvas.width = Math.floor(viewport.width)
      canvas.height = Math.floor(viewport.height)
      const ctx = canvas.getContext('2d')
      const renderCtx = { canvasContext: ctx, viewport }
      try { await page.render(renderCtx).promise } catch { failed = true; continue }
      const blob = await new Promise((r) => canvas.toBlob(r, 'image/jpeg', 0.92))
      if (pages === 1) {
        const bytes = await blob.arrayBuffer()
        downloadBytes(new Uint8Array(bytes), f.name.replace(/\.pdf$/i, '') + '_第1页.jpg', 'image/jpeg')
      } else {
        zip.file(`第${i}页.jpg`, blob)
      }
      progress.value = Math.round((i / pages) * 100)
    }
    pdf.destroy?.()
    if (pages > 1) {
      statusText.value = '打包 ZIP…'
      const content = await zip.generateAsync({ type: 'blob' })
      const url = URL.createObjectURL(content)
      const a = document.createElement('a'); a.href = url; a.download = f.name.replace(/\.pdf$/i, '') + '_图片.zip'
      document.body.appendChild(a); a.click(); a.remove()
      setTimeout(() => URL.revokeObjectURL(url), 2000)
    }
    if (failed) f.error = '部分页面失败'
    else { ElMessage.success('完成，文件已下载'); clearList('b') }
  } catch (e) {
    f.error = '处理失败'
    ElMessage.error('处理失败：' + (e?.message || '未知错误'))
  }
  statusText.value = '完成'
  processing.value = false
}

async function doMerge() {
  if (cList.value.length < 1) { ElMessage.warning('请先上传 PDF'); return }
  await ensureLibs()
  processing.value = true
  progress.value = 0
  statusText.value = '合并中…'
  const names = []
  try {
    const out = await window.PDFLib.PDFDocument.create()
    for (let idx = 0; idx < cList.value.length; idx++) {
      const f = cList.value[idx]
      f.error = ''
      statusText.value = `合并 ${idx + 1}/${cList.value.length}：${f.name}`
      try {
        const src = await window.PDFLib.PDFDocument.load(await arrayBuffer(f.file), { ignoreEncryption: true })
        const pages = await out.copyPages(src, src.getPageIndices())
        pages.forEach((p) => out.addPage(p))
        names.push(f.name)
      } catch { f.error = '合并失败' }
      progress.value = Math.round(((idx + 1) / cList.value.length) * 100)
    }
    const bytes = await out.save()
    downloadBytes(bytes, cOpt.mergedName || 'merged.pdf', 'application/pdf')
    clearList('c')
    ElMessage.success('完成，已下载合并后 PDF')
  } catch (e) { showFatal(e) }
  statusText.value = '完成'
  processing.value = false
}

function parseRange(str) {
  if (!str || !str.trim()) return null
  const set = new Set()
  for (const part of String(str).split(',')) {
    const p = part.trim()
    if (!p) continue
    if (/-/.test(p)) {
      const [a, b] = p.split('-').map((x) => parseInt(x.trim(), 10))
      if (isNaN(a)) return null
      const end = isNaN(b) ? a : b
      if (end < a) return null
      for (let i = a; i <= end; i++) set.add(i)
    } else {
      const n = parseInt(p, 10)
      if (isNaN(n)) return null
      set.add(n)
    }
  }
  return [...set]
}

async function doSplitPdf() {
  if (cList.value.length !== 1) { ElMessage.warning('请仅上传一个 PDF'); return }
  await ensureLibs()
  const f = cList.value[0]
  const pages = parseRange(cOpt.range)
  if (!pages || !pages.length) { ElMessage.warning('页码范围格式错误，示例：1-3,5'); return }
  processing.value = true
  statusText.value = '拆分中…'
  try {
    const src = await window.PDFLib.PDFDocument.load(await arrayBuffer(f.file), { ignoreEncryption: true })
    const max = src.getPageCount()
    const ok = pages.filter((p) => p >= 1 && p <= max)
    if (!ok.length) { ElMessage.warning('没有有效的页码范围'); return }
    const out = await window.PDFLib.PDFDocument.create()
    const copied = await out.copyPages(src, ok.map((p) => p - 1))
    copied.forEach((p) => out.addPage(p))
    const bytes = await out.save()
    downloadBytes(bytes, f.name.replace(/\.pdf$/i, '') + '_拆分.pdf', 'application/pdf')
    clearList('c')
    ElMessage.success('完成，已下载拆分后 PDF')
  } catch (e) { showFatal(e) }
  statusText.value = '完成'
  processing.value = false
}

async function doSplitText() {
  if (cList.value.length !== 1) { ElMessage.warning('请仅上传一个 PDF'); return }
  await ensureLibs()
  const f = cList.value[0]
  processing.value = true
  statusText.value = '提取文本…'
  try {
    const data = await arrayBuffer(f.file)
    const task = window.pdfjsLib.getDocument({ data })
    const pdf = await task.promise
    let text = ''
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i)
      const content = await page.getTextContent()
      const pageText = content.items.map((it) => it.str || '').join(' ')
      text += `\n===== 第 ${i} 页 =====\n${pageText}\n`
      progress.value = Math.round((i / pdf.numPages) * 100)
    }
    pdf.destroy?.()
    const txtBytes = new TextEncoder().encode(text)
    downloadBytes(txtBytes, f.name.replace(/\.pdf$/i, '') + '_文本.txt', 'text/plain')
    clearList('c')
    ElMessage.success('完成，已下载文本')
  } catch (e) { showFatal(e) }
  statusText.value = '完成'
  processing.value = false
}

function clearList(kind) {
  const target = kind === 'a' ? aList.value : kind === 'b' ? bList.value : cList.value
  target.forEach((f) => { void f })
  target.length = 0
}

onBeforeUnmount(() => {
  if (uploadInput && uploadInput.parentNode) uploadInput.parentNode.removeChild(uploadInput)
})
</script>

<style scoped>
.pdf-tool { display: flex; flex-direction: column; gap: 18px; }
.pt-head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
.pt-badge {
  font-size: 12px; color: #7fcfa3; background: rgba(80, 190, 130, 0.12);
  border: 1px solid rgba(80, 190, 130, 0.35); padding: 6px 14px; border-radius: 40px;
}
.pt-tabs { display: flex; gap: 8px; flex-wrap: wrap; }
.pt-tab {
  padding: 9px 18px; border-radius: var(--radius-sm); border: 1px solid var(--ls-line);
  background: var(--ls-paper-2); color: var(--ls-text-2); font-size: 14px; cursor: pointer;
  transition: all var(--transition);
}
.pt-tab:hover { border-color: var(--ls-dai); color: var(--ls-dai); }
.pt-tab.active { background: var(--ls-dai); color: var(--ls-bg1); border-color: var(--ls-dai); }
.pt-tab:disabled { opacity: 0.5; cursor: not-allowed; }

.pt-body { display: flex; flex-direction: column; gap: 16px; }
.dropzone {
  border: 2px dashed var(--ls-line-strong); border-radius: var(--radius);
  padding: 34px 20px; text-align: center; cursor: pointer;
  background: var(--ls-paper-1); transition: all var(--transition);
}
.dropzone.dragging { border-color: var(--ls-dai); background: rgba(112, 192, 214, 0.08); }
.dz-icon { font-size: 40px; margin-bottom: 8px; }
.dz-text { font-family: var(--font-serif); font-size: 16px; color: var(--ls-text); }
.dz-hint { font-size: 12px; color: var(--ls-text-3); margin-top: 8px; }

.file-list { display: flex; flex-direction: column; gap: 8px; max-height: 260px; overflow: auto; }
.file-row {
  display: flex; align-items: center; gap: 12px; padding: 8px 12px;
  background: var(--ls-paper-2); border: 1px solid var(--ls-line); border-radius: var(--radius-sm);
}
.fr-idx { width: 20px; height: 20px; flex: none; border-radius: 50%; background: var(--ls-line); color: var(--ls-text-2); display: flex; align-items: center; justify-content: center; font-size: 12px; }
.fr-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; color: var(--ls-text); }
.fr-size { flex: none; font-size: 12px; color: var(--ls-text-3); }
.fr-status { flex: none; font-size: 12px; color: var(--ls-dai); }
.fr-status.err { color: #e28a78; }
.fr-ops { flex: none; display: flex; gap: 6px; }
.op {
  border: 1px solid var(--ls-line-strong); background: transparent; color: var(--ls-text-2);
  padding: 3px 10px; border-radius: var(--radius-sm); font-size: 12px; cursor: pointer;
}
.op:hover:not(:disabled) { border-color: var(--ls-dai); color: var(--ls-dai); }
.op.danger:hover:not(:disabled) { border-color: #e28a78; color: #e28a78; }
.op:disabled { opacity: 0.4; cursor: not-allowed; }

.opt-grid { display: flex; gap: 16px; flex-wrap: wrap; }
.opt { display: flex; flex-direction: column; gap: 5px; font-size: 13px; color: var(--ls-text-2); }
.opt select {
  padding: 8px 12px; border-radius: var(--radius-sm); border: 1px solid var(--ls-line);
  background: var(--ls-paper-2); color: var(--ls-text); font-size: 13px; min-width: 130px;
}
.opt-inline { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--ls-text-2); flex-wrap: wrap; }
.text-input {
  padding: 8px 12px; border-radius: var(--radius-sm); border: 1px solid var(--ls-line);
  background: var(--ls-paper-2); color: var(--ls-text); font-size: 13px; min-width: 200px;
}
.range-ops { display: flex; gap: 10px; flex-wrap: wrap; }
.mini-btn {
  padding: 9px 18px; border-radius: var(--radius-sm); border: 1px solid var(--ls-line-strong);
  background: var(--ls-paper-2); color: var(--ls-text); font-size: 13px; cursor: pointer;
  transition: all var(--transition);
}
.mini-btn:hover:not(:disabled) { border-color: var(--ls-dai); color: var(--ls-dai); }
.mini-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.pt-actionbar {
  position: sticky; bottom: 0; z-index: 5;
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  padding: 12px 18px; border-radius: var(--radius);
  background: var(--ls-glass); border: 1px solid var(--ls-line);
  backdrop-filter: saturate(160%) blur(14px); -webkit-backdrop-filter: saturate(160%) blur(14px);
}
.pt-summary { font-size: 13px; color: var(--ls-text-2); display: flex; gap: 16px; }
.pt-summary b { color: var(--ls-dai); }
.pt-run {
  padding: 11px 26px; border: none; border-radius: var(--radius-sm);
  background: var(--ls-dai); color: var(--ls-bg1); font-size: 15px; font-weight: 500;
  cursor: pointer; transition: all var(--transition);
}
.pt-run:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(112, 192, 214, 0.4); }
.pt-run:disabled { opacity: 0.5; cursor: not-allowed; }

.pt-progress { display: flex; align-items: center; gap: 12px; }
.pt-progress-bar { flex: 1; height: 8px; border-radius: 6px; background: var(--ls-paper-2); overflow: hidden; }
.pt-progress-fill { height: 100%; background: var(--ls-dai); transition: width 0.2s; }
.pt-progress-text { font-size: 12px; color: var(--ls-text-2); flex: none; }
</style>