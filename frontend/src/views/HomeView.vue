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
        <el-dropdown trigger="click" @command="handleDropdownCommand">
          <div class="user-avatar-area">
            <span class="avatar-text">{{ avatarText }}</span>
            <el-icon class="dropdown-arrow"><CaretBottom /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>
                <span>个人中心</span>
              </el-dropdown-item>
              <el-dropdown-item command="password">
                <el-icon><Lock /></el-icon>
                <span>修改密码</span>
              </el-dropdown-item>
              <el-dropdown-item command="avatar">
                <el-icon><Avatar /></el-icon>
                <span>选择头像</span>
              </el-dropdown-item>
              <el-dropdown-item divided command="music" @click="router.push('/island/music')">
                <span>🎵 音乐岛</span>
              </el-dropdown-item>
              <el-dropdown-item command="novel" @click="router.push('/island/novel')">
                <span>📖 小说岛</span>
              </el-dropdown-item>
              <el-dropdown-item command="video" @click="router.push('/island/video')">
                <span>🎬 视频岛</span>
              </el-dropdown-item>
              <el-dropdown-item command="log" @click="router.push('/island/log')">
                <span>📝 日志岛</span>
              </el-dropdown-item>
              <el-dropdown-item command="tool" @click="router.push('/island/tool')">
                <span>⚙️ 工具岛</span>
              </el-dropdown-item>
              <el-dropdown-item v-if="auth.isSuperAdmin" divided command="admin" @click="router.push('/admin')">
                <el-icon><Tools /></el-icon>
                <span>管理后台</span>
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <el-icon><SwitchButton /></el-icon>
                <span>退出账号</span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- 主内容：浮空岛屿 -->
    <main class="islands-container">
      <div class="island music-island" @click="router.push('/island/music')">
        <img src="@/assets/islands/music-island-xianxia.svg" class="island-image" alt="音乐岛" />
        <div class="island-name">音乐岛</div>
        <div class="island-subtitle">音律飘渺</div>
        <div class="island-enter">点击进入</div>
      </div>

      <div class="island novel-island" @click="router.push('/island/novel')">
        <img src="@/assets/islands/novel-island-xianxia.svg" class="island-image" alt="小说岛" />
        <div class="island-name">小说岛</div>
        <div class="island-subtitle">书卷悠长</div>
        <div class="island-enter">点击进入</div>
      </div>

      <div class="island video-island" @click="router.push('/island/video')">
        <img src="@/assets/islands/video-island-xianxia.svg" class="island-image" alt="视频岛" />
        <div class="island-name">视频岛</div>
        <div class="island-subtitle">光影流转</div>
        <div class="island-enter">点击进入</div>
      </div>

      <div class="island log-island" @click="router.push('/island/log')">
        <img src="@/assets/islands/log-island-xianxia.svg" class="island-image" alt="日志岛" />
        <div class="island-name">日志岛</div>
        <div class="island-subtitle">岁月留痕</div>
        <div class="island-enter">点击进入</div>
      </div>

      <div class="island tool-island" @click="router.push('/island/tool')">
        <img src="@/assets/islands/tool-island-xianxia.svg" class="island-image" alt="工具岛" />
        <div class="island-name">工具岛</div>
        <div class="island-subtitle">机关万千</div>
        <div class="island-enter">点击进入</div>
      </div>
    </main>

    <!-- 全局背景音乐 -->
    <audio ref="bgAudio" :src="settingsStore.bgMusicUrl" loop preload="auto" />

    <!-- 备案信息 -->
    <footer class="filing-footer">
      <div class="filing-content">
        <img src="/filing/beian-icon.png" alt="备案图标" class="filing-icon" />
        <div class="filing-links">
          <a href="https://beian.mps.gov.cn/#/query/webSearch?code=34010402704746" target="_blank" rel="noopener">皖公网安备34010402704746号</a>
          <span class="filing-divider">|</span>
          <a href="https://beian.miit.gov.cn/#/Integrated/index" target="_blank" rel="noopener">皖ICP备2026006516号</a>
        </div>
      </div>
    </footer>

    <!-- 头像选择对话框 -->
    <el-dialog v-model="showAvatarDialog" title="选择头像" width="320px">
      <div class="avatar-options">
        <div
          v-for="avatar in avatarOptions"
          :key="avatar.id"
          class="avatar-option"
          :class="{ selected: selectedAvatar === avatar.id }"
          @click="selectedAvatar = avatar.id"
        >
          <span class="avatar-emoji">{{ avatar.emoji }}</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="showAvatarDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmAvatar">确定</el-button>
      </template>
    </el-dialog>

    <!-- 修改密码对话框 -->
    <el-dialog v-model="showPasswordDialog" title="修改密码" width="400px">
      <el-form :model="passwordForm" label-width="80px">
        <el-form-item label="当前密码">
          <el-input v-model="passwordForm.oldPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="passwordForm.newPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="passwordForm.confirmPassword" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPasswordDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmPassword">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import { CaretBottom, User, Lock, Avatar, Tools, SwitchButton } from '@element-plus/icons-vue'

const router = useRouter()
const auth = useAuthStore()
const settingsStore = useSettingsStore()
const bgAudio = ref(null)

// 头像相关
const showAvatarDialog = ref(false)
const avatarOptions = [
  { id: 1, emoji: '🌙' },
  { id: 2, emoji: '☁️' }
]
const selectedAvatar = ref(1)
const avatarText = computed(() => {
  const av = avatarOptions.find(a => a.id === selectedAvatar.value)
  return av?.emoji || '🌙'
})

// 密码相关
const showPasswordDialog = ref(false)
const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

onMounted(async () => {
  await settingsStore.fetchBgMusic()
  setTimeout(() => {
    bgAudio.value?.play().catch(() => {})
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

function handleDropdownCommand(command) {
  switch (command) {
    case 'profile':
      ElMessage.info('个人中心功能开发中')
      break
    case 'password':
      showPasswordDialog.value = true
      passwordForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
      break
    case 'avatar':
      showAvatarDialog.value = true
      break
    case 'logout':
      handleLogout()
      break
  }
}

function confirmAvatar() {
  showAvatarDialog.value = false
  ElMessage.success('头像已更新')
}

function confirmPassword() {
  if (!passwordForm.value.oldPassword) {
    ElMessage.warning('请输入当前密码')
    return
  }
  if (!passwordForm.value.newPassword) {
    ElMessage.warning('请输入新密码')
    return
  }
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    ElMessage.warning('两次密码不一致')
    return
  }
  // TODO: 调用修改密码API
  ElMessage.success('密码修改成功')
  showPasswordDialog.value = false
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

/* 头像下拉区域 */
.user-avatar-area {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.user-avatar-area:hover {
  background: rgba(255, 255, 255, 0.1);
}

.avatar-text {
  font-size: 20px;
}

.dropdown-arrow {
  font-size: 12px;
  color: #667eea;
}

/* 下拉菜单图标 */
.el-dropdown-menu__item {
  display: flex;
  align-items: center;
  gap: 8px;
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
  bottom: 60px;
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

/* 备案信息 */
.filing-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 50;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  border-top: 1px solid rgba(102, 126, 234, 0.2);
  padding: 10px 20px;
}

.filing-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.filing-icon {
  width: 20px;
  height: 20px;
  object-fit: contain;
}

.filing-links {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.filing-links a {
  color: #667eea;
  text-decoration: none;
  transition: color 0.2s;
}

.filing-links a:hover {
  color: #5a67d8;
}

.filing-divider {
  color: #ddd;
}

/* 头像选项 */
.avatar-options {
  display: flex;
  justify-content: center;
  gap: 20px;
  padding: 20px 0;
}

.avatar-option {
  width: 70px;
  height: 70px;
  border-radius: 50%;
  background: rgba(102, 126, 234, 0.1);
  border: 2px solid rgba(102, 126, 234, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.avatar-option:hover {
  border-color: rgba(102, 126, 234, 0.5);
  background: rgba(102, 126, 234, 0.15);
}

.avatar-option.selected {
  border-color: #667eea;
  background: rgba(102, 126, 234, 0.2);
  box-shadow: 0 0 15px rgba(102, 126, 234, 0.3);
}

.avatar-emoji {
  font-size: 32px;
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