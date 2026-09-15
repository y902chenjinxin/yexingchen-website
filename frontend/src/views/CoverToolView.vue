<template>
  <IslandInnerBase type="tool" title="AI 封面" subtitle="输入标题，一键生成公众号 / 小红书 / 视频封面">
    <div class="cover-tool">
      <!-- 左：参数表单 -->
      <section class="cv-form">
        <label class="cv-label">
          <span class="cv-label-text">标题 <i class="cv-count">{{ title.length }}/40</i></span>
          <input v-model="title" class="cv-input" maxlength="40" placeholder="如：山月不知心底事" @input="queueRender" />
        </label>

        <label class="cv-label">
          <span class="cv-label-text">副标题 <i class="cv-count">{{ subtitle.length }}/60</i></span>
          <input v-model="subtitle" class="cv-input" maxlength="60" placeholder="可留空" @input="queueRender" />
        </label>

        <div class="cv-label">
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

        <div class="cv-label">
          <span class="cv-label-text">版式</span>
          <div class="cv-opts">
            <button
              v-for="l in presets.layouts" :key="l.key"
              class="cv-opt" :class="{ active: layout === l.key }"
              type="button" @click="pick('layout', l.key)"
            >{{ l.label }}</button>
          </div>
        </div>

        <div class="cv-label">
          <span class="cv-label-text">主题</span>
          <div class="cv-opts">
            <button
              v-for="t in presets.themes" :key="t.key"
              class="cv-opt cv-theme" :class="{ active: theme === t.key }"
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
        <div class="cv-stage" :class="{ loading: rendering }">
          <img v-if="image" :src="image" class="cv-img" alt="封面预览" />
          <div v-else class="cv-empty">{{ rendering ? '渲染中…' : '填写标题后自动生成预览' }}</div>
          <transition name="fade">
            <div v-if="rendering" class="cv-mask">渲染中…</div>
          </transition>
        </div>
        <div class="cv-actions">
          <button class="cv-btn" :disabled="!image || rendering" @click="download">下载 PNG</button>
          <button class="cv-btn ghost" :disabled="rendering" @click="renderNow(true)">强制重渲</button>
        </div>
        <p v-if="errMsg" class="cv-err">{{ errMsg }}</p>
      </section>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { reactive, ref, onMounted, onUnmounted } from 'vue'
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
let seq = 0  // 竞态保护：慢响应不覆盖新结果

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
  } catch { /* 选择器为空时按钮不显示，错误已由拦截器提示 */ }
  renderNow()
})
onUnmounted(() => clearTimeout(timer))
</script>

<style scoped>
.cover-tool {
  display: grid;
  grid-template-columns: minmax(300px, 420px) minmax(0, 1fr);
  gap: 28px;
  align-items: start;
}
@media (max-width: 900px) {
  .cover-tool { grid-template-columns: 1fr; }
}

/* ---- 表单 ---- */
.cv-form { display: flex; flex-direction: column; gap: 18px; }
.cv-label { display: flex; flex-direction: column; gap: 8px; }
.cv-label-text { font-size: 13px; color: var(--lj-text-2); letter-spacing: 0.06em; }
.cv-count { font-style: normal; color: var(--lj-text-3); font-size: 11px; margin-left: 6px; }
.cv-input {
  background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01)), rgba(18, 26, 34, 0.5);
  border: 1px solid var(--lj-line);
  border-radius: 10px;
  color: var(--lj-text);
  padding: 10px 14px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.cv-input:focus { border-color: var(--lj-seal); box-shadow: 0 0 0 3px var(--lj-seal-soft); }

.cv-opts { display: flex; flex-wrap: wrap; gap: 8px; }
.cv-opt {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 12px;
  border: 1px solid var(--lj-line);
  border-radius: 10px;
  background: rgba(127, 168, 163, 0.06);
  color: var(--lj-text-2);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  flex-direction: column;
  align-items: flex-start;
}
.cv-opt:hover { color: var(--lj-seal); border-color: var(--lj-seal); }
.cv-opt.active {
  color: var(--lj-seal);
  border-color: var(--lj-seal);
  background: var(--lj-seal-soft);
  box-shadow: 0 0 0 1px var(--lj-seal) inset;
}
.cv-opt-name { font-size: 12px; }
.cv-opt-dim { font-size: 10px; color: var(--lj-text-3); }
.cv-theme { flex-direction: row; align-items: center; }

/* 主题色卡小样 */
.cv-swatch {
  width: 14px; height: 14px; border-radius: 4px; flex: none;
  border: 1px solid rgba(255,255,255,0.2);
}
.sw-ink { background: linear-gradient(135deg, #141b24 55%, #d8b573 55%); }
.sw-rain { background: linear-gradient(135deg, #283e42 55%, #f2ede3 55%); }
.sw-paper { background: linear-gradient(135deg, #f0e9dc 55%, #c25450 55%); }

.cv-tip { font-size: 11px; color: var(--lj-text-3); }

/* ---- 预览 ---- */
.cv-preview { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.cv-stage {
  position: relative;
  border: 1px solid var(--lj-line);
  border-radius: 14px;
  background: rgba(18, 26, 34, 0.5);
  min-height: 220px;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
  padding: 14px;
}
.cv-img {
  max-width: 100%;
  max-height: 560px;
  border-radius: 8px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
}
.cv-empty { font-size: 13px; color: var(--lj-text-3); }
.cv-mask {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  background: rgba(10, 14, 20, 0.45);
  color: var(--lj-text-2);
  font-size: 13px;
  backdrop-filter: blur(2px);
}
.cv-actions { display: flex; gap: 10px; }
.cv-btn {
  padding: 9px 20px;
  border: 1px solid var(--lj-seal);
  border-radius: 10px;
  background: linear-gradient(135deg, var(--lj-seal), var(--lj-seal-hover));
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.cv-btn:hover:not(:disabled) { box-shadow: 0 6px 16px rgba(217, 138, 118, 0.3); transform: translateY(-1px); }
.cv-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.cv-btn.ghost { background: transparent; color: var(--lj-text-2); border-color: var(--lj-line); }
.cv-btn.ghost:hover:not(:disabled) { color: var(--lj-seal); border-color: var(--lj-seal); }
.cv-err { font-size: 12px; color: var(--lj-vermilion); }

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
