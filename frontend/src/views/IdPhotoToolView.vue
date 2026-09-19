<template>
  <div class="idp-page">
    <div class="lj-bg" aria-hidden="true">
      <div class="lj-paper-texture"></div>
      <div class="lj-wash w1"></div>
      <div class="lj-wash w2"></div>
    </div>

    <div class="idp-inner">
      <!-- 页头 -->
      <header class="idp-head">
        <div class="idp-head-left"><BackButton class="idp-back" /></div>
        <div class="idp-titles">
          <h1 class="idp-title">证件照</h1>
          <p class="idp-sub">纯前端裁剪 · 智能换底 · 多种尺寸即出</p>
        </div>
      </header>

      <!-- 第一步：上传原图 -->
      <section v-if="!srcUrl" class="glass idp-upload">
        <div
          class="idp-drop"
          :class="{ dragging }"
          @dragover.prevent="dragging = true"
          @dragleave="dragging = false"
          @drop.prevent="onDrop"
          @click="trigPick"
        >
          <div class="idp-drop-icon">📷</div>
          <div class="idp-drop-text">拖拽人像照片到这里，或点击选择</div>
          <div class="idp-drop-hint">正面免冠 · 光线均匀 · JPG/PNG ≤ 20MB</div>
        </div>
        <div class="idp-upload-note">全部处理在浏览器本地完成，照片不会上传到服务器</div>
      </section>

      <!-- 第二步：裁剪 + 参数 → 生成 -->
      <template v-else>
        <div class="idp-grid">
          <!-- 裁剪窗 -->
          <section class="glass idp-pane">
            <h2 class="idp-pane-title">裁剪</h2>
            <div
              class="idp-crop"
              :class="{ panning: panning }"
              @pointerdown="onCropDown"
              @pointermove="onCropMove"
              @pointerup="onCropUp"
              @pointercancel="onCropUp"
            >
              <canvas ref="cropCanvas" class="idp-crop-canvas"></canvas>
              <span class="idp-crop-hint">{{ panning ? '松开停止平移' : '在框内按住拖动调整位置' }}</span>
            </div>
            <div class="idp-crop-ctl">
              <span class="idp-crop-ctl-label">缩放</span>
              <input class="idp-range" type="range" min="1" max="3" step="0.05" v-model.number="zoom" />
              <span class="idp-crop-ctl-val">{{ zoom.toFixed(2) }}x</span>
            </div>
            <button class="idp-text-btn" @click="resetUpload">↺ 换一张</button>
          </section>

          <!-- 参数 -->
          <section class="glass idp-pane">
            <h2 class="idp-pane-title">参数设置</h2>

            <div class="idp-block">
              <span class="idp-label">尺寸</span>
              <div class="idp-size-grid">
                <button
                  v-for="s in sizeOptions"
                  :key="s.key"
                  class="idp-chip"
                  :class="{ active: !custom.on && size.key === s.key }"
                  @click="pickSize(s)"
                >{{ s.label }}</button>
                <button class="idp-chip" :class="{ active: custom.on }" @click="custom.on = true">自定义</button>
              </div>
              <div v-if="custom.on" class="idp-custom">
                <input v-model.number="custom.w" type="number" min="100" class="idp-num" placeholder="宽" @blur="clampCustom" />
                <span class="idp-x">×</span>
                <input v-model.number="custom.h" type="number" min="100" class="idp-num" placeholder="高" @blur="clampCustom" />
                <span class="idp-hint">px · 300dpi</span>
              </div>
            </div>

            <div class="idp-block">
              <div class="idp-switch-row">
                <span>智能换底</span>
                <span class="idp-desc">仅对底色较均匀的照片效果好</span>
                <span class="idp-toggle" :class="{ on: removeBg }" @click="removeBg = !removeBg"><i></i></span>
              </div>
              <div v-if="removeBg" class="idp-block">
                <span class="idp-label">容差 <i class="idp-cap">低=只清相近底色，高=清得更干净</i></span>
                <input class="idp-range" type="range" min="6" max="45" step="1" v-model.number="tolerance" />
                <span class="idp-crop-ctl-val">{{ tolerance }}</span>
              </div>
              <div class="idp-block">
                <div class="idp-switch-row">
                  <span>背景色</span>
                  <div class="idp-color-row">
                    <button
                      v-for="c in colors"
                      :key="c.hex"
                      class="idp-color"
                      :class="{ active: color.hex === c.hex }"
                      :style="{ background: c.hex }"
                      :title="c.name"
                      @click="color = c"
                    ></button>
                    <label class="idp-color-pick" title="自定义颜色">
                      <span class="idp-rainbow"></span>
                      <input type="color" v-model="color.hex" class="idp-color-input" />
                    </label>
                    <span class="idp-color-name">{{ colorName }} {{ color.hex }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="idp-block">
              <div class="idp-switch-row">
                <span>提亮</span>
                <span class="idp-desc">人物区轻微增亮</span>
                <span class="idp-toggle" :class="{ on: enhance }" @click="enhance = !enhance"><i></i></span>
              </div>
            </div>

            <button class="idp-generate" :disabled="busy" @click="generate">
              {{ busy ? '生成中…' : '生成证件照' }}
            </button>
          </section>
        </div>

        <!-- 第三步：结果 -->
        <transition name="idp-fade">
          <section v-if="result.show" class="glass idp-result">
            <div class="idp-result-head">
              <h2 class="idp-pane-title">生成结果 · {{ sizeLabel }}</h2>
              <span class="idp-badge">{{ sizeLabel }} · {{ curSize.w }}×{{ curSize.h }}px</span>
            </div>

            <div class="idp-result-body">
              <!-- 标准照（带底色） -->
              <div class="idp-card">
                <span class="idp-card-tag">标准照 {{ sizeLabel }}</span>
                <div class="idp-stage" :style="{ background: stageBgBorder }">
                  <img :src="result.coloredUrl" alt="标准照" />
                </div>
                <div class="idp-card-ops">
                  <button class="idp-btn" @click="downloadColored" :disabled="busy">下载</button>
                </div>
              </div>

              <!-- 透明底 -->
              <div v-if="result.transparentUrl" class="idp-card">
                <span class="idp-card-tag">透明底 PNG</span>
                <div class="idp-stage grid-bg">
                  <img :src="result.transparentUrl" alt="透明底" />
                </div>
                <div class="idp-card-ops">
                  <button class="idp-btn ghost" @click="downloadTransparent" :disabled="busy">下载透明底</button>
                </div>
              </div>
            </div>

            <div class="idp-result-tip">提示：输出为 PNG，像素尺寸与所选尺寸一致（300dpi）。换底仅在「智能换底」开启时生效。</div>
          </section>
        </transition>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import BackButton from '@/components/BackButton.vue'
import api from '@/api/index'

const sizeOptions = [
  { key: 'c1', label: '一寸',       w: 295, h: 413 },
  { key: 'c2', label: '二寸',       w: 413, h: 579 },
  { key: 's1', label: '小一寸',     w: 260, h: 378 },
  { key: 's2', label: '小二寸',     w: 413, h: 531 },
  { key: 'lg', label: '大一寸',     w: 390, h: 567 },
  { key: 'id', label: '身份证',     w: 358, h: 441 },
  { key: 'dz', label: '驾驶证',     w: 358, h: 441 },
  { key: 'hz', label: '护照签证',   w: 390, h: 567 },
]
const colors = [
  { name: '白', hex: '#FFFFFF' },
  { name: '蓝', hex: '#3B73C6' },
  { name: '红', hex: '#E23A3A' },
  { name: '灰', hex: '#6B6B6B' },
]

const dragging = ref(false)
const busy = ref(false)
const srcUrl = ref('')
const srcImg = ref(null)
const size = ref(sizeOptions[0])
const custom = reactive({ on: false, w: 400, h: 567 })
const color = ref(colors[0])
const removeBg = ref(true)
const tolerance = ref(22)
const enhance = ref(false)
const zoom = ref(1.25)
const srcCy = ref(0)
const panning = ref(false)
const result = ref({ show: false, coloredUrl: '', transparentUrl: '' })
const cropCanvas = ref(null)

// ---- MODNet 人像分割 matte 缓存与状态机 ----
// matteCache/宽度为原图尺寸的 alpha（0-255），推理在 WebWorker，不阻塞 UI。
let matteCache = null
let matteW = 0
let mattePromise = null

function resetMatte() {
  matteCache = null
  matteW = 0
  mattePromise = null
}

// 原图尺寸的 matte 取裁剪窗内对应区域（与 drawCrop 同一几何映射），逐像素写入 alpha
// 服务端 CPU 跑 MODNet（浏览器 wasm 对动态量化为全零），返回全分辨率灰度 PNG，解码为 matte
async function matteFromBackend() {
  const img = srcImg.value
  if (!img) return null
  const iw = img.naturalWidth, ih = img.naturalHeight
  const cv = document.createElement('canvas'); cv.width = iw; cv.height = ih
  const ctx = cv.getContext('2d'); ctx.drawImage(img, 0, 0)
  const blob = await new Promise((res) => cv.toBlob(res, 'image/jpeg', 0.92))
  if (!blob) return null
  const fd = new FormData()
  fd.append('file', blob, 'photo.jpg')
  // api 拦截器已 return response.data，这里拿到的就是 {code,msg,data:{w,h,b64}}
  const body = await api.post('/idphoto/matte', fd)
  if (!body || body.code !== 0 || !body.data) return null
  const { w, h, b64 } = body.data
  const pngBlob = await (await fetch(`data:image/png;base64,${b64}`)).blob()
  const url = URL.createObjectURL(pngBlob)
  const png = new Image()
  await new Promise((res, rej) => { png.onload = res; png.onerror = rej; png.src = url })
  URL.revokeObjectURL(url)
  const c2 = document.createElement('canvas'); c2.width = w; c2.height = h
  const cx2 = c2.getContext('2d', { willReadFrequently: true })
  cx2.drawImage(png, 0, 0)
  const id = cx2.getImageData(0, 0, w, h).data
  const matte = new Uint8ClampedArray(w * h)
  for (let i = 0; i < w * h; i++) matte[i] = id[i * 4]  // 灰度 PNG：R 通道即强度
  return { matte, w }
}

// 取原图尺寸 matte；未缓存则异步分割（共享 in-flight promise）
function getMatte() {
  if (matteCache) return Promise.resolve(matteCache)
  if (mattePromise) return mattePromise
  mattePromise = matteFromBackend()
    .then((r) => { if (r) { matteCache = r.matte; matteW = r.w } return r ? r.matte : null })
    .catch(() => null)
    .finally(() => { mattePromise = null })
  return mattePromise
}

const curSize = computed(() => {
  if (custom.on) return { label: `${custom.w}×${custom.h}`, w: custom.w, h: custom.h }
  return size.value
})
const sizeLabel = computed(() => curSize.value.label)
const colorName = computed(() => colors.find((c) => c.hex.toLowerCase() === color.value.hex.toLowerCase())?.name || '自定义')
const stageBgBorder = computed(() => (color.value.hex && color.value.hex !== '#FFFFFF' ? color.value.hex : '#dfe6e2'))

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v))
function clampCustom() {
  if (!Number.isFinite(custom.w) || custom.w < 100) custom.w = 100
  if (!Number.isFinite(custom.h) || custom.h < 100) custom.h = 100
}
function pickSize(s) { custom.on = false; size.value = s }
function resetCy() {
  const img = srcImg.value
  if (img) srcCy.value = img.naturalHeight / 2
}

function drawCrop() {
  const cv = cropCanvas.value
  if (!cv) return
  const { w, h } = curSize.value
  if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h }
  const ctx = cv.getContext('2d', { willReadFrequently: true })
  const img = srcImg.value
  if (!img || !img.naturalWidth) return
  const iw = img.naturalWidth, ih = img.naturalHeight
  const sc = Math.max(w / iw, h / ih) * zoom.value
  const cw = w / sc, chh = h / sc
  if (cw > iw || chh > ih) { resetCy() }
  const cy = clamp(srcCy.value, chh / 2, ih - chh / 2)
  srcCy.value = cy
  const sx = (iw - cw) / 2
  ctx.clearRect(0, 0, w, h)
  ctx.drawImage(img, sx, cy - chh / 2, cw, chh, 0, 0, w, h)
}
watch(() => [curSize.value.w, curSize.value.h, zoom.value, srcCy.value], () => drawCrop())

// ---- 裁剪窗平移 ----
let pan = null
function onCropDown(e) {
  if (!srcImg.value) return
  pan = { y: e.clientY, cy: srcCy.value }
  panning.value = true
  const cv = cropCanvas.value
  if (cv && cv.setPointerCapture) cv.setPointerCapture(e.pointerId)
}
function onCropMove(e) {
  if (!pan) return
  const cv = cropCanvas.value, img = srcImg.value
  if (!cv || !img) return
  const rect = cv.getBoundingClientRect()
  const { w, h } = curSize.value
  const sc = Math.max(w / img.naturalWidth, h / img.naturalHeight) * zoom.value
  const dySrc = ((e.clientY - pan.y) * (h / rect.height)) / sc
  srcCy.value = clamp(pan.cy - dySrc, 0, img.naturalHeight)
}
function onCropUp() { pan = null; panning.value = false }

// ---- 上传 ----
function detectNewCanvas() { nextTick(() => drawCrop()) }
function handleFile(f) {
  if (!/^image\/(jpeg|png|webp)$/i.test(f.type)) { ElMessage.error('仅支持 JPG / PNG 图片'); return }
  if (f.size > 20 * 1024 * 1024) { ElMessage.error('图片超过 20MB，请压缩后重试'); return }
  const url = URL.createObjectURL(f)
  const img = new Image()
  img.onload = () => {
    if (!img.naturalWidth || !img.naturalHeight) { ElMessage.error('图片读取失败'); URL.revokeObjectURL(url); return }
    srcImg.value = img
    srcCy.value = img.naturalHeight / 2
    detectNewCanvas()
  }
  img.onerror = () => { ElMessage.error('图片读取失败'); URL.revokeObjectURL(url) }
  img.src = url
  srcUrl.value = url
}
function resetUpload() {
  if (srcUrl.value) URL.revokeObjectURL(srcUrl.value)
  srcUrl.value = ''
  srcImg.value = null
  result.value.show = false
  zoom.value = 1.25
  resetMatte()
}
let picker = null
function ensurePicker() {
  if (picker) return picker
  picker = document.createElement('input')
  picker.type = 'file'
  picker.accept = 'image/jpeg,image/png,image/webp'
  picker.style.display = 'none'
  return picker
}
function trigPick() {
  const inp = ensurePicker()
  inp.onchange = () => { const f = inp.files && inp.files[0]; inp.value = ''; if (f) handleFile(f) }
  inp.click()
}
function onDrop(e) {
  dragging.value = false
  const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]
  if (f) handleFile(f)
}

// ---- 图像处理（纯前端，零网络） ----
/**
 * 智能换底 v2：边缘抗锯齿版。
 * 思路：
 * 1. 采样四边求背景色（比 v1 更鲁棒）
 * 2. BFS flood fill 建 mask（全透明=背景）
 * 3. 对 mask 边界像素做 alpha 羽化（soft matting），消除锯齿
 * 4. 仅对边缘 3px 范围做加权混合，人物主体保持原样
 */
function removeUniformBg(ctx, w, h, tol) {
  const im = ctx.getImageData(0, 0, w, h)
  const d = im.data

  // Step 1：采样四边，取中位数作为背景色（比均值更抗噪）
  const samples = []
  const step = Math.max(1, (w * h > 250000) ? 8 : 4)
  for (let x = 0; x < w; x += step) {
    // 顶行
    samples.push({ r: d[x * 4], g: d[x * 4 + 1], b: d[x * 4 + 2] })
    // 底行
    const bi = ((h - 1) * w + x) * 4
    samples.push({ r: d[bi], g: d[bi + 1], b: d[bi + 2] })
  }
  for (let y = 0; y < h; y += step) {
    // 左列
    samples.push({ r: d[y * w * 4], g: d[y * w * 4 + 1], b: d[y * w * 4 + 2] })
    // 右列
    const ri = (y * w + w - 1) * 4
    samples.push({ r: d[ri], g: d[ri + 1], b: d[ri + 2] })
  }
  // 中位数（样本不够时用均值兜底）
  const med = (arr, k) => {
    if (arr.length === 0) return 0
    arr.sort((a, b) => a - b)
    return arr[Math.floor(arr.length * k)]
  }
  const rr = med(samples.map(s => s.r), 0.5)
  const rg = med(samples.map(s => s.g), 0.5)
  const rb = med(samples.map(s => s.b), 0.5)

  const tol2 = tol * tol * 3  // RGB 欧氏距离阈值

  // Step 2：BFS flood fill（仅标记，不改 alpha）
  const visited = new Uint8Array(w * h)
  const queue = new Array(w * h)
  let qi = 0, qe = 0
  const push = (i) => { if (!visited[i]) { visited[i] = 1; queue[qe++] = i } }
  // 从四边入队（已知的背景起点）
  for (let x = 0; x < w; x++) { push(x); push((h - 1) * w + x) }
  for (let y = 0; y < h; y++) { push(y * w); push(y * w + w - 1) }

  const isBg = (i) => {
    const p = i * 4
    const dr = d[p] - rr, dg = d[p + 1] - rg, db = d[p + 2] - rb
    return dr * dr + dg * dg + db * db <= tol2
  }

  while (qi < qe) {
    const idx = queue[qi++]
    if (!isBg(idx)) continue  // 该像素不是背景色，不扩展
    const x = idx % w, y = (idx - x) / w | 0
    if (y > 0) push(idx - w)
    if (y < h - 1) push(idx + w)
    if (x > 0) push(idx - 1)
    if (x < w - 1) push(idx + 1)
  }

  // Step 3：构建 alpha map（0=确定背景，1=确定前景，中间值=边界）
  const alpha = new Uint8ClampedArray(w * h)
  const EDGE_R = 3  // 边缘羽化半径（px）
  for (let i = 0; i < w * h; i++) alpha[i] = visited[i] ? 0 : 255

  // 对边界像素做羽化：找每个背景像素到最近前景像素的曼哈顿距离
  const dist = new Int16Array(w * h)
  dist.fill(9999)
  const fq = []
  for (let i = 0; i < w * h; i++) {
    if (alpha[i] > 0) { dist[i] = 0; fq.push(i) }
  }
  // 多源 BFS 计算到前景的距离
  for (let s = 0; s < fq.length; s++) {
    const i = fq[s]
    const x = i % w, y = (i - x) / w
    const nd = dist[i] + 1
    if (y > 0 && dist[i - w] > nd) { dist[i - w] = nd; fq.push(i - w) }
    if (y < h - 1 && dist[i + w] > nd) { dist[i + w] = nd; fq.push(i + w) }
    if (x > 0 && dist[i - 1] > nd) { dist[i - 1] = nd; fq.push(i - 1) }
    if (x < w - 1 && dist[i + 1] > nd) { dist[i + 1] = nd; fq.push(i + 1) }
  }
  // 在 EDGE_R 范围内用距离加权 alpha
  for (let i = 0; i < w * h; i++) {
    if (dist[i] <= EDGE_R) {
      alpha[i] = Math.round((dist[i] / (EDGE_R + 1)) * 255)
    }
  }

  // Step 4：应用 alpha 到图像数据
  for (let i = 0; i < w * h; i++) {
    d[i * 4 + 3] = alpha[i]
  }
  ctx.putImageData(im, 0, 0)
}
function brightenCtx(ctx, w, h) {
  const im = ctx.getImageData(0, 0, w, h)
  const d = im.data
  for (let i = 0; i < d.length; i += 4) {
    if (d[i + 3] < 12) continue
    d[i] = Math.min(255, d[i] * 1.08 + 9)
    d[i + 1] = Math.min(255, d[i + 1] * 1.08 + 9)
    d[i + 2] = Math.min(255, d[i + 2] * 1.08 + 9)
  }
  ctx.putImageData(im, 0, 0)
}

async function generate() {
  const srcCv = cropCanvas.value
  if (!srcCv) return
  drawCrop()
  const { w, h } = curSize.value
  if (!w || !h || w < 100 || h < 100) { ElMessage.error('请填写正确的宽高（≥100px）'); return }
  if (busy.value) return
  busy.value = true
  try {
    const snapshot = srcCv.getContext('2d').getImageData(0, 0, w, h)

    // 优先用 AI 人像分割（复杂背景也能抠净）；获取不到时回退算法
    let matte = null
    let usedAI = false
    if (removeBg.value) {
      matte = await getMatte()
      usedAI = !!matte
    }

    // 透明底图
    const data = new Uint8ClampedArray(snapshot.data)
    if (usedAI) applyMatte(data, w, h, matte)
    else if (removeBg.value) {
      const tc0 = document.createElement('canvas'); tc0.width = w; tc0.height = h
      const t0 = tc0.getContext('2d', { willReadFrequently: true })
      t0.putImageData(new ImageData(data, w, h), 0, 0)
      removeUniformBg(t0, w, h, tolerance.value)
      const im = t0.getImageData(0, 0, w, h)
      for (let i = 0; i < data.length; i++) data[i] = im.data[i]
    }
    const tc = document.createElement('canvas'); tc.width = w; tc.height = h
    const tctx = tc.getContext('2d', { willReadFrequently: true })
    tctx.putImageData(new ImageData(data, w, h), 0, 0)
    if (enhance.value) brightenCtx(tctx, w, h)

    // 标准照（合成底色）
    const cc = document.createElement('canvas'); cc.width = w; cc.height = h
    const cctx = cc.getContext('2d')
    if (removeBg.value) {
      cctx.fillStyle = color.value.hex
      cctx.fillRect(0, 0, w, h)
      cctx.drawImage(tc, 0, 0)
    } else {
      cctx.drawImage(tc, 0, 0)
    }

    if (result.value.show) {
      URL.revokeObjectURL(result.value.coloredUrl)
      if (result.value.transparentUrl) URL.revokeObjectURL(result.value.transparentUrl)
    }
    result.value.coloredUrl = cc.toDataURL('image/png')
    result.value.transparentUrl = removeBg.value ? tc.toDataURL('image/png') : ''
    result.value.show = true
    ElMessage.success(usedAI ? '已用 AI 人像分割抠净背景，可切换底色后重新生成或下载' : '已生成，可切换底色后重新生成或下载')
  } finally {
    busy.value = false
  }
}

// 原图尺寸的 matte 取裁剪窗内对应区域（与 drawCrop 同一几何映射），逐像素写入 alpha
function applyMatte(data, w, h, matte) {
  const img = srcImg.value
  if (!img) return
  const iw = img.naturalWidth, ih = img.naturalHeight
  const sc = Math.max(w / iw, h / ih) * zoom.value
  const cw = w / sc, chh = h / sc
  const sx = (iw - cw) / 2
  const cy = clamp(srcCy.value, chh / 2, ih - chh / 2)
  const srcW = matteW || iw
  for (let py = 0; py < h; py++) {
    const sy = ((cy - chh / 2) + chh * (py + 0.5) / h) | 0
    if (sy < 0 || sy >= ih) continue
    for (let px = 0; px < w; px++) {
      const sxSrc = (sx + cw * (px + 0.5) / w) | 0
      if (sxSrc < 0 || sxSrc >= iw) continue
      data[(py * w + px) * 4 + 3] = matte[sy * srcW + sxSrc]
    }
  }
}

function dataURLToBlob(dataUrl) {
  const parts = dataUrl.split(',')
  const b64 = parts[1]
  const bin = atob(b64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
  return new Blob([bytes], { type: 'image/png' })
}
function saveBlob(blob, name) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = name
  document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}
const outName = () => `证件照_${sizeLabel.value}_${colorName.value === '自定义' ? '自定义' : colorName.value}.png`
function downloadColored() {
  if (!result.value.coloredUrl) return
  saveBlob(dataURLToBlob(result.value.coloredUrl), outName())
}
function downloadTransparent() {
  if (!result.value.transparentUrl) return
  saveBlob(dataURLToBlob(result.value.transparentUrl), `证件照_${sizeLabel.value}_透明底.png`)
}

// 首帧适配（若某尺寸被阅/相机拍出超大图则默认适中缩放）
drawCrop()
</script>

<style scoped>
.idp-page {
  position: relative; min-height: 100vh; padding: 96px 24px 60px;
  box-sizing: border-box; font-family: var(--font-serif); color: var(--lj-text); overflow-x: hidden;
}
.idp-inner { position: relative; z-index: 1; max-width: 1080px; margin: 0 auto; }

.lj-bg { position: absolute; inset: 0; z-index: 0; pointer-events: none; overflow: hidden;
  background:
    radial-gradient(ellipse 55% 40% at 18% 6%, var(--glow-rain), transparent 60%),
    radial-gradient(ellipse 45% 40% at 85% 26%, var(--glow-gold), transparent 60%),
    var(--lj-bg); }
.lj-paper-texture { position: absolute; inset: 0; opacity: .5;
  background:
    repeating-linear-gradient(0deg, rgba(127,168,163,.02) 0 1px, transparent 1px 5px),
    repeating-linear-gradient(90deg, rgba(127,168,163,.014) 0 1px, transparent 1px 7px); }
.lj-wash { position: absolute; border-radius: 50%; filter: blur(80px); opacity: .4;
  background: radial-gradient(circle, rgba(127,168,163,.14), transparent 70%); animation: fd-drift 30s ease-in-out infinite; }
.lj-wash.w1 { width: 480px; height: 400px; top: 4%; left: -8%; }
.lj-wash.w2 { width: 420px; height: 360px; bottom: 4%; right: -8%; animation-delay: 9s; }
@keyframes fd-drift { 0%,100% { transform: translate(0,0); } 50% { transform: translate(32px,-18px); } }
@media (prefers-reduced-motion: reduce) { .lj-wash { animation: none; } }

.glass { background: var(--lj-glass); -webkit-backdrop-filter: var(--lj-glass-blur); backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line); box-shadow: var(--glass-highlight), var(--glass-shadow); }

.idp-head { display: flex; align-items: center; gap: 18px; margin-bottom: 20px; }
.idp-head-left { flex: none; }
.idp-titles { flex: 1; }
.idp-title { margin: 0; font-size: 28px; letter-spacing: .12em; }
.idp-sub { margin: 6px 0 0; font-size: 12px; color: var(--lj-text-2); letter-spacing: .18em; }

.idp-upload { padding: 26px; display: flex; flex-direction: column; gap: 14px; }
.idp-drop {
  border: 2px dashed var(--lj-line-strong); border-radius: 16px; padding: 48px 20px;
  text-align: center; cursor: pointer; background: rgba(127,168,163,.05); transition: all var(--transition);
}
.idp-drop:hover { border-color: var(--lj-seal); }
.idp-drop.dragging { border-color: var(--lj-dai); background: rgba(127,168,163,.10); }
.idp-drop-icon { font-size: 44px; margin-bottom: 10px; }
.idp-drop-text { font-size: 16px; color: var(--lj-text); letter-spacing: .06em; }
.idp-drop-hint { font-size: 12px; color: var(--lj-text-3); margin-top: 8px; }
.idp-upload-note { font-size: 11px; color: var(--lj-text-3); text-align: center; }

.idp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 18px; align-items: start; }
.idp-pane { padding: 20px; display: flex; flex-direction: column; gap: 12px; }
.idp-pane-title { margin: 0; font-size: 15px; letter-spacing: .1em; }

.idp-crop { position: relative; border-radius: 12px; overflow: hidden; border: 1px solid var(--lj-line);
  background: #0d141a; cursor: grab; touch-action: none; }
.idp-crop.panning { cursor: grabbing; }
.idp-crop-canvas { display: block; width: 100%; height: auto; max-height: 440px; margin: 0 auto; object-fit: contain;
  aspect-ratio: auto; }
.idp-crop-hint { position: absolute; left: 0; right: 0; bottom: 6px; text-align: center; font-size: 11px;
  color: rgba(220,232,228,.6); letter-spacing: .08em; pointer-events: none; text-shadow: 0 1px 3px #000; }
.idp-crop-ctl { display: flex; align-items: center; gap: 10px; }
.idp-crop-ctl-label { font-size: 12px; color: var(--lj-text-2); }
.idp-crop-ctl-val { font-size: 12px; color: var(--lj-text-3); min-width: 34px; }
.idp-range { flex: 1; accent-color: var(--lj-dai); }

.idp-text-btn { align-self: flex-start; border: none; background: none; color: var(--lj-dai); cursor: pointer; font-family: var(--font-serif); font-size: 13px; }

.idp-block { display: flex; flex-direction: column; gap: 10px; }
.idp-label { font-size: 13px; color: var(--lj-text-2); letter-spacing: .06em; }
.idp-cap { font-style: normal; font-size: 11px; color: var(--lj-text-3); }
.idp-size-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.idp-chip {
  padding: 8px 4px; border-radius: 9px; border: 1px solid var(--lj-line);
  background: rgba(127,168,163,.06); color: var(--lj-text); font-size: 13px; cursor: pointer;
  font-family: var(--font-serif); transition: all .2s;
}
.idp-chip:hover { border-color: var(--lj-seal); }
.idp-chip.active { background: var(--lj-seal); color: #101820; border-color: var(--lj-seal); font-weight: 500; }
.idp-custom { display: flex; align-items: center; gap: 8px; }
.idp-num { width: 72px; padding: 7px 10px; border-radius: 8px; border: 1px solid var(--lj-line);
  background: rgba(22,30,39,.4); color: var(--lj-text); font-family: var(--font-serif); font-size: 13px; }
.idp-x { color: var(--lj-text-3); }
.idp-hint { font-size: 11px; color: var(--lj-text-3); }

.idp-color-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.idp-color { width: 26px; height: 26px; border-radius: 50%; border: 2px solid transparent; cursor: pointer;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,.25); }
.idp-color.active { border-color: var(--lj-ochre); transform: scale(1.08); }
.idp-color-pick { position: relative; width: 26px; height: 26px; border-radius: 50%; overflow: hidden; cursor: pointer; border: 2px solid transparent; }
.idp-rainbow { position: absolute; inset: 0;
  background: conic-gradient(#fff,#e23a3a,#ffd34d,#3b73c6,#7fa8a3,#fff); }
.idp-color-input { position: absolute; inset: -10px; width: 46px; height: 46px; opacity: 0; cursor: pointer; }
.idp-color-name { font-size: 12px; color: var(--lj-text-3); }

.idp-switch-row { display: flex; align-items: center; gap: 10px; }
.idp-switch-row .idp-desc { font-size: 11px; color: var(--lj-text-3); flex: 1; }
.idp-toggle { width: 40px; height: 22px; border-radius: 20px; background: rgba(127,168,163,.25); position: relative; cursor: pointer; transition: background .2s; flex: none; }
.idp-toggle i { position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; border-radius: 50%; background: #cfd8d5; transition: all .2s; }
.idp-toggle.on { background: var(--lj-seal); }
.idp-toggle.on i { left: 20px; background: #fff; }

.idp-generate { margin-top: 4px; padding: 13px; border: none; border-radius: 11px; cursor: pointer;
  background: linear-gradient(135deg, var(--lj-dai), var(--lj-dai-deep)); color: #101820;
  font-family: var(--font-serif); font-size: 15px; letter-spacing: .1em; font-weight: 500; transition: all .25s; }
.idp-generate:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 8px 22px rgba(127,168,163,.35); }
.idp-generate:disabled { opacity: .55; cursor: not-allowed; }

.idp-result { padding: 20px; display: flex; flex-direction: column; gap: 16px; }
.idp-result-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.idp-badge { font-size: 11px; color: var(--lj-ochre); border: 1px solid rgba(199,169,107,.4); padding: 4px 12px; border-radius: 30px; background: rgba(199,169,107,.10); }
.idp-result-body { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.idp-card { display: flex; flex-direction: column; gap: 10px; }
.idp-card-tag { font-size: 12px; color: var(--lj-text-2); }
.idp-stage { flex: 1; min-height: 260px; display: flex; align-items: center; justify-content: center; border-radius: 12px; overflow: hidden; border: 1px solid var(--lj-line); }
.idp-stage.grid-bg { background: repeating-conic-gradient(#3a434b 0% 25%, #2a3138 0% 50%) 0 0 / 18px 18px; }
.idp-stage img { max-width: 100%; max-height: 340px; }
.idp-card-ops { display: flex; gap: 10px; }
.idp-btn { padding: 9px 22px; border: none; border-radius: 9px; cursor: pointer;
  background: var(--lj-dai); color: #101820; font-family: var(--font-serif); font-size: 13px; transition: all .2s; }
.idp-btn.ghost { background: rgba(127,168,163,.10); border: 1px solid var(--lj-line-strong); color: var(--lj-text); }
.idp-btn:hover:not(:disabled) { transform: translateY(-1px); }
.idp-btn:disabled { opacity: .55; cursor: not-allowed; }
.idp-result-tip { font-size: 11px; color: var(--lj-text-3); }

.idp-fade-enter-active, .idp-fade-leave-active { transition: opacity .25s ease; }
.idp-fade-enter-from, .idp-fade-leave-to { opacity: 0; }

@media (max-width: 700px) {
  .idp-page { padding: 88px 14px 50px; }
  .idp-grid { grid-template-columns: 1fr; }
  .idp-result-body { grid-template-columns: 1fr; }
  .idp-size-grid { grid-template-columns: repeat(3, 1fr); }
}
</style>