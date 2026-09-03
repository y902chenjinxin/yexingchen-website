<template>
  <div class="video-content">
      <!-- 镜头光圈装饰 -->
      <div class="lens-aperture">
        <div class="aperture-ring" v-for="i in 4" :key="i"></div>
      </div>

      <!-- 胶片飘带 -->
      <div class="film-ribbon">
        <div v-for="i in 6" :key="i" class="film-frame" :style="getFrameStyle(i)"></div>
      </div>

      <!-- 播放器 -->
      <transition name="player-fade">
        <div v-if="playerUrl" class="video-player-wrap">
          <button class="player-close" @click="closePlayer">✕</button>
          <video :src="playerUrl" controls autoplay playsinline class="video-player"></video>
        </div>
      </transition>

      <!-- 视频列表 -->
      <div class="video-list-area">
        <div v-if="videoStore.loading" class="loading-state">
          <span class="loading-text">洞天正在加载光影...</span>
        </div>
        <div v-else-if="!videoStore.list || videoStore.list.length === 0" class="empty-state">
          <span class="empty-icon">🎬</span>
          <span class="empty-text">暂无影像收录，静待光影凝固</span>
        </div>
        <div v-else class="video-items">
          <div
            v-for="(item, index) in videoStore.list"
            :key="item.id"
            class="video-item"
            :class="{ active: isActive(item) }"
            :style="getItemStyle(index)"
            @click="playVideo(item)"
          >
            <div class="video-thumbnail">
              <span class="play-icon">▶</span>
            </div>
            <div class="video-info">
              <span class="video-title">{{ item.title || '无题' }}</span>
              <span class="video-meta">{{ item.category || '未分类' }}</span>
            </div>
            <div class="video-ops" @click.stop>
              <el-dropdown trigger="click" @command="(cmd) => onOp(cmd, item)">
                <button class="ops-btn" title="操作">⋯</button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="edit">编辑</el-dropdown-item>
                    <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </div>
      </div>

      <!-- 光圈飘动效果 -->
      <div class="floating-apertures">
        <div v-for="i in 6" :key="i" class="aperture" :style="getApertureStyle(i)"></div>
      </div>

      <!-- 编辑弹窗 -->
      <el-dialog v-model="showEdit" title="编辑视频" width="440px" append-to-body>
        <el-form label-width="56px">
          <el-form-item label="标题">
            <el-input v-model="editForm.title" placeholder="视频标题" />
          </el-form-item>
          <el-form-item label="分类">
            <el-input v-model="editForm.category" placeholder="分类" />
          </el-form-item>
          <el-form-item label="标签">
            <el-input v-model="editForm.tags" placeholder="标签，用逗号分隔" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showEdit = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
        </template>
      </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useVideoStore } from '@/stores/video'
import { ElMessage } from 'element-plus'

const videoStore = useVideoStore()

const playerUrl = ref('')
const currentId = ref(null)
const showEdit = ref(false)
const saving = ref(false)
const editForm = ref({ id: null, title: '', category: '', tags: '' })

onMounted(async () => {
  await videoStore.fetchList()
})

const isActive = (item) => String(currentId.value) === String(item.id)

function resolveStream(item) {
  const u = item.cos_url || ''
  if (u.startsWith('http://') || u.startsWith('https://')) return u
  return `/api/videos/${item.id}/stream`
}

function playVideo(item) {
  if (isActive(item)) { closePlayer(); return }
  closePlayer()
  playerUrl.value = resolveStream(item)
  currentId.value = item.id
}

function closePlayer() {
  playerUrl.value = ''
  currentId.value = null
}

function onOp(cmd, item) {
  if (cmd === 'edit') {
    editForm.value = { id: item.id, title: item.title || '', category: item.category || '', tags: item.tags || '' }
    showEdit.value = true
  } else if (cmd === 'delete') {
    doDelete(item)
  }
}

async function doDelete(item) {
  try {
    await videoStore.remove(item.id)
    ElMessage.success('已删除')
    if (isActive(item)) closePlayer()
    videoStore.fetchList()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

async function saveEdit() {
  saving.value = true
  try {
    await videoStore.update(editForm.value.id, {
      title: editForm.value.title,
      category: editForm.value.category,
      tags: editForm.value.tags
    })
    ElMessage.success('已保存')
    showEdit.value = false
    videoStore.fetchList()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const seededRandom = (seed) => {
  const x = Math.sin(seed * 12.9898) * 43758.5453
  return x - Math.floor(x)
}

const getFrameStyle = (i) => {
  const seed = i * 7890.1234
  const random = seededRandom(seed)

  return {
    animationDelay: `${random * 2}s`,
    opacity: 0.2 + random * 0.3
  }
}

const getApertureStyle = (i) => {
  const seed = i * 3456.789
  const random = seededRandom(seed)

  return {
    left: `${random * 100}%`,
    top: `${10 + seededRandom(seed * 2) * 60}%`,
    width: `${40 + random * 60}px`,
    height: `${40 + random * 60}px`,
    animationDelay: `${random * 6}s`,
    opacity: 0.1 + random * 0.2,
    borderRadius: '50%',
    border: `2px solid var(--island-video)`,
    boxShadow: `0 0 ${10 + random * 20}px var(--island-video)`
  }
}

const getItemStyle = (index) => {
  const seed = index * 8901.234
  const random = seededRandom(seed)

  return {
    animationDelay: `${random * 0.3}s`
  }
}
</script>

<style scoped>
.video-content {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.lens-aperture {
  position: absolute;
  top: 15%;
  right: 10%;
  width: 150px;
  height: 150px;
  pointer-events: none;
}

.aperture-ring {
  position: absolute;
  inset: 0;
  border: 2px solid #8a6a86;
  border-radius: 50%;
  opacity: 0.15;
  animation: aperture-pulse 4s ease-in-out infinite;
}

.aperture-ring:nth-child(1) { inset: 0; animation-delay: 0s; }
.aperture-ring:nth-child(2) { inset: 20px; animation-delay: 0.5s; }
.aperture-ring:nth-child(3) { inset: 40px; animation-delay: 1s; }
.aperture-ring:nth-child(4) { inset: 60px; animation-delay: 1.5s; }

@keyframes aperture-pulse {
  0%, 100% { opacity: 0.1; transform: scale(1); }
  50% { opacity: 0.25; transform: scale(1.05); }
}

.film-ribbon {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  gap: 20px;
  padding: 20px 40px;
  pointer-events: none;
  overflow: hidden;
}

.film-frame {
  width: 60px;
  height: 80px;
  background: linear-gradient(
    135deg,
    #8a6a86 0%,
    rgba(168, 124, 156, 0.3) 100%
  );
  border-radius: 4px;
  animation: ribbon-drift 20s linear infinite;
  flex-shrink: 0;
}

@keyframes ribbon-drift {
  from { transform: translateX(-100px); opacity: 0; }
  10% { opacity: 0.5; }
  90% { opacity: 0.5; }
  to { transform: translateX(calc(100vw + 100px)); opacity: 0; }
}

.video-list-area {
  background: var(--ls-glass);
  backdrop-filter: saturate(160%) blur(14px);
  -webkit-backdrop-filter: saturate(160%) blur(14px);
  border: 1px solid var(--ls-line);
  border-radius: var(--radius);
  padding: 30px;
  min-height: 300px;
  box-shadow: inset 0 1px 0 var(--ls-highlight), var(--ls-shadow);
}

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

.video-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.video-item {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px;
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

.video-item:hover {
  background: var(--ls-paper-2);
  border-color: var(--ls-line-strong);
  transform: translateX(8px);
}

.video-item.active {
  border-color: var(--island-video, #8a6a86);
  box-shadow: 0 0 0 1px var(--island-video, #8a6a86), var(--ls-shadow);
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

.video-thumbnail {
  width: 100px;
  height: 70px;
  background: linear-gradient(
    135deg,
    #8a6a86 0%,
    rgba(168, 124, 156, 0.3) 100%
  );
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.play-icon {
  font-size: 24px;
  color: var(--ls-bg1);
  opacity: 0.8;
}

.video-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  justify-content: center;
  flex: 1;
  min-width: 0;
}

.video-title {
  font-family: var(--font-serif);
  color: var(--ls-text);
  font-size: 16px;
}

.video-meta {
  color: var(--ls-text-2);
  font-size: 13px;
}

.video-ops {
  flex-shrink: 0;
  align-self: flex-start;
}

.ops-btn {
  width: 30px;
  height: 30px;
  border: 1px solid var(--ls-line-strong);
  border-radius: 50%;
  background: transparent;
  color: var(--ls-text-2);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  transition: all var(--transition);
}

.ops-btn:hover {
  background: var(--ls-paper-2);
  color: var(--ls-text);
}

.video-player-wrap {
  position: relative;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--ls-line-strong);
  box-shadow: var(--ls-shadow);
  background: #000;
}

.video-player {
  width: 100%;
  max-height: 320px;
  display: block;
}

.player-close {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid rgba(255,255,255,.4);
  background: rgba(0,0,0,.5);
  color: #fff;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  z-index: 2;
}

.player-fade-enter-active,
.player-fade-leave-active {
  transition: all 0.35s ease;
}

.player-fade-enter-from,
.player-fade-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}

.floating-apertures {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.aperture {
  position: absolute;
  animation: float-aperture 10s ease-in-out infinite;
  will-change: transform, opacity;
}

@keyframes float-aperture {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
    opacity: 0.2;
  }
  50% {
    transform: translateY(-40px) rotate(180deg);
    opacity: 0.5;
  }
}
</style>