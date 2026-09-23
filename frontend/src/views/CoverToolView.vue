<!--
  CoverToolView.vue
  玄黄・AI 封面工具
  - 左：参数表单（el-input / 自绘选择 chip）
  - 右：实时预览（玻璃卡片 + 鎏金描边）
  - 主题感知：昼夜两套配色统一
-->
<template>
  <IslandInnerBase type="tool" title="AI 封面" subtitle="输入标题，一键生成公众号 / 小红书 / 视频封面">
    <div class="cover-tool">
      <!-- 左：参数表单 -->
      <section class="cv-form cv-card">
        <div class="cv-field">
          <span class="cv-label-text">
            标题
            <i class="cv-count">{{ title.length }}/40</i>
          </span>
          <el-input v-model="title" maxlength="40" placeholder="如：山月不知心底事" @input="queueRender" />
        </div>

        <div class="cv-field">
          <span class="cv-label-text">
            副标题
            <i class="cv-count">{{ subtitle.length }}/60</i>
          </span>
          <el-input v-model="subtitle" maxlength="60" placeholder="可留空" @input="queueRender" />
        </div>

        <div class="cv-field">
          <span class="cv-label-text">尺寸</span>
          <div class="cv-opts">
            <button
              v-for="s in presets.sizes" :key="s.key"
              class="cv-opt" :class="{ active: size === s.key }"
              type="button" @click="pick('size', s.key)"
            >
              <span class="cv-opt-name">{{ s.label }}</span>
              <span class="cv-opt-dim">{{ s.w }}×{{ s.h }}</span>
            </button>
          </div>
        </div>

        <div class="cv-field">
          <span class="cv-label-text">版式</span>
          <div class="cv-opts">
            <button
              v-for="l in presets.layouts" :key="l.key"
              class="cv-opt cv-opt--inline" :class="{ active: layout === l.key }"
              type="button" @click="pick('layout', l.key)"
            >{{ l.label }}</button>
          </div>
        </div>

        <div class="cv-field">
          <span class="cv-label-text">主题</span>
          <div class="cv-opts">
            <button
              v-for="t in presets.themes" :key="t.key"
              class="cv-opt cv-opt--inline cv-theme" :class="{ active: theme === t.key }"
              type="button" @click="pick('theme', t.key)"
            >
              <span class="cv-swatch" :class="'sw-' + t.key"></span>{{ t.label }}
            </button>
          </div>
        </div>

        <p class="cv-tip">全部在服务器本地渲染，不上传任何数据、不消耗 AI 额度。</p>
      </section>

      <!-- 右：实时预览 -->
      <section class="cv-preview">
        <div class="cv-stage cv-card">
          <img v-if="image" :src="image" class="cv-img" alt="封面预览" />
          <div v-else class="cv-empty">{{ rendering ? '渲染中…' : '填写标题后自动生成预览' }}</div>
          <transition name="fade">
            <div v-if="rendering" class="cv-mask">
              <span class="cv-spin" aria-hidden="true"></span>
              渲染中…
            </div>
          </transition>
        </div>
        <div class="cv-actions">
          <button class="cv-btn cv-btn-primary" :disabled="!image || rendering" @click="download">
            下载 PNG
          </button>
          <button class="cv-btn cv-btn-ghost" :disabled="rendering" @click="renderNow(true)">
            强制重渲
          </button>
        </div>
        <p v-if="errMsg" class="cv-err">{{ errMsg }}</p>
      </section>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { reactive, ref, onMounted, onUnmounted } from 'vue'
import { ElInput } from 'element-plus'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import { getCoverPresets, renderCover } from '@/api/cover'

const title = ref('')
const subtitle = ref('')
const size = ref('wechat')
const layout = ref('center')
const theme = ref('ink')

const presets = reactive({ sizes: [], layouts: [], themes: [] })
const image = ref('')
const rendering = ref(false)
const errMsg = ref('')

let timer = null
let seq = 0

function queueRender() {
  clearTimeout(timer)
  timer = setTimeout(() => renderNow(), 500)
}

function pick(key, val) {
  if (key === 'size') size.value = val
  else if (key === 'layout') layout.value = val
  else if (key === 'theme') theme.value = val
  renderNow()
}

async function renderNow(force = false) {
  const t = title.value.trim()
  if (!t) { image.value = ''; return }
  if (rendering.value && !force) return
  const my = ++seq
  rendering.value = true
  errMsg.value = ''
  try {
    const res = await renderCover({ title: t, subtitle: subtitle.value.trim(), size: size.value, layout: layout.value, theme: theme.value })
    if (my === seq) image.value = res.data?.image || ''
  } catch (e) {
    if (my === seq) {
      image.value = ''
      const d = e?.detail || e?.data?.msg
      errMsg.value = (typeof d === 'string' ? d : d?.msg) || '渲染失败，请稍后重试'
    }
  } finally {
    if (my === seq) rendering.value = false
  }
}

function download() {
  if (!image.value) return
  const a = document.createElement('a')
  a.href = image.value
  a.download = `封面-${(title.value.trim() || 'cover').slice(0, 20)}-${size.value}.png`
  document.body.appendChild(a)
  a.click()
  a.remove()
}

onMounted(async () => {
  try {
    const res = await getCoverPresets()
    Object.assign(presets, res.data || {})
  } catch { /* 空时按钮不显示，错误已由拦截器提示 */ }
  renderNow()
})
onUnmounted(() => clearTimeout(timer))
</script>

<style scoped>
/* ============ 两栏布局 ============ */
.cover-tool {
  display: grid;
  grid-template-columns: minmax(300px, 420px) minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}
@media (max-width: 900px) {
  .cover-tool { grid-template-columns: 1fr; }
}

/* ============ 卡片：玻璃 + 主题感知 ============ */
.cv-card {
  padding: 22px 22px 20px;
  border-radius: 18px;
  background: var(--color-bg-glass, rgba(127, 127, 127, 0.06));
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.18));
  box-shadow: var(--dp-shadow, 0 6px 24px rgba(0, 0, 0, 0.18));
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
}

/* ============ 表单 ============ */
.cv-form { display: flex; flex-direction: column; gap: 18px; }
.cv-field { display: flex; flex-direction: column; gap: 8px; }
.cv-label-text {
  font-size: 12px;
  color: var(--lj-text-2);
  letter-spacing: .08em;
  display: flex; align-items: baseline; gap: 8px;
}
.cv-count {
  font-style: normal;
  color: var(--lj-text-3);
  font-size: 11px;
  margin-left: auto;
  letter-spacing: .04em;
}

/* ElementPlus 控件：玻璃态（与音色克隆统一风格） */
.cv-form :deep(.el-input__wrapper) {
  background: var(--color-bg-glass) !important;
  box-shadow: 0 0 0 1px var(--dp-line) inset !important;
  border-radius: 10px !important;
  padding: 2px 12px !important;
}
.cv-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--yq-gold) inset, 0 0 0 3px var(--yq-gold-faint, rgba(199, 169, 107, 0.18)) !important;
}
.cv-form :deep(.el-input__inner) {
  color: var(--lj-text) !important;
  -webkit-text-fill-color: var(--lj-text);
}
.cv-form :deep(.el-input__inner::placeholder) {
  color: var(--lj-text-3) !important;
  -webkit-text-fill-color: var(--lj-text-3);
}
.cv-form :deep(.el-input__count .el-input__count-inner) {
  color: var(--lj-text-3) !important;
  background: transparent !important;
}

/* ============ 选项 chip ============ */
.cv-opts { display: flex; flex-wrap: wrap; gap: 8px; }
.cv-opt {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  padding: 9px 14px;
  border: 1px solid var(--dp-line, rgba(127, 127, 127, 0.22));
  border-radius: 10px;
  background: var(--yq-rain-faint, rgba(127, 168, 163, 0.04));
  color: var(--lj-text-2);
  font-size: 12px;
  cursor: pointer;
  transition: all .18s ease;
  font-family: inherit;
}
.cv-opt--inline {
  flex-direction: row;
  align-items: center;
  padding: 7px 14px;
  font-size: 12px;
}
.cv-opt:hover {
  color: var(--yq-gold, #c7a96b);
  border-color: var(--yq-gold, #c7a96b);
}
.cv-opt.active {
  color: var(--yq-gold-fg, #0b0f14);
  border-color: var(--yq-gold, #c7a96b);
  background: linear-gradient(135deg, var(--yq-gold, #c7a96b), var(--yq-rain, #7fa8a3));
  box-shadow: 0 4px 12px var(--yq-gold-glow, rgba(199, 169, 107, 0.3));
  font-weight: 600;
}
.cv-opt-name { font-size: 12px; }
.cv-opt-dim {
  font-size: 10px;
  color: var(--lj-text-3);
  letter-spacing: .04em;
}
.cv-opt.active .cv-opt-dim {
  color: var(--yq-gold-fg-faint, rgba(11, 15, 20, 0.55));
}
.cv-theme { flex-direction: row; align-items: center; }

/* 主题色卡小样 */
.cv-swatch {
  width: 14px; height: 14px; border-radius: 4px; flex: none;
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.1);
}
.sw-ink { background: linear-gradient(135deg, #141b24 55%, #d8b573 55%); }
.sw-rain { background: linear-gradient(135deg, #283e42 55%, #f2ede3 55%); }
.sw-paper { background: linear-gradient(135deg, #f0e9dc 55%, #c25450 55%); }

.cv-tip {
  font-size: 11px;
  color: var(--lj-text-3);
  margin: 0;
  letter-spacing: .04em;
  line-height: 1.6;
}

/* ============ 预览 ============ */
.cv-preview { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.cv-stage {
  position: relative;
  display: flex; align-items: center; justify-content: center;
  min-height: 240px;
  padding: 18px;
  overflow: hidden;
}
.cv-img {
  max-width: 100%;
  max-height: 560px;
  border-radius: 10px;
  box-shadow: 0 12px 32px var(--yq-gold-glow, rgba(0, 0, 0, 0.35));
}
.cv-empty {
  font-size: 13px;
  color: var(--lj-text-3);
  letter-spacing: .04em;
}
.cv-mask {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; gap: 10px;
  align-items: center; justify-content: center;
  background: var(--dp-glass-deep, rgba(10, 14, 20, 0.45));
  color: var(--lj-text-2);
  font-size: 13px;
  letter-spacing: .04em;
  -webkit-backdrop-filter: blur(2px);
  backdrop-filter: blur(2px);
}
.cv-spin {
  width: 18px; height: 18px;
  border: 2px solid var(--yq-gold-fg-faint, rgba(11, 15, 20, 0.3));
  border-top-color: var(--yq-gold, #c7a96b);
  border-radius: 50%;
  animation: cv-rot .7s linear infinite;
}
@keyframes cv-rot { to { transform: rotate(360deg); } }

/* ============ 按钮 ============ */
.cv-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.cv-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  min-height: 40px;
  padding: 9px 22px;
  border-radius: 10px;
  border: 1px solid transparent;
  font-size: 13px;
  cursor: pointer;
  letter-spacing: .04em;
  transition: all .18s ease;
  font-family: inherit;
}
.cv-btn-primary {
  background: linear-gradient(135deg, var(--yq-gold, #c7a96b), var(--yq-rain, #7fa8a3));
  color: var(--yq-gold-fg, #0b0f14);
  font-weight: 600;
  box-shadow: 0 4px 14px var(--yq-gold-glow, rgba(199, 169, 107, 0.28));
}
.cv-btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 22px var(--yq-gold-glow-strong, rgba(199, 169, 107, 0.42));
}
.cv-btn-primary:active:not(:disabled) { transform: translateY(0); }
.cv-btn-primary:disabled { opacity: .45; cursor: not-allowed; box-shadow: none; }
.cv-btn-ghost {
  background: transparent;
  color: var(--lj-text-2);
  border-color: var(--dp-line, rgba(127, 127, 127, 0.3));
}
.cv-btn-ghost:hover:not(:disabled) { color: var(--lj-text); border-color: var(--yq-gold, #c7a96b); }

.cv-err {
  font-size: 12px;
  color: var(--dp-danger, #fb7185);
  margin: 0;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>