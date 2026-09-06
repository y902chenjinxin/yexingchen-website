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
          <p class="idp-sub">智能抠底 · 随心换色 · 多尺寸即出</p>
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
        <div class="idp-upload-note">照片仅用于本工具推理，不写入你的资料库</div>
      </section>

      <!-- 第二步：工作区 -->
      <template v-else>
        <div class="idp-grid">
          <!-- 原图 -->
          <section class="glass idp-pane">
            <h2 class="idp-pane-title">原图</h2>
            <div class="idp-preview"><img :src="srcUrl" alt="原图" /></div>
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
                  :class="{ active: size.key === s.key }"
                  @click="size = s"
                >{{ s.label }}</button>
                <button class="idp-chip" :class="{ active: custom.on }" @click="custom.on = true">自定义</button>
              </div>
              <div v-if="custom.on" class="idp-custom">
                <input v-model.number="custom.w" type="number" min="100" class="idp-num" placeholder="宽" />
                <span class="idp-x">×</span>
                <input v-model.number="custom.h" type="number" min="100" class="idp-num" placeholder="高" />
                <span class="idp-hint">px · 300dpi</span>
              </div>
            </div>

            <div class="idp-block">
              <span class="idp-label">背景色</span>
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

            <div class="idp-block">
              <label class="idp-switch-row">
                <span>智能修图</span>
                <span class="idp-desc">人脸矫正 · 细节优化</span>
                <span class="idp-toggle" :class="{ on: enhance }" @click="enhance = !enhance"><i></i></span>
              </label>
            </div>

            <button class="idp-generate" :disabled="busy" @click="generate">
              {{ busy ? generatingText : '开始生成证件照' }}
            </button>
          </section>
        </div>

        <!-- 第三步：结果 -->
        <section v-if="result.show" class="glass idp-result">
          <div class="idp-result-head">
            <h2 class="idp-pane-title">生成结果</h2>
            <span class="idp-badge">已生成 · 可下载</span>
          </div>

          <div class="idp-result-body">
            <!-- 标准照（带底色） -->
            <div class="idp-card">
              <span class="idp-card-tag">标准照 · {{ sizeLabel }}</span>
              <div class="idp-stage" :style="{ background: stageBg }">
                <img :src="result.standardUrl" alt="标准照" />
              </div>
              <div class="idp-card-ops">
                <button class="idp-btn" @click="download('standard')" :disabled="busy">下载</button>
                <button class="idp-btn ghost" @click="downloadRaw('standard')">透明底</button>
              </div>
            </div>

            <!-- 高清照 -->
            <div class="idp-card">
              <span class="idp-card-tag">高清照 · {{ sizeLabel }}</span>
              <div class="idp-stage" :style="{ background: stageBg }">
                <img :src="result.hdUrl" alt="高清照" />
              </div>
              <div class="idp-card-ops">
                <button class="idp-btn" @click="download('hd')" :disabled="busy">下载</button>
                <button class="idp-btn ghost" @click="downloadRaw('hd')">透明底</button>
              </div>
            </div>
          </div>

          <div class="idp-result-tip">提示：标准照与高清照均为透明底 PNG；下载时自动应用所选背景色（白色默认）。</div>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import BackButton from '@/components/BackButton.vue'

const API = '/api/tool/idphoto'

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
const generatingText = ref('')
const srcUrl = ref('')
const srcFile = ref(null)
const size = ref(sizeOptions[0])
const custom = reactive({ on: false, w: 400, h: 500 })
const color = ref(colors[0])
const enhance = ref(true)
const result = ref({ show: false, standardUrl: '', hdUrl: '', standardRaw: '', hdRaw: '' })

const curSize = computed(() => (custom.on ? { label: `${custom.w}×${custom.h}`, w: custom.w, h: custom.h } : size.value))
const sizeLabel = computed(() => curSize.value.label)
// 舞台底色：透明底用棋盘格，否则显示所选背景
const stageBg = computed(() => {
  if (color.value.hex && color.value.hex !== '#FFFFFF') return color.value.hex
  return 'repeating-conic-gradient(#3a434b 0% 25%, #2a3138 0% 50%) 0 0 / 16px 16px'
})

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
function handleFile(f) {
  if (!/^image\/(jpeg|png|webp)$/i.test(f.type)) { ElMessage.error('仅支持 JPG / PNG 图片'); return }
  if (f.size > 20 * 1024 * 1024) { ElMessage.error('图片超过 20MB，请压缩后重试'); return }
  srcUrl.value = URL.createObjectURL(f)
  srcFile.value = f
}
function resetUpload() {
  if (srcUrl.value) URL.revokeObjectURL(srcUrl.value)
  srcUrl.value = ''
  srcFile.value = null
  result.value.show = false
}

function apiCall(endpoint, form) {
  return fetch(`${API}/${endpoint}`, { method: 'POST', body: form }).then(async (r) => {
    const j = await r.json()
    if (!r.ok || j.status === false) throw new Error((j && j.detail) || '处理失败，请检查照片为正面单人像')
    return j
  })
}
function b64ToUrl(b64) {
  const b64s = b64.replace(/^data:image\/\w+;base64,/, '')
  const bytes = Uint8Array.from(atob(b64s), (c) => c.charCodeAt(0))
  const blob = new Blob([bytes], { type: 'image/png' })
  return URL.createObjectURL(blob)
}
function blobOfB64(b64, name) {
  const b64s = b64.replace(/^data:image\/\w+;base64,/, '')
  const bytes = Uint8Array.from(atob(b64s), (c) => c.charCodeAt(0))
  return new Blob([bytes], { type: 'image/png' })
}
function saveBlob(blob, name) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = name
  document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}

async function generate() {
  if (!srcFile.value) return
  const { w, h } = curSize.value
  if (!w || !h || w < 100 || h < 100) { ElMessage.error('请填写正确的宽高（≥100px）'); return }
  busy.value = true
  generatingText.value = '正在抠底生成…（约需数秒）'
  try {
    const form = new FormData()
    form.append('input_image', srcFile.value)
    form.append('width', String(w))
    form.append('height', String(h))
    form.append('hd', 'true')
    form.append('dpi', '300')
    form.append('face_align', enhance.value ? 'true' : 'false')
    form.append('whitening_strength', enhance.value ? '20' : '0')
    const r = await apiCall('idphoto', form)
    // 刷新对象链接
    if (result.value.show) {
      URL.revokeObjectURL(result.value.standardUrl)
      URL.revokeObjectURL(result.value.hdUrl)
    }
    result.value.standardRaw = r.image_base64_standard
    result.value.hdRaw = r.image_base64_hd || ''
    result.value.standardUrl = b64ToUrl(r.image_base64_standard)
    result.value.hdUrl = r.image_base64_hd ? b64ToUrl(r.image_base64_hd) : ''
    result.value.show = true
    ElMessage.success('证件照已生成，可换底色或下载')
  } catch (e) {
    ElMessage.error(e.message || '生成失败，请重试')
  } finally {
    busy.value = false
    generatingText.value = ''
  }
}

async function download(kind) {
  const raw = kind === 'standard' ? result.value.standardRaw : result.value.hdRaw
  if (!raw) return
  busy.value = true
  generatingText.value = '正在合成背景色…'
  try {
    const form = new FormData()
    form.append('input_image_base64', raw.replace(/^data:image\/\w+;base64,/, ''))
    form.append('color', color.value.hex.replace('#', ''))
    form.append('dpi', '300')
    const r = await apiCall('add_background', form)
    const name = `证件照_${sizeLabel.value}_${color.value.name || '自定义'}.png`
    saveBlob(blobOfB64(r.image_base64), name)
    ElMessage.success('已下载')
  } catch (e) {
    ElMessage.error(e.message || '换底失败，请重试')
  } finally {
    busy.value = false
    generatingText.value = ''
  }
}
function downloadRaw(kind) {
  const raw = kind === 'standard' ? result.value.standardRaw : result.value.hdRaw
  if (!raw) return
  saveBlob(blobOfB64(raw), `证件照_${sizeLabel.value}_透明底.png`)
}

// 颜色名称联动
const colorName = computed(() => colors.find((c) => c.hex.toLowerCase() === color.value.hex.toLowerCase())?.name || '自定义')
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

/* 页头 */
.idp-head { display: flex; align-items: center; gap: 18px; margin-bottom: 20px; }
.idp-head-left { flex: none; }
.idp-titles { flex: 1; }
.idp-title { margin: 0; font-size: 28px; letter-spacing: .12em; }
.idp-sub { margin: 6px 0 0; font-size: 12px; color: var(--lj-text-2); letter-spacing: .18em; }

/* 上传 */
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

/* 网格 */
.idp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 18px; }
.idp-pane { padding: 20px; display: flex; flex-direction: column; gap: 14px; }
.idp-pane-title { margin: 0; font-size: 15px; letter-spacing: .1em; }

.idp-preview { flex: 1; min-height: 220px; display: flex; align-items: center; justify-content: center; border-radius: 12px; overflow: hidden;
  background: repeating-conic-gradient(#3a434b 0% 25%, #2a3138 0% 50%) 0 0 / 18px 18px; border: 1px solid var(--lj-line); }
.idp-preview img { max-width: 100%; max-height: 360px; }
.idp-text-btn { align-self: flex-start; border: none; background: none; color: var(--lj-dai); cursor: pointer; font-family: var(--font-serif); font-size: 13px; }

.idp-block { display: flex; flex-direction: column; gap: 10px; }
.idp-label { font-size: 13px; color: var(--lj-text-2); letter-spacing: .06em; }
.idp-size-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.idp-chip {
  padding: 8px 4px; border-radius: 9px; border: 1px solid var(--lj-line);
  background: rgba(127,168,163,.06); color: var(--lj-text); font-size: 13px; cursor: pointer;
  font-family: var(--font-serif); transition: all .2s;
}
.idp-chip:hover { border-color: var(--lj-dai); }
.idp-chip.active { background: var(--lj-dai); color: #101820; border-color: var(--lj-dai); font-weight: 500; }
.idp-custom { display: flex; align-items: center; gap: 8px; }
.idp-num {
  width: 72px; padding: 7px 10px; border-radius: 8px; border: 1px solid var(--lj-line);
  background: rgba(22,30,39,.4); color: var(--lj-text); font-family: var(--font-serif); font-size: 13px;
}
.idp-x { color: var(--lj-text-3); }
.idp-hint { font-size: 11px; color: var(--lj-text-3); }

.idp-color-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.idp-color {
  width: 30px; height: 30px; border-radius: 50%; border: 2px solid transparent; cursor: pointer;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,.25);
}
.idp-color.active { border-color: var(--lj-ochre); transform: scale(1.08); }
.idp-color-pick { position: relative; width: 30px; height: 30px; border-radius: 50%; overflow: hidden; cursor: pointer;
  border: 2px solid transparent; }
.idp-rainbow { position: absolute; inset: 0;
  background: conic-gradient(#fff,#e23a3a,#ffd34d,#3b73c6,#7fa8a3,#fff); }
.idp-color-input { position: absolute; inset: -10px; width: 50px; height: 50px; opacity: 0; cursor: pointer; }
.idp-color-name { font-size: 12px; color: var(--lj-text-3); }

.idp-switch-row { display: flex; align-items: center; gap: 10px; }
.idp-switch-row .idp-desc { font-size: 11px; color: var(--lj-text-3); flex: 1; }
.idp-toggle { width: 40px; height: 22px; border-radius: 20px; background: rgba(127,168,163,.25); position: relative; cursor: pointer; transition: background .2s; flex: none; }
.idp-toggle i { position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; border-radius: 50%; background: #cfd8d5; transition: all .2s; }
.idp-toggle.on { background: var(--lj-dai); }
.idp-toggle.on i { left: 20px; background: #fff; }

.idp-generate {
  margin-top: 4px; padding: 13px; border: none; border-radius: 11px; cursor: pointer;
  background: linear-gradient(135deg, var(--lj-dai), var(--lj-dai-deep)); color: #101820;
  font-family: var(--font-serif); font-size: 15px; letter-spacing: .1em; font-weight: 500;
  transition: all .25s;
}
.idp-generate:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 8px 22px rgba(127,168,163,.35); }
.idp-generate:disabled { opacity: .55; cursor: not-allowed; }

/* 结果 */
.idp-result { padding: 20px; display: flex; flex-direction: column; gap: 16px; }
.idp-result-head { display: flex; align-items: center; justify-content: space-between; }
.idp-badge { font-size: 11px; color: var(--lj-ochre); border: 1px solid rgba(199,169,107,.4); padding: 4px 12px; border-radius: 30px; background: rgba(199,169,107,.10); }
.idp-result-body { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.idp-card { display: flex; flex-direction: column; gap: 10px; }
.idp-card-tag { font-size: 12px; color: var(--lj-text-2); }
.idp-stage { flex: 1; min-height: 260px; display: flex; align-items: center; justify-content: center; border-radius: 12px; overflow: hidden;
  border: 1px solid var(--lj-line); }
.idp-stage img { max-width: 100%; max-height: 340px; }
.idp-card-ops { display: flex; gap: 10px; }
.idp-btn {
  padding: 9px 22px; border: none; border-radius: 9px; cursor: pointer;
  background: var(--lj-dai); color: #101820; font-family: var(--font-serif); font-size: 13px; transition: all .2s;
}
.idp-btn.ghost { background: rgba(127,168,163,.10); border: 1px solid var(--lj-line-strong); color: var(--lj-text); }
.idp-btn:hover:not(:disabled) { transform: translateY(-1px); }
.idp-btn:disabled { opacity: .55; cursor: not-allowed; }
.idp-result-tip { font-size: 11px; color: var(--lj-text-3); }

@media (max-width: 700px) {
  .idp-page { padding: 88px 14px 50px; }
  .idp-grid { grid-template-columns: 1fr; }
  .idp-result-body { grid-template-columns: 1fr; }
  .idp-size-grid { grid-template-columns: repeat(3, 1fr); }
}
</style>