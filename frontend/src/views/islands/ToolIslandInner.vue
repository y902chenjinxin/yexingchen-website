<template>
  <IslandInnerBase
    type="tool"
    title="工具岛 · 机关百变"
    subtitle="匠心独运，妙用无穷"
    @back="$emit('back')"
  >
    <div class="tool-content">
      <!-- 齿轮机关装饰 -->
      <div class="gears-decoration">
        <div class="gear" v-for="i in 6" :key="i" :class="`gear-${i}`"></div>
      </div>

      <!-- 零件悬浮 -->
      <div class="parts-floating">
        <div v-for="i in 10" :key="i" class="part" :style="getPartStyle(i)"></div>
      </div>

      <!-- 视频去水印 -->
      <div class="parse-area">
        <div class="parse-head">
          <span class="parse-title">🎬 视频去水印</span>
          <span class="parse-sub">支持抖音 / 快手 / 小红书等平台分享链接</span>
        </div>
        <div class="parse-input-row">
          <input
            v-model="link"
            class="parse-input"
            type="text"
            placeholder="粘贴视频分享链接，如 https://v.douyin.com/xxxx"
            @keyup.enter="doParse"
          />
          <button class="parse-btn" :disabled="parsing" @click="doParse">
            {{ parsing ? '解析中…' : '解析' }}
          </button>
        </div>

        <transition name="fade-drop">
          <div v-if="errorMsg" class="parse-error">{{ errorMsg }}</div>
        </transition>

        <transition name="fade-drop">
          <div v-if="result" class="parse-result">
            <div class="parse-meta">
              <span class="parse-name">{{ result.title || '（无标题）' }}</span>
              <span v-if="result.author && result.author.name" class="parse-author">@{{ result.author.name }}</span>
            </div>
            <video v-if="result.video_url" :src="result.video_url" controls playsinline class="parse-video" />
            <div v-else-if="result.images && result.images.length" class="parse-grid">
              <img v-for="(img, i) in result.images" :key="i" :src="img.url || img" class="parse-thumb" alt="图集图片" />
            </div>
            <div class="parse-actions">
              <a v-if="result.video_url" class="parse-dl" :href="result.video_url" target="_blank" rel="noopener noreferrer" @click.prevent="download($event, result.video_url)">⬇ 下载视频</a>
              <a v-if="result.music_url" class="parse-dl" :href="result.music_url" target="_blank" rel="noopener noreferrer" @click.prevent="download($event, result.music_url)">🎵 下载音频</a>
              <a v-if="result.cover_url" class="parse-dl" :href="result.cover_url" target="_blank" rel="noopener noreferrer" @click.prevent="download($event, result.cover_url)">🖼 下载封面</a>
            </div>
            <div class="parse-note">请在权利允许范围内使用，仅供个人学习参考。</div>
          </div>
        </transition>
      </div>

      <!-- 工具列表 -->
      <div class="tool-list-area">
        <div v-if="toolStore.loading" class="loading-state">
          <span class="loading-text">洞天正在解锁机关...</span>
        </div>
        <div v-else-if="!toolStore.list || toolStore.list.length === 0" class="empty-state">
          <span class="empty-icon">⚙️</span>
          <span class="empty-text">暂无机关启用，静待天机显现</span>
        </div>
        <div v-else class="tool-items">
          <div
            v-for="(item, index) in toolStore.list"
            :key="item.id"
            class="tool-item"
            :style="getItemStyle(index)"
          >
            <div class="tool-icon">
              <span>{{ getToolIcon(item.type) }}</span>
            </div>
            <div class="tool-info">
              <span class="tool-name">{{ item.name || '无名工具' }}</span>
              <span class="tool-desc">{{ item.description || '暂无描述' }}</span>
            </div>
            <div class="tool-status">
              <span class="status-dot" :class="{ active: item.enabled }"></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import IslandInnerBase from './IslandInnerBase.vue'
import { useToolStore } from '@/stores/tool'
import { parseVideoUrl, parseErrorMsg } from '@/api/videoParse'

defineEmits(['back'])

const toolStore = useToolStore()

// 视频去水印状态
const link = ref('')
const parsing = ref(false)
const errorMsg = ref('')
const result = ref(null)

async function doParse() {
  const url = (link.value || '').trim()
  if (!url) { errorMsg.value = '请先粘贴视频分享链接'; return }
  parsing.value = true
  errorMsg.value = ''
  result.value = null
  try {
    const res = await parseVideoUrl(url)
    result.value = res.data || {}
  } catch (e) {
    errorMsg.value = parseErrorMsg(e)
  } finally {
    parsing.value = false
  }
}

function download(e, url) {
  e.preventDefault()
  if (!url) return
  window.open(url, '_blank', 'noopener,noreferrer')
}

onMounted(async () => {
  await toolStore.fetchList()
})

const seededRandom = (seed) => {
  const x = Math.sin(seed * 12.9898) * 43758.5453
  return x - Math.floor(x)
}

const getPartStyle = (i) => {
  const seed = i * 5678.901
  const random = seededRandom(seed)

  return {
    left: `${random * 100}%`,
    top: `${10 + seededRandom(seed * 2) * 60}%`,
    width: `${8 + random * 16}px`,
    height: `${8 + random * 16}px`,
    animationDelay: `${random * 6}s`,
    opacity: 0.2 + random * 0.3,
    borderRadius: random > 0.5 ? '50%' : '2px',
    transform: `rotate(${random * 360}deg)`
  }
}

const getItemStyle = (index) => {
  const seed = index * 6789.012
  const random = seededRandom(seed)

  return {
    animationDelay: `${random * 0.3}s`
  }
}

const getToolIcon = (type) => {
  const icons = {
    generator: '⚡',
    converter: '🔄',
    analyzer: '📊',
    utility: '🔧',
    other: '🎛️'
  }
  return icons[type] || '🔧'
}
</script>

<style scoped>
.tool-content {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.gears-decoration {
  position: absolute;
  top: 10%;
  left: 5%;
  width: 250px;
  height: 200px;
  pointer-events: none;
}

.gear {
  position: absolute;
  border: 3px solid #a5825a;
  border-radius: 50%;
  opacity: 0.2;
}

.gear-1 {
  width: 100px;
  height: 100px;
  top: 20%;
  left: 10%;
  animation: rotate-gear 12s linear infinite;
}

.gear-2 {
  width: 70px;
  height: 70px;
  top: 50%;
  left: 45%;
  animation: rotate-gear 9s linear infinite reverse;
}

.gear-3 {
  width: 55px;
  height: 55px;
  top: 10%;
  right: 20%;
  animation: rotate-gear 8s linear infinite;
}

.gear-4 {
  width: 45px;
  height: 45px;
  bottom: 20%;
  left: 30%;
  animation: rotate-gear 7s linear infinite reverse;
}

.gear-5 {
  width: 35px;
  height: 35px;
  bottom: 30%;
  right: 15%;
  animation: rotate-gear 6s linear infinite;
}

.gear-6 {
  width: 50px;
  height: 50px;
  top: 35%;
  left: 60%;
  animation: rotate-gear 10s linear infinite reverse;
}

@keyframes rotate-gear {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.parts-floating {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.part {
  position: absolute;
  background: #a5825a;
  animation: float-part 10s ease-in-out infinite;
  will-change: transform, opacity;
}

@keyframes float-part {
  0%, 100% {
    transform: translateY(0) rotate(var(--rotate, 0deg));
    opacity: 0.3;
  }
  50% {
    transform: translateY(-30px) rotate(calc(var(--rotate, 0deg) + 180deg));
    opacity: 0.6;
  }
}

.tool-list-area {
  background: var(--ls-glass);
  backdrop-filter: saturate(160%) blur(14px);
  -webkit-backdrop-filter: saturate(160%) blur(14px);
  border: 1px solid var(--ls-line);
  border-radius: var(--radius);
  padding: 30px;
  min-height: 300px;
  box-shadow: inset 0 1px 0 var(--ls-highlight), var(--ls-shadow);
}

/* 视频去水印面板 */
.parse-area {
  background: var(--ls-glass);
  backdrop-filter: saturate(160%) blur(14px);
  -webkit-backdrop-filter: saturate(160%) blur(14px);
  border: 1px solid var(--ls-line);
  border-radius: var(--radius);
  padding: 24px 28px;
  box-shadow: inset 0 1px 0 var(--ls-highlight), var(--ls-shadow);
}

.parse-head { display: flex; align-items: baseline; gap: 14px; margin-bottom: 16px; flex-wrap: wrap; }
.parse-title { font-family: var(--font-serif); font-size: 17px; color: var(--ls-text); letter-spacing: 0.04em; }
.parse-sub { font-size: 12px; color: var(--ls-text-3); }

.parse-input-row { display: flex; gap: 12px; }
.parse-input {
  flex: 1;
  padding: 11px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--ls-line);
  background: var(--ls-paper-1);
  color: var(--ls-text);
  font-size: 14px;
  outline: none;
  transition: border-color var(--transition);
}
.parse-input:focus { border-color: var(--ls-dai); }
.parse-input::placeholder { color: var(--ls-text-3); }

.parse-btn {
  flex: none;
  padding: 0 22px;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--ls-dai);
  color: var(--ls-bg1);
  font-size: 14px;
  cursor: pointer;
  transition: all var(--transition);
}
.parse-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(112, 192, 214, 0.4); }
.parse-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; box-shadow: none; }

.parse-error {
  margin-top: 14px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  background: rgba(200, 80, 60, 0.12);
  border: 1px solid rgba(200, 80, 60, 0.35);
  color: #e28a78;
  font-size: 13px;
}

.parse-result { margin-top: 18px; }
.parse-meta { display: flex; align-items: baseline; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.parse-name { font-family: var(--font-serif); font-size: 15px; color: var(--ls-text); }
.parse-author { font-size: 12px; color: var(--ls-text-2); }

.parse-video {
  width: 100%;
  max-height: 320px;
  border-radius: var(--radius-sm);
  background: #000;
  outline: none;
}

.parse-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; }
.parse-thumb { width: 100%; aspect-ratio: 3/4; object-fit: cover; border-radius: var(--radius-sm); }

.parse-actions { display: flex; gap: 12px; margin-top: 14px; flex-wrap: wrap; }
.parse-dl {
  display: inline-block;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  background: var(--ls-paper-2);
  border: 1px solid var(--ls-line-strong);
  color: var(--ls-dai);
  font-size: 13px;
  text-decoration: none;
  transition: all var(--transition);
}
.parse-dl:hover { border-color: var(--ls-dai); transform: translateY(-1px); }

.parse-note { margin-top: 12px; font-size: 12px; color: var(--ls-text-3); }

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 16px;
}

.loading-text,
.empty-text {
  color: var(--ls-text-3);
  font-size: 14px;
}

.empty-icon {
  font-size: 48px;
  opacity: 0.5;
}

.tool-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tool-item {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px 20px;
  background: linear-gradient(165deg, rgba(255,255,255,.03), rgba(255,255,255,0) 55%), var(--ls-glass);
  border: 1px solid var(--ls-line);
  border-radius: var(--radius-sm);
  box-shadow: inset 0 1px 0 var(--ls-highlight), var(--ls-shadow);
  backdrop-filter: saturate(150%) blur(10px);
  -webkit-backdrop-filter: saturate(150%) blur(10px);
  transition: all var(--transition);
  animation: slide-in 0.5s ease-out backwards;
  cursor: pointer;
}

.tool-item:hover {
  background: var(--ls-paper-2);
  border-color: var(--ls-line-strong);
  transform: translateX(8px);
}

@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.tool-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(
    135deg,
    #a5825a 0%,
    rgba(196, 154, 108, 0.3) 100%
  );
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}

.tool-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.tool-name {
  font-family: var(--font-serif);
  color: var(--ls-text);
  font-size: 16px;
}

.tool-desc {
  color: var(--ls-text-2);
  font-size: 13px;
}

.tool-status {
  display: flex;
  align-items: center;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--ls-text-3);
  transition: all var(--transition);
}

.status-dot.active {
  background: var(--ls-jade);
  box-shadow: 0 0 10px var(--ls-jade);
}
</style>