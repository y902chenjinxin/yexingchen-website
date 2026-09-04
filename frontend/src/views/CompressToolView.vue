<template>
  <IslandInnerBase type="tool" title="像素压缩" subtitle="智能压缩 · 纯本地处理 · 即时销毁">
    <div class="compress-tool">
      <!-- 顶部：隐私提示 -->
      <div class="ct-head">
        <span class="ct-badge">🔒 图片仅在浏览器本地处理，绝不经过服务器，处理完即刻销毁，请放心使用。</span>
      </div>

      <!-- 模式切换 -->
      <div class="ct-tabs">
        <button
          v-for="m in modes"
          :key="m.key"
          class="ct-tab"
          :class="{ active: mode === m.key }"
          :disabled="processing"
          @click="switchMode(m.key)"
        >{{ m.label }}</button>
      </div>

      <!-- 自定义配置区（仅自定义模式） -->
      <div v-if="mode === 'custom'" class="ct-options">
        <label class="opt">目标方式
          <select v-model="custom.targetType">
            <option value="size">按目标大小</option>
            <option value="quality">按压缩质量</option>
          </select>
        </label>
        <label v-if="custom.targetType === 'size'" class="opt">
          目标大小 ≤ <b class="hl">{{ custom.targetKb }}</b> KB
          <input v-model.number="custom.targetKb" type="range" min="50" max="2000" step="50">
        </label>
        <label v-else class="opt">
          压缩质量 {{ custom.quality }}%
          <input v-model.number="custom.quality" type="range" min="10" max="100" step="5">
        </label>
      </div>

      <!-- 缩放配置区（仅缩放模式） -->
      <div v-else-if="mode === 'resize'" class="ct-options">
        <label class="opt">缩放方式
          <select v-model="resize.scaleBy">
            <option value="long">按最长边宽度</option>
            <option value="percent">按比例</option>
          </select>
        </label>
        <label v-if="resize.scaleBy === 'long'" class="opt">最长边
          <b class="hl">{{ resize.longEdge }}</b> px
          <input v-model.number="resize.longEdge" type="range" min="200" max="4000" step="50">
        </label>
        <label v-else class="opt">比例
          <b class="hl">{{ resize.percent }}</b>%
          <input v-model.number="resize.percent" type="range" min="10" max="100" step="5">
        </label>
      </div>

      <!-- 上传区 -->
      <div class="dropzone" :class="{ dragging, locked: processing }" @dragover.prevent="dragging = true" @dragleave="dragging = false" @drop.prevent="onDrop" @click="!processing && trigUpload()">
        <div class="dz-icon">🖼️</div>
        <div class="dz-text">拖拽图片到这里，或点击选择文件</div>
        <div class="dz-hint">支持 JPG / PNG / WEBP（GIF 转静态首帧）· 多文件 · 单文件 ≤ 10MB</div>
      </div>

      <!-- 文件列表 -->
      <div v-if="list.length" class="file-list">
        <div v-for="(f, i) in list" :key="f.id" class="file-row" :class="{ err: !!f.error }">
          <img v-if="f.thumb" :src="f.thumb" class="fr-thumb" alt="" />
          <div class="fr-main">
            <div class="fr-name" :title="f.name">{{ f.name }}</div>
            <div class="fr-meta" v-if="!f.error">
              <template v-if="f.status === 'done'">
                <span class="orig">{{ sizeStr(f.origSize) }}</span>
                <span class="arrow">→</span>
                <span class="out">{{ sizeStr(f.outSize) }}</span>
                <span class="rate" :class="{ neg: f.negOptim }">{{ f.negOptim ? '原图更优，未压缩' : '压缩了 ' + f.rate + '%' }}</span>
              </template>
              <template v-else-if="f.status === 'processing'">
                <span class="proc">{{ f.statusText }}</span>
              </template>
              <template v-else>
                <span class="pending">待压缩</span>
              </template>
            </div>
            <div class="fr-meta err-tip" v-else>{{ f.error }}</div>
          </div>
          <div class="fr-ops">
            <button v-if="f.status === 'done'" class="op" :disabled="processing" @click="download(f)">下载</button>
            <button class="op danger" :disabled="processing" @click="removeAt(i)">删除</button>
          </div>
        </div>
      </div>

      <!-- 进度条（大文件压缩中展示） -->
      <div v-if="processing" class="ct-progress">
        <div class="ct-progress-bar"><div class="ct-progress-fill" :style="{ width: progress + '%' }"></div></div>
        <span class="ct-progress-text">{{ statusText }}</span>
      </div>

      <!-- 底部操作栏 -->
      <div class="ct-actionbar">
        <div class="ct-summary" v-if="list.length">
          <template v-if="finishedCount">
            <span>已压缩 <b>{{ finishedCount }}/{{ list.length }}</b></span>
            <span>节省 <b>{{ savedStr }}</b></span>
          </template>
          <span v-else>已选 {{ list.length }} 项</span>
        </div>
        <div class="ct-summary" v-else>未选择文件</div>
        <div class="ct-btns">
          <button
            v-if="mode === 'smart'"
            class="ct-run"
            :disabled="!list.length || processing"
            @click="run()"
          >{{ processing ? '处理中…' : '一键压缩' }}</button>
          <button
            v-if="mode !== 'smart'"
            class="ct-run"
            :disabled="!list.length || processing"
            @click="run()"
          >{{ processing ? '处理中…' : '开始压缩' }}</button>
          <button v-if="finishedCount" class="ct-zip" :disabled="processing" @click="downloadZip">全部打包下载 (ZIP)</button>
          <button v-if="list.length" class="ct-clear" :disabled="processing" @click="clearAll">清空列表</button>
        </div>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, reactive, computed, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import IslandInnerBase from './islands/IslandInnerBase.vue'

/* ========== 模式 ========== */
const modes = [
  { key: 'smart', label: '🧠 智能压缩' },
  { key: 'custom', label: '⚙️ 自定义压缩' },
  { key: 'resize', label: '📐 仅缩放尺寸' }
]
const mode = ref('smart')
const custom = reactive({ targetType: 'size', targetKb: 250, quality: 80 })
const resize = reactive({ scaleBy: 'long', longEdge: 1920, percent: 50 })

/* ========== 上传 ========== */
const dragging = ref(false)
const processing = ref(false)
const progress = ref(0)
const statusText = ref('')
const list = ref([])
let idSeq = 0

const MAX_SIZE = 10 * 1024 * 1024
const MAX_COUNT = 30
const VALID_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const GIF = 'image/gif'

const finishedCount = computed(() => list.value.filter((f) => f.status === 'done').length)
function savedStr() {
  const arr = list.value.filter((f) => f.status === 'done' && !f.negOptim)
  const saved = arr.reduce((s, f) => s + (f.origSize - f.outSize), 0)
  return saved > 0 ? sizeStr(saved) : '0'
}

let fileInput = null
function ensureInput() {
  if (fileInput) return fileInput
  fileInput = document.createElement('input')
  fileInput.type = 'file'
  fileInput.multiple = true
  fileInput.accept = 'image/jpeg,image/png,image/webp,image/gif'
  fileInput.style.display = 'none'
  return fileInput
}
function trigUpload() {
  const inp = ensureInput()
  inp.onchange = () => {
    addFiles(Array.from(inp.files || []))
    inp.value = ''
  }
  inp.click()
}
function onDrop(e) {
  dragging.value = false
  if (processing.value) return
  addFiles(Array.from(e.dataTransfer?.files || []))
}

function addFiles(files) {
  if (!files.length) return
  for (const file of files) {
    if (list.value.length >= MAX_COUNT) { ElMessage.warning(`最多 ${MAX_COUNT} 个文件，已停止添加`); break }
    if (!file.size || file.size === 0) { ElMessage.error('文件损坏或为空，已拒绝'); continue }
    if (file.size > MAX_SIZE) { ElMessage.error(`「${file.name}」超过 10MB 上限，已拒绝`); continue }
    const isGif = file.type === GIF
    if (VALID_TYPES.indexOf(file.type) < 0 && !isGif) { ElMessage.error(`「${file.name}」不支持的文件类型（仅 JPG/PNG/WEBP/GIF）`); continue }
    const item = {
      id: ++idSeq,
      name: file.name,
      file,
      size: file.size,
      type: file.type,
      status: 'pending',
      error: '',
      statusText: '',
      thumb: URL.createObjectURL(file),
      origSize: file.size,
      outSize: 0,
      outBlob: null,
      rate: 0,
      negOptim: false,
      outName: ''
    }
    if (isGif) ElMessage.warning(`「${file.name}」为 GIF，将转为静态首帧输出`)
    list.value.push(item)
  }
}

function removeAt(i) {
  const f = list.value[i]
  revoke(f)
  list.value.splice(i, 1)
}
function revoke(f) {
  if (f.thumb) { URL.revokeObjectURL(f.thumb); f.thumb = '' }
  if (f.outBlob && f.outBlobUrl) { URL.revokeObjectURL(f.outBlobUrl); f.outBlobUrl = '' }
  f.outBlob = null
}
function clearAll() {
  list.value.forEach((f) => revoke(f))
  list.value.length = 0
}
onBeforeUnmount(() => {
  clearAll()
  if (fileInput && fileInput.parentNode) fileInput.parentNode.removeChild(fileInput)
})

function switchMode(m) {
  if (processing.value) return
  mode.value = m
  // 改模式后清掉已有压缩结果，回到待压缩状态
  list.value.forEach((f) => {
    if (f.outBlobUrl) URL.revokeObjectURL(f.outBlobUrl)
    f.outBlob = null; f.outBlobUrl = ''; f.outSize = 0; f.rate = 0; f.negOptim = false
    f.status = f.error ? 'error' : 'pending'
  })
}

/* ========== 工具函数 ========== */
function sizeStr(n) {
  if (n == null) return '-'
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB'
  return (n / 1024 / 1024).toFixed(2) + ' MB'
}
function baseName(name) {
  return String(name).replace(/\.[^.]+$/, '')
}
function extFor(mime) {
  if (mime === 'image/png') return 'png'
  if (mime === 'image/webp') return 'webp'
  return 'jpg'
}

/* ========== Canvas 解码 ========== */
function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('解析失败'))
    img.src = src
  })
}
function canvasToBlob(canvas, type, quality) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('导出失败'))), type, quality)
  })
}
function drawToCanvas(canvas, img, w, h) {
  canvas.width = Math.max(1, Math.round(w))
  canvas.height = Math.max(1, Math.round(h))
  const ctx = canvas.getContext('2d')
  ctx.imageSmoothingEnabled = true
  ctx.imageSmoothingQuality = 'high'
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
}

/* ========== 智能压缩：Luban 策略 ========== */
const SMART_MAX_SHORT = 1440
const SMART_MAX_LONG = 10800
const SMART_MAX_PX = 10.24 * 1024 * 1024
const LOW_MP = 0.5 * 1024 * 1024

function smartDims(w, h) {
  let scale = 1
  const shortSide = Math.min(w, h)
  const longSide = Math.max(w, h)
  const isLongShot = longSide > SMART_MAX_LONG
  if (isLongShot && shortSide > SMART_MAX_SHORT) {
    scale = SMART_MAX_LONG / longSide
  } else if (shortSide > SMART_MAX_SHORT) {
    scale = SMART_MAX_SHORT / shortSide
  }
  let nw = w * scale
  let nh = h * scale
  if (nw * nh > SMART_MAX_PX) {
    const s = Math.sqrt(SMART_MAX_PX / (w * h))
    nw = w * s
    nh = h * s
  }
  return { w: nw, h: nh, scale }
}
function smartQuality(totalPx) {
  if (totalPx < LOW_MP) return 0.9 // 小图不缩放，高质量保证清晰
  if (totalPx < 2 * 1024 * 1024) return 0.82
  if (totalPx < 5 * 1024 * 1024) return 0.78
  if (totalPx < 10 * 1024 * 1024) return 0.72
  return 0.65
}

/* ========== 核心：压缩单个文件 ========== */
async function compressOne(f) {
  const file = f.file
  f.status = 'processing'
  const srcUrl = URL.createObjectURL(file)
  try {
    // 步骤1：解码（损坏/非图片在此拦截）
    progress.value = 5
    f.statusText = '解析图片…'
    let img
    try { img = await loadImage(srcUrl) }
    catch { throw new Error('解析失败') }
    const w = img.naturalWidth
    const h = img.naturalHeight
    if (!w || !h) throw new Error('无效图片尺寸')
    progress.value = 15

    // 步骤2：计算目标尺寸
    f.statusText = '计算压缩参数…'
    let dw = w, dh = h
    let quality = 0.8
    const isGif = file.type === GIF
    const outType = isGif ? 'image/webp' : (file.type === 'image/png' || file.type === 'image/webp' ? file.type : 'image/jpeg')

    if (mode.value === 'smart') {
      const d = smartDims(w, h)
      dw = d.w; dh = d.h
      quality = smartQuality(w * h)
    } else if (mode.value === 'custom') {
      if (custom.targetType === 'size') {
        // 目标大小：用最长边约束 + 二分质量逼近
        dw = w; dh = h
        const longSide = Math.max(w, h)
        if (longSide > 8000) { dw *= 8000 / longSide; dh *= 8000 / longSide }
      } else {
        quality = custom.quality / 100
      }
    } else {
      // 仅缩放：按长边或比例
      if (resize.scaleBy === 'long') {
        const longSide = Math.max(w, h)
        const s = resize.longEdge / longSide
        dw = w * s; dh = h * s
      } else {
        dw = w * resize.percent / 100
        dh = h * resize.percent / 100
      }
      quality = 0.92
    }
    progress.value = 25

    // 步骤3：绘canvas
    const canvas = document.createElement('canvas')
    drawToCanvas(canvas, img, dw, dh)
    URL.revokeObjectURL(srcUrl)
    if (img.src && img.src.startsWith('blob:')) URL.revokeObjectURL(img.src)
    progress.value = 40

    // 步骤4：生成 Blob（自定义-按大小时二分逼近）
    let blob
    if (mode.value === 'custom' && custom.targetType === 'size') {
      blob = await compressToTarget(canvas, outType, custom.targetKb * 1024, f)
    } else {
      f.statusText = '压缩…'
      blob = await canvasToBlob(canvas, outType, quality)
    }
    progress.value = 80

    // 步骤5：防负优化
    const outSize = blob.size
    const negOptim = outSize >= file.size
    let finalBlob = blob
    let outName = baseName(file.name) + '_compressed.' + extFor(blob.type || outType)
    if (negOptim) {
      if (!isGif) {
        finalBlob = file
        outName = baseName(file.name) + '.' + extFor(file.type)
      } else {
        // GIF 无对应原图下载，保留压缩帧
        negOptim = false
        outSize = blob.size
      }
    }

    f.outBlob = finalBlob
    f.outBlobUrl = URL.createObjectURL(finalBlob)
    f.outSize = finalBlob.size
    f.outName = outName
    f.negOptim = !!negOptim
    f.rate = Math.max(0, Math.round((1 - finalBlob.size / file.size) * 100))
    if (finalBlob.size >= file.size) f.rate = 0
    f.status = 'done'
    f.statusText = ''
    progress.value = 100
  } catch (e) {
    URL.revokeObjectURL(srcUrl)
    f.status = 'error'
    f.error = e?.message || '处理失败'
  }
}

/* 按目标大小二分逼近质量 */
async function compressToTarget(canvas, type, targetBytes, f) {
  let lo = 0.05, hi = 0.95
  let best = null
  for (let i = 0; i < 12; i++) {
    const q = (lo + hi) / 2
    f.statusText = `尝试质量 ${Math.round(q * 100)}%（第${i + 1}轮）…`
    const b = await canvasToBlob(canvas, type, q)
    if (!best || b.size < best.size) best = b
    if (b.size <= targetBytes) lo = q
    else hi = q
    progress.value = 40 + Math.round((i / 12) * 30)
  }
  return best
}

/* ========== 入口：串行处理队列 ========== */
async function run() {
  if (!list.value.length) { ElMessage.warning('请先选择图片'); return }
  const pending = list.value.filter((f) => f.status === 'pending' || f.status === 'error')
  if (!pending.length) { ElMessage.warning('没有待处理的图片'); return }
  processing.value = true
  progress.value = 0
  const total = pending.length
  let done = 0
  for (const f of pending) {
    statusText.value = `正在压缩 ${done + 1}/${total}：${f.name}`
    await compressOne(f)
    done++
    progress.value = Math.round((done / total) * 100)
  }
  processing.value = false
  statusText.value = '完成'
  const ok = list.value.filter((f) => f.status === 'done').length
  ElMessage.success(`完成：成功 ${ok} 个` + (list.value.length - ok ? `，失败 ${list.value.length - ok} 个` : ''))
}

/* ========== 下载（即时销毁） ========== */
function download(f) {
  const url = f.outBlobUrl || URL.createObjectURL(f.outBlob || f.file)
  const a = document.createElement('a')
  a.href = url
  a.download = f.outName || f.name
  document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1500)
}

async function downloadZip() {
  const dones = list.value.filter((f) => f.status === 'done' && f.outBlob)
  if (!dones.length) { ElMessage.warning('暂无压缩结果'); return }
  const JSZip = await loadZip()
  const zip = new JSZip()
  dones.forEach((f, i) => {
    zip.file((f.outName || f.name) || `image_${i + 1}.${extFor(f.outBlob.type || f.type)}`, f.outBlob)
  })
  statusText.value = '打包 ZIP…'
  const content = await zip.generateAsync({ type: 'blob' })
  const url = URL.createObjectURL(content)
  const a = document.createElement('a'); a.href = url; a.download = '压缩图片包.zip'
  document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
  ElMessage.success('已下载压缩图片包')
}
let zipPromise = null
function loadZip() {
  if (!zipPromise) {
    zipPromise = new Promise((resolve, reject) => {
      if (window.JSZip) return resolve(window.JSZip)
      const s = document.createElement('script')
      s.src = 'https://unpkg.com/jszip@3.10.1/dist/jszip.min.js'
      s.async = true
      s.onload = () => resolve(window.JSZip)
      s.onerror = () => reject(new Error('ZIP 库加载失败'))
      document.head.appendChild(s)
    })
  }
  return zipPromise
}
</script>

<style scoped>
.compress-tool { display: flex; flex-direction: column; gap: 18px; }
.ct-head { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
.ct-badge {
  font-size: 12px; color: #7fcfa3; background: rgba(80, 190, 130, 0.12);
  border: 1px solid rgba(80, 190, 130, 0.35); padding: 6px 14px; border-radius: 40px;
}
.ct-tabs { display: flex; gap: 8px; flex-wrap: wrap; }
.ct-tab {
  padding: 9px 18px; border-radius: var(--radius-sm); border: 1px solid var(--ls-line);
  background: var(--ls-paper-2); color: var(--ls-text-2); font-size: 14px; cursor: pointer;
  transition: all var(--transition);
}
.ct-tab:hover { border-color: var(--ls-dai); color: var(--ls-dai); }
.ct-tab.active { background: var(--ls-dai); color: var(--ls-bg1); border-color: var(--ls-dai); }
.ct-tab:disabled { opacity: 0.5; cursor: not-allowed; }

.ct-options { display: flex; gap: 22px; flex-wrap: wrap; }
.opt { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--ls-text-2); }
.opt select, .opt input[type=range] { min-width: 180px; }
.opt select {
  padding: 8px 12px; border-radius: var(--radius-sm); border: 1px solid var(--ls-line);
  background: var(--ls-paper-2); color: var(--ls-text); font-size: 13px;
}
.opt .hl { color: var(--ls-dai); font-size: 15px; }

.dropzone {
  border: 2px dashed var(--ls-line-strong); border-radius: var(--radius);
  padding: 34px 20px; text-align: center; cursor: pointer;
  background: var(--ls-paper-1); transition: all var(--transition);
}
.dropzone.dragging { border-color: var(--ls-dai); background: rgba(112, 192, 214, 0.08); }
.dropzone.locked { opacity: 0.6; cursor: not-allowed; }
.dz-icon { font-size: 40px; margin-bottom: 8px; }
.dz-text { font-family: var(--font-serif); font-size: 16px; color: var(--ls-text); }
.dz-hint { font-size: 12px; color: var(--ls-text-3); margin-top: 8px; }

.file-list { display: flex; flex-direction: column; gap: 8px; max-height: 300px; overflow: auto; }
.file-row {
  display: flex; align-items: center; gap: 12px; padding: 8px 12px;
  background: var(--ls-paper-2); border: 1px solid var(--ls-line); border-radius: var(--radius-sm);
}
.file-row.err { border-color: rgba(226, 138, 120, 0.5); }
.fr-thumb { width: 42px; height: 42px; border-radius: 6px; object-fit: cover; flex: none; background: var(--ls-paper-1); }
.fr-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.fr-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; color: var(--ls-text); }
.fr-meta { font-size: 12px; color: var(--ls-text-2); display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.fr-meta .orig { color: var(--ls-text-3); text-decoration: line-through; }
.fr-meta .out { color: var(--ls-dai); font-weight: 600; }
.fr-meta .rate { color: #7fcfa3; }
.fr-meta .rate.neg { color: var(--ls-text-3); }
.fr-meta .proc { color: var(--ls-text-3); }
.fr-meta.err-tip, .err-tip { color: #e28a78; }
.fr-ops { flex: none; display: flex; gap: 6px; }
.op {
  border: 1px solid var(--ls-line-strong); background: transparent; color: var(--ls-text-2);
  padding: 3px 10px; border-radius: var(--radius-sm); font-size: 12px; cursor: pointer;
}
.op:hover:not(:disabled) { border-color: var(--ls-dai); color: var(--ls-dai); }
.op.danger:hover:not(:disabled) { border-color: #e28a78; color: #e28a78; }
.op:disabled { opacity: 0.4; cursor: not-allowed; }

.ct-progress { display: flex; align-items: center; gap: 12px; }
.ct-progress-bar { flex: 1; height: 8px; border-radius: 6px; background: var(--ls-paper-2); overflow: hidden; }
.ct-progress-fill { height: 100%; background: var(--ls-dai); transition: width 0.2s; }
.ct-progress-text { font-size: 12px; color: var(--ls-text-2); flex: none; }

.ct-actionbar {
  position: sticky; bottom: 0; z-index: 5;
  display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap;
  padding: 12px 18px; border-radius: var(--radius);
  background: var(--ls-glass); border: 1px solid var(--ls-line);
  backdrop-filter: saturate(160%) blur(14px); -webkit-backdrop-filter: saturate(160%) blur(14px);
}
.ct-summary { font-size: 13px; color: var(--ls-text-2); display: flex; gap: 14px; }
.ct-summary b { color: var(--ls-dai); }
.ct-btns { display: flex; gap: 10px; flex-wrap: wrap; }
.ct-run {
  padding: 11px 26px; border: none; border-radius: var(--radius-sm);
  background: var(--ls-dai); color: var(--ls-bg1); font-size: 15px; font-weight: 500;
  cursor: pointer; transition: all var(--transition);
}
.ct-run:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(112, 192, 214, 0.4); }
.ct-run:disabled { opacity: 0.5; cursor: not-allowed; }
.ct-zip {
  padding: 10px 20px; border-radius: var(--radius-sm); border: 1px solid var(--ls-dai);
  background: transparent; color: var(--ls-dai); font-size: 14px; cursor: pointer; transition: all var(--transition);
}
.ct-zip:hover:not(:disabled) { background: rgba(112, 192, 214, 0.1); }
.ct-zip:disabled { opacity: 0.5; cursor: not-allowed; }
.ct-clear {
  padding: 10px 16px; border-radius: var(--radius-sm); border: 1px solid var(--ls-line-strong);
  background: transparent; color: var(--ls-text-2); font-size: 13px; cursor: pointer;
}
.ct-clear:hover:not(:disabled) { border-color: #e28a78; color: #e28a78; }
.ct-clear:disabled { opacity: 0.5; cursor: not-allowed; }
</style>