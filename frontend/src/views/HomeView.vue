<template>
  <div class="home-page">
    <!-- 背景云海 -->
    <div class="cloud-sea">
      <div class="cloud cloud-1"></div>
      <div class="cloud cloud-2"></div>
      <div class="cloud cloud-3"></div>
      <div class="cloud cloud-4"></div>
    </div>

    <!-- 顶栏 -->
    <header class="top-bar">
      <div class="top-bar-left">
        <span class="site-name font-serif">叶兴辰的个人网站</span>
      </div>
      <div class="top-bar-right">
        <el-button
          class="music-btn"
          :icon="settingsStore.musicPlaying ? 'VideoPause' : 'VideoPlay'"
          circle
          @click="toggleMusic"
        />
        <span class="username">{{ auth.user?.email }}</span>
        <el-dropdown trigger="click">
          <span class="el-dropdown-link">
            <el-icon><Setting /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-if="auth.isSuperAdmin" @click="router.push('/admin')">
                管理后台
              </el-dropdown-item>
              <el-dropdown-item @click="handleLogout">退出账号</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- 主内容：浮空岛屿 -->
    <main class="islands-container">
      <div class="island music-island" @click="router.push('/island/music')">
        <img src="@/assets/islands/music-island.svg" class="island-image" alt="音乐岛" />
        <div class="island-name">音乐岛</div>
        <div class="island-subtitle">音律飘渺</div>
        <div class="island-enter">点击进入</div>
      </div>

      <div class="island novel-island" @click="router.push('/island/novel')">
        <img src="@/assets/islands/novel-island.svg" class="island-image" alt="小说岛" />
        <div class="island-name">小说岛</div>
        <div class="island-subtitle">书卷悠长</div>
        <div class="island-enter">点击进入</div>
      </div>

      <div class="island video-island" @click="router.push('/island/video')">
        <img src="@/assets/islands/video-island.svg" class="island-image" alt="视频岛" />
        <div class="island-name">视频岛</div>
        <div class="island-subtitle">光影流转</div>
        <div class="island-enter">点击进入</div>
      </div>

      <div class="island log-island" @click="router.push('/island/log')">
        <img src="@/assets/islands/log-island.svg" class="island-image" alt="日志岛" />
        <div class="island-name">日志岛</div>
        <div class="island-subtitle">岁月留痕</div>
        <div class="island-enter">点击进入</div>
      </div>

      <div class="island tool-island" @click="router.push('/island/tool')">
        <img src="@/assets/islands/tool-island.svg" class="island-image" alt="工具岛" />
        <div class="island-name">工具岛</div>
        <div class="island-subtitle">机关万千</div>
        <div class="island-enter">点击进入</div>
      </div>
    </main>

    <!-- 全局背景音乐 -->
    <audio ref="bgAudio" :src="settingsStore.bgMusicUrl" loop preload="auto" />

    <!-- 底部岛屿切换 -->
    <div class="bottom-switcher" @click="showIslandList = true">
      <div class="switcher-hint">岛屿导航</div>
    </div>

    <!-- 岛屿切换弹层 -->
    <div class="island-modal" v-if="showIslandList" @click.self="showIslandList = false">
      <div class="island-list-panel">
        <div class="panel-title">岛屿导航</div>
        <div class="island-item" @click="router.push('/island/music'); showIslandList = false">
          <img src="@/assets/islands/music-island.svg" class="island-item-icon" alt="音乐岛" />
          <span>音乐岛</span>
        </div>
        <div class="island-item" @click="router.push('/island/novel'); showIslandList = false">
          <img src="@/assets/islands/novel-island.svg" class="island-item-icon" alt="小说岛" />
          <span>小说岛</span>
        </div>
        <div class="island-item" @click="router.push('/island/video'); showIslandList = false">
          <img src="@/assets/islands/video-island.svg" class="island-item-icon" alt="视频岛" />
          <span>视频岛</span>
        </div>
        <div class="island-item" @click="router.push('/island/log'); showIslandList = false">
          <img src="@/assets/islands/log-island.svg" class="island-item-icon" alt="日志岛" />
          <span>日志岛</span>
        </div>
        <div class="island-item" @click="router.push('/island/tool'); showIslandList = false">
          <img src="@/assets/islands/tool-island.svg" class="island-item-icon" alt="工具岛" />
          <span>工具岛</span>
        </div>
        <div class="panel-divider"></div>
        <div class="island-item logout-item" @click="handleLogout">
          <span>🚪</span>
          <span>退出账号</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'

const router = useRouter()
const auth = useAuthStore()
const settingsStore = useSettingsStore()
const bgAudio = ref(null)
const showIslandList = ref(false)

onMounted(async () => {
  await settingsStore.fetchBgMusic()
  // 尝试播放背景音乐（浏览器可能阻止自动播放）
  setTimeout(() => {
    bgAudio.value?.play().catch(() => {
      // 自动播放被阻止，静默处理
    })
  }, 500)
})

watch(() => settingsStore.bgMusicUrl, (url) => {
  if (bgAudio.value) {
    bgAudio.value.src = url
    bgAudio.value.play().catch(() => {})
  }
})

function toggleMusic() {
  settingsStore.toggleMusic()
  if (bgAudio.value) {
    if (settingsStore.musicPlaying) {
      bgAudio.value.play()
    } else {
      bgAudio.value.pause()
    }
  }
}

function handleLogout() {
  auth.logoutAction()
  router.push('/login')
  ElMessage.success('已退出账号')
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: linear-gradient(180deg,
    #87CEEB 0%,
    #B0E0E6 30%,
    #E0F0FF 60%,
    #F5F9FF 100%
  );
  position: relative;
  overflow: hidden;
}

/* 天空云朵装饰 */
.cloud-sea::before {
  content: '';
  position: absolute;
  width: 100%;
  height: 100%;
  background:
    radial-gradient(ellipse 300px 120px at 10% 85%, rgba(255,255,255,0.8) 0%, transparent 70%),
    radial-gradient(ellipse 400px 150px at 80% 90%, rgba(255,255,255,0.7) 0%, transparent 70%),
    radial-gradient(ellipse 250px 100px at 50% 95%, rgba(255,255,255,0.6) 0%, transparent 70%);
  pointer-events: none;
}

/* 云海背景 */
.cloud-sea {
  position: absolute;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.cloud {
  position: absolute;
  background: radial-gradient(ellipse at center, rgba(255,255,255,0.1) 0%, transparent 70%);
  border-radius: 50%;
}

.cloud-1 { width: 400px; height: 200px; top: 20%; left: -5%; animation: cloud-drift 25s linear infinite; }
.cloud-2 { width: 300px; height: 150px; top: 50%; left: 30%; animation: cloud-drift 30s linear infinite 5s; }
.cloud-3 { width: 500px; height: 250px; top: 70%; left: 60%; animation: cloud-drift 20s linear infinite 10s; }
.cloud-4 { width: 350px; height: 180px; top: 85%; left: -10%; animation: cloud-drift 28s linear infinite 3s; }

/* 顶栏 */
.top-bar {
  position: relative;
  z-index: 10;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 40px;
}

.site-name {
  font-size: 20px;
  color: #1a1a2e;
  text-shadow: 0 1px 3px rgba(255,255,255,0.5);
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.music-btn {
  background: rgba(78, 205, 196, 0.2);
  border: 1px solid rgba(78, 205, 196, 0.4);
  color: var(--color-accent);
}

.username {
  color: var(--color-text-secondary);
  font-size: 14px;
}

/* 岛屿容器 */
.islands-container {
  position: relative;
  z-index: 10;
  display: flex;
  justify-content: center;
  align-items: flex-end;
  gap: 40px;
  padding: 60px 40px 120px;
  flex-wrap: wrap;
  min-height: calc(100vh - 200px);
}

/* 岛屿卡片 */
.island {
  width: 220px;
  height: 260px;
  background: linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(240,248,255,0.9) 100%);
  border: 2px solid rgba(255,255,255,0.8);
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.3s, box-shadow 0.3s, border-color 0.3s;
  position: relative;
  animation: float-island 6s ease-in-out infinite;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1), 0 2px 8px rgba(0,0,0,0.05);
  overflow: hidden;
}

.island-image {
  width: 180px;
  height: 180px;
  object-fit: contain;
  margin-bottom: 8px;
}

.island::before {
  content: '';
  position: absolute;
  bottom: -20px;
  left: 50%;
  transform: translateX(-50%) scaleY(-0.5);
  width: 80%;
  height: 30px;
  background: inherit;
  border-radius: 50%;
  filter: blur(8px);
  opacity: 0.3;
}

/* 各岛屿独立动画相位 */
.music-island { animation-delay: 0s; }
.novel-island { animation-delay: 1.2s; }
.video-island { animation-delay: 2.4s; }
.log-island { animation-delay: 3.6s; }
.tool-island { animation-delay: 4.8s; }

.island:hover {
  transform: scale(1.05) translateY(-8px);
  box-shadow: 0 20px 40px rgba(0,0,0,0.4);
  border-color: var(--color-accent);
}


.island-name {
  font-family: var(--font-serif);
  font-size: 20px;
  color: #1a1a2e;
  margin-bottom: 8px;
}

.island-subtitle {
  font-size: 13px;
  color: #4a5568;
  margin-bottom: 12px;
}

.island-enter {
  font-size: 12px;
  color: #667eea;
  opacity: 0;
  transition: opacity 0.3s;
}

.island:hover .island-enter {
  opacity: 1;
}

/* 底部切换 */
.bottom-switcher {
  position: fixed;
  bottom: 30px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  background: rgba(255, 255, 255, 0.95);
  border: 2px solid rgba(102, 126, 234, 0.3);
  border-radius: 20px;
  padding: 8px 20px;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.15);
}

.bottom-switcher:hover {
  border-color: #667eea;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);
}

.switcher-hint {
  color: #667eea;
  font-size: 14px;
  font-weight: 500;
}

/* 岛屿弹层 */
.island-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  z-index: 200;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.island-list-panel {
  width: 100%;
  max-width: 400px;
  background: rgba(255, 255, 255, 0.98);
  border: 2px solid rgba(102, 126, 234, 0.3);
  border-bottom: none;
  border-radius: var(--radius) var(--radius) 0 0;
  padding: 20px 30px;
  animation: slide-up 300ms ease-out;
}

.panel-title {
  text-align: center;
  color: #1a1a2e;
  font-family: var(--font-serif);
  font-size: 18px;
  margin-bottom: 20px;
}

.island-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 15px;
  border-radius: 8px;
  cursor: pointer;
  color: #1a1a2e;
  transition: background 0.2s;
}

.island-item:hover {
  background: rgba(102, 126, 234, 0.1);
}

.island-item-icon {
  width: 24px;
  height: 24px;
  object-fit: contain;
}

.logout-item {
  color: var(--color-danger) !important;
}

.panel-divider {
  height: 1px;
  background: rgba(102, 126, 234, 0.2);
  margin: 15px 0;
}

@media (max-width: 768px) {
  .islands-container {
    gap: 20px;
    padding: 40px 20px 100px;
  }

  .island {
    width: 160px;
    height: 180px;
  }

  .island-icon {
    font-size: 36px;
  }

  .island-name {
    font-size: 18px;
  }
}
</style>