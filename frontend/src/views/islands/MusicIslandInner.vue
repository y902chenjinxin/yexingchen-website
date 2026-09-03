<template>
  <div class="music-content">
      <!-- 古琴虚影背景 -->
      <div class="guqin-bg">
        <svg viewBox="0 0 400 100" class="guqin-svg">
          <ellipse cx="200" cy="80" rx="180" ry="20" fill="none" stroke="var(--island-music)" stroke-width="1" opacity="0.2"/>
          <ellipse cx="200" cy="80" rx="150" ry="15" fill="none" stroke="var(--island-music)" stroke-width="0.5" opacity="0.15"/>
          <line v-for="i in 7" :key="i" :x1="100 + i * 28" y1="30" :x2="100 + i * 28" y2="130" stroke="var(--island-music)" stroke-width="0.5" opacity="0.3"/>
        </svg>
      </div>

      <!-- 音符飘带装饰 -->
      <div class="music-ribbon">
        <svg viewBox="0 0 200 300" class="ribbon-svg">
          <path d="M20 0 Q60 80 100 150 T180 300" fill="none" stroke="var(--island-music)" stroke-width="2" opacity="0.2" stroke-dasharray="5,5">
            <animate attributeName="stroke-dashoffset" from="0" to="30" dur="3s" repeatCount="indefinite"/>
          </path>
          <circle v-for="i in 5" :key="i" r="4" fill="var(--island-music)" :cx="20 + i * 35" :cy="i * 60" opacity="0.3">
            <animate attributeName="cy" values="0;280;0" :dur="`${4 + i * 0.5}s`" repeatCount="indefinite"/>
          </circle>
        </svg>
      </div>

      <!-- 音乐列表 -->
      <div class="music-list-area">
        <div v-if="musicStore.loading" class="loading-state">
          <span class="loading-text">洞天正在加载天籁之音...</span>
        </div>
        <div v-else-if="!musicStore.list || musicStore.list.length === 0" class="empty-state">
          <span class="empty-icon">🎵</span>
          <span class="empty-text">暂无音乐收录，静待仙音降临</span>
        </div>
        <div v-else class="music-items">
          <div
            v-for="(item, index) in musicStore.list"
            :key="item.id"
            class="music-item"
            :style="getItemStyle(index)"
          >
            <div class="music-info">
              <span class="music-name">{{ item.title || '未知曲目' }}</span>
              <span class="music-artist">{{ item.artist || '佚名' }}</span>
            </div>
            <div class="music-actions">
              <div class="music-ops" @click.stop>
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
              <button
                class="mini-btn bgm-btn"
                :class="{ on: isCurBgm(item) }"
                title="设为背景音乐"
                @click="setAsBg(item)"
                aria-label="设为背景音乐"
              >💠</button>
              <button
                class="mini-btn play-btn"
                :class="{ playing: isCurPlaying(item) }"
                @click="handlePlay(item)"
                :title="isCurPlaying(item) ? '暂停' : '播放'"
              >{{ isCurPlaying(item) ? '❚❚' : '▶' }}</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 音符飘舞效果 -->
      <div class="floating-notes">
        <span v-for="i in 12" :key="i" class="note" :style="getNoteStyle(i)">♪</span>
      </div>

      <!-- 编辑弹窗 -->
      <el-dialog v-model="showEdit" title="编辑音乐" width="440px" append-to-body>
        <el-form label-width="56px">
          <el-form-item label="标题">
            <el-input v-model="editForm.title" placeholder="曲目标题" />
          </el-form-item>
          <el-form-item label="作者">
            <el-input v-model="editForm.artist" placeholder="作者/演奏者" />
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
import { useMusicStore } from '@/stores/music'
import { usePlayerStore } from '@/stores/player'
import { ElMessage } from 'element-plus'

const musicStore = useMusicStore()
const player = usePlayerStore()

const showEdit = ref(false)
const saving = ref(false)
const editForm = ref({ id: null, title: '', artist: '', category: '', tags: '' })

onMounted(async () => {
  await musicStore.fetchList()
})

const seededRandom = (seed) => {
  const x = Math.sin(seed * 12.9898) * 43758.5453
  return x - Math.floor(x)
}

const getNoteStyle = (i) => {
  const seed = i * 1234.5678
  const random = seededRandom(seed)

  return {
    left: `${random * 100}%`,
    top: `${10 + seededRandom(seed * 2) * 60}%`,
    animationDelay: `${random * 5}s`,
    opacity: 0.3 + random * 0.4,
    fontSize: `${16 + random * 16}px`
  }
}

const getItemStyle = (index) => {
  const seed = index * 9876.5432
  const random = seededRandom(seed)

  return {
    animationDelay: `${random * 0.3}s`,
    '--item-hue': `${random * 30}deg`
  }
}

const handlePlay = (item) => {
  player.playItem(item)
}

// 设为背景音乐（同时开始播放并持久化选择）
const setAsBg = (item) => {
  player.setBackground(item, true)
}

const isCurBgm = (item) => String(item.id) === String(player.bgmChoiceId)

const isCurPlaying = (item) =>
  player.curItem && String(player.curItem.id) === String(item.id) && player.isPlaying

function onOp(cmd, item) {
  if (cmd === 'edit') {
    editForm.value = {
      id: item.id,
      title: item.title || '',
      artist: item.artist || '',
      category: item.category || '',
      tags: item.tags || ''
    }
    showEdit.value = true
  } else if (cmd === 'delete') {
    doDelete(item)
  }
}

async function doDelete(item) {
  if (Number(item.is_default) === 1) {
    ElMessage.warning('系统默认曲不可删除')
    return
  }
  try {
    await musicStore.remove(item.id)
    ElMessage.success('已删除')
    if (String(player.bgmChoiceId) === String(item.id)) player.setBackground(null, false)
    musicStore.fetchList()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

async function saveEdit() {
  saving.value = true
  try {
    await musicStore.update(editForm.value.id, {
      title: editForm.value.title,
      artist: editForm.value.artist,
      category: editForm.value.category,
      tags: editForm.value.tags
    })
    ElMessage.success('已保存')
    showEdit.value = false
    await musicStore.fetchList()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.music-content {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.guqin-bg {
  position: absolute;
  top: 20%;
  left: 5%;
  width: 300px;
  height: 150px;
  opacity: 0.6;
  pointer-events: none;
}

.guqin-svg {
  width: 100%;
  height: 100%;
}

.music-ribbon {
  position: absolute;
  top: 0;
  right: 10%;
  width: 150px;
  height: 250px;
  opacity: 0.5;
  pointer-events: none;
}

.ribbon-svg {
  width: 100%;
  height: 100%;
}

.music-list-area {
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

.music-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.music-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: linear-gradient(165deg, rgba(255,255,255,.03), rgba(255,255,255,0) 55%), var(--ls-glass);
  border: 1px solid var(--ls-line);
  border-radius: var(--radius-sm);
  box-shadow: inset 0 1px 0 var(--ls-highlight), var(--ls-shadow);
  backdrop-filter: saturate(150%) blur(10px);
  -webkit-backdrop-filter: saturate(150%) blur(10px);
  transition: all var(--transition);
  animation: slide-in 0.5s ease-out backwards;
}

.music-item:hover {
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

.music-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.music-name {
  font-family: var(--font-serif);
  color: var(--ls-text);
  font-size: 16px;
}

.music-artist {
  color: var(--ls-text-2);
  font-size: 13px;
}

.music-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.mini-btn {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  transition: all var(--transition);
}

.play-btn {
  background: var(--ls-dai);
  color: var(--ls-bg1);
}

.play-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 0 15px var(--ls-dai);
}

.play-btn.playing {
  background: var(--ls-ochre);
  box-shadow: 0 0 15px var(--ls-ochre);
}

.bgm-btn {
  width: 32px;
  height: 32px;
  background: transparent;
  border: 1px solid var(--ls-line);
  color: var(--ls-text-2);
  font-size: 14px;
}

.bgm-btn:hover {
  background: var(--ls-paper-2);
  color: var(--ls-dai);
  transform: scale(1.1);
}

.bgm-btn.on {
  background: rgba(112, 150, 170, 0.16);
  border-color: var(--ls-dai);
  color: var(--ls-dai);
  box-shadow: 0 0 12px rgba(112, 192, 214, 0.35);
}

.music-ops {
  display: flex;
  align-items: center;
  margin-right: 2px;
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

.floating-notes {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.note {
  position: absolute;
  color: var(--ls-dai);
  animation: float-note 10s ease-in-out infinite;
  will-change: transform, opacity;
}

@keyframes float-note {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
    opacity: 0.3;
  }
  50% {
    transform: translateY(-50px) rotate(15deg);
    opacity: 0.7;
  }
}
</style>