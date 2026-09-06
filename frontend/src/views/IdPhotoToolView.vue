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
function removeUniformBg(ctx, w, h, tol) {
  const im = ctx.getImageData(0, 0, w, h)
  const d = im.data
  let r = 0, g = 0, b = 0, n = 0
  const add = (x, y) => { const i = (y * w + x) * 4; r += d[i]; g += d[i + 1]; b += d[i + 2]; n++ }
  const step = Math.max(1, w >> 3)
  for (let x = 0; x < w; x += step) { add(x, 0); add(x, h - 1) }
  for (let y = 0; y < h; y += step) { add(0, y); add(w - 1, y) }
  const br = r / n, bg = g / n, bb = b / n
  const tol2 = tol * tol * 3
  const visited = new Uint8Array(w * h)
  const queue = new Array(w * h)
  let qi = 0, qe = 0
  const push = (i) => { if (!visited[i]) { visited[i] = 1; queue[qe++] = i } }
  for (let x = 0; x < w; x++) { push(x); push((h - 1) * w + x) }
  for (let y = 0; y < h; y++) { push(y * w); push(y * w + w - 1) }
  while (qi < qe) {
    const idx = queue[qi++]
    const p = idx * 4
    const dr = d[p] - br, dg = d[p + 1] - bg, db = d[p + 2] - bb
    if (dr * dr + dg * dg + db * db <= tol2) {
      d[p + 3] = 0
      const x = idx % w
      const y = (idx - x) / w
      if (y > 0) push(idx - w)
      if (y < h - 1) push(idx + w)
      if (x > 0) push(idx - 1)
      if (x < w - 1) push(idx + 1)
    }
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

function generate() {
  const srcCv = cropCanvas.value
  if (!srcCv) return
  drawCrop()
  const { w, h } = curSize.value
  if (!w || !h || w < 100 || h < 100) { ElMessage.error('请填写正确的宽高（≥100px）'); return }
  busy.value = true
  try {
    const snapshot = srcCv.getContext('2d').getImageData(0, 0, w, h)

    // 透明底图
    const tc = document.createElement('canvas'); tc.width = w; tc.height = h
    const tctx = tc.getContext('2d', { willReadFrequently: true })
    tctx.putImageData(new ImageData(new Uint8ClampedArray(snapshot.data), w, h), 0, 0)
    if (removeBg.value) removeUniformBg(tctx, w, h, tolerance.value)
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
    ElMessage.success('已生成，可切换底色后重新生成或下载')
  } finally {
    busy.value = false
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
.idp-drop:hover { border-color: var(--lj-dai); }
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
.idp-chip:hover { border-color: var(--lj-dai); }
.idp-chip.active { background: var(--lj-dai); color: #101820; border-color: var(--lj-dai); font-weight: 500; }
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
.idp-toggle.on { background: var(--lj-dai); }
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