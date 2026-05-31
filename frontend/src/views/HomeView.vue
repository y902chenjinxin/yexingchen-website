<template>
  <div class="home-page" tabindex="0">
    <!-- 五层背景纵深 -->
    <div class="parallax-layers">
      <!-- Layer 1: 天穹深处 - 深墨色+微弱星点 -->
      <div class="layer layer-1"><div class="star-field"></div></div>
      <!-- Layer 2: 远山如黛 - 淡墨山脉剪影 -->
      <div class="layer layer-2"><div class="mountain-range"></div></div>
      <!-- Layer 3: 灵气涌动 - 半透明渐变呼吸 -->
      <div class="layer layer-3"><div class="qi-flow"></div></div>
      <!-- Layer 4: 中景云海 - 清晰云层 -->
      <div class="layer layer-4">
        <div class="cloud-bank cloud-1"></div>
        <div class="cloud-bank cloud-2"></div>
        <div class="cloud-bank cloud-3"></div>
      </div>
      <!-- Layer 5: 近景薄雾 -->
      <div class="layer layer-5">
        <div class="mist-wisp wisp-1"></div>
        <div class="mist-wisp wisp-2"></div>
      </div>
    </div>

    <!-- 阵法符文层 -->
    <div class="array-symbol-layer">
      <div class="array-symbol array-symbol-1"></div>
      <div class="array-symbol array-symbol-2"></div>
      <div class="array-symbol array-symbol-3"></div>
    </div>

    <!-- 顶栏 -->
    <header class="top-bar">
      <div class="top-bar-left">
        <span class="site-name font-serif">叶兴辰的个人网站</span>
      </div>
      <div class="top-bar-right">
        <el-dropdown trigger="click" @command="handleMusicSelect">
        <el-button class="music-btn" circle>
          <span class="music-icon">{{ settingsStore.musicPlaying ? '🎵' : '🎶' }}</span>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item v-for="bgm in availableBgmList" :key="bgm.id" :command="bgm.id" :disabled="settingsStore.currentBgmId === bgm.id">
              <span>{{ bgm.name }}</span>
              <span v-if="settingsStore.currentBgmId === bgm.id" class="current-bgm">✓</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
        <!-- v2.3 音效开关 -->
        <el-tooltip content="音效" placement="bottom">
          <el-button class="sound-btn" circle @click="toggleSound">
            <span>{{ isMuted ? '🔇' : '🔊' }}</span>
          </el-button>
        </el-tooltip>
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
              <el-dropdown-item command="chronicle">
                <el-icon><Calendar /></el-icon>
                <span>修炼编年史</span>
              </el-dropdown-item>
              <el-dropdown-item command="spirit-quiz">
                <el-icon><Star /></el-icon>
                <span>灵根测试</span>
              </el-dropdown-item>
              <el-dropdown-item command="help">
                <el-icon><QuestionFilled /></el-icon>
                <span>键盘帮助</span>
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

    <!-- 顶部装饰区域 -->
    <div class="top-decoration">
      <div class="deco-line"></div>
      <div class="deco-particles">
        <span v-for="i in 12" :key="i" class="deco-particle" :style="getDecoParticleStyle(i)"></span>
      </div>
    </div>

    <!-- 主内容：浮空岛屿 - 行星公转布局 -->
    <main class="islands-container" :class="{ 'magic-mode': magicMode }">
      <!-- 灵气连线层 -->
      <svg v-if="magicMode" class="magic-links" viewBox="0 0 100 100" preserveAspectRatio="none">
        <line x1="15%" y1="75%" x2="50%" y2="25%" class="magic-line" />
        <line x1="50%" y1="25%" x2="85%" y2="55%" class="magic-line" />
        <line x1="85%" y1="55%" x2="75%" y2="85%" class="magic-line" />
        <line x1="75%" y1="85%" x2="25%" y2="80%" class="magic-line" />
        <line x1="25%" y1="80%" x2="15%" y2="75%" class="magic-line" />
        <circle cx="15%" cy="75%" r="1" class="magic-node" />
        <circle cx="50%" cy="25%" r="1" class="magic-node" />
        <circle cx="85%" cy="55%" r="1" class="magic-node" />
        <circle cx="75%" cy="85%" r="1" class="magic-node" />
        <circle cx="25%" cy="80%" r="1" class="magic-node" />
      </svg>

      <!-- 岛屿公转系统 - 5个岛屿均匀绕中心旋转 -->
      <div class="solar-system">
        <!-- 旋转容器 -->
        <div class="orbit-group">
          <!-- 音乐岛 - 0度 -->
          <div class="island-pos" @click="router.push('/island/music')" @mouseenter="playHoverSound('music')" @mouseleave="stopHoverSound">
            <div class="island">
              <div class="island-wrapper">
                <img src="@/assets/islands/music-island.svg" class="island-image" alt="音乐岛" />
                <div class="island-glow"></div>
                <div class="music-island-hover">
                  <span class="music-note">♪</span>
                  <span class="music-note">♫</span>
                  <span class="music-note">♪</span>
                </div>
              </div>
              <div class="island-name">音乐岛</div>
              <div class="island-subtitle">音律飘渺</div>
            </div>
          </div>

          <!-- 小说岛 - 72度 -->
          <div class="island-pos" @click="router.push('/island/novel')" @mouseenter="playHoverSound('novel')" @mouseleave="stopHoverSound">
            <div class="island">
              <div class="island-wrapper">
                <img src="@/assets/islands/novel-island.svg" class="island-image" alt="小说岛" />
                <div class="island-glow"></div>
                <div class="novel-island-hover">
                  <div class="book-page"></div>
                  <div class="ink-particle"></div>
                  <div class="ink-particle"></div>
                  <div class="ink-particle"></div>
                </div>
              </div>
              <div class="island-name">小说岛</div>
              <div class="island-subtitle">书卷悠长</div>
            </div>
          </div>

          <!-- 视频岛 - 144度 -->
          <div class="island-pos" @click="router.push('/island/video')" @mouseenter="playHoverSound('video')" @mouseleave="stopHoverSound">
            <div class="island">
              <div class="island-wrapper">
                <img src="@/assets/islands/video-island.svg" class="island-image" alt="视频岛" />
                <div class="island-glow"></div>
                <div class="video-island-hover">
                  <div class="aperture"></div>
                  <div class="film-ribbon"></div>
                </div>
              </div>
              <div class="island-name">视频岛</div>
              <div class="island-subtitle">光影流转</div>
            </div>
          </div>

          <!-- 日志岛 - 216度 -->
          <div class="island-pos" @click="router.push('/island/log')" @mouseenter="playHoverSound('log')" @mouseleave="stopHoverSound">
            <div class="island">
              <div class="island-wrapper">
                <img src="@/assets/islands/log-island.svg" class="island-image" alt="日志岛" />
                <div class="island-glow"></div>
                <div class="log-island-hover">
                  <div class="ink-drop"></div>
                  <div class="paper-float"></div>
                </div>
              </div>
              <div class="island-name">日志岛</div>
              <div class="island-subtitle">岁月留痕</div>
            </div>
          </div>

          <!-- 工具岛 - 288度 -->
          <div class="island-pos" @click="router.push('/island/tool')" @mouseenter="playHoverSound('tool')" @mouseleave="stopHoverSound">
            <div class="island">
              <div class="island-wrapper">
                <img src="@/assets/islands/tool-island.svg" class="island-image" alt="工具岛" />
                <div class="island-glow"></div>
                <div class="tool-island-hover">
                  <div class="gear"></div>
                  <div class="gear"></div>
                  <div class="gear"></div>
                  <div class="tool-part"></div>
                  <div class="tool-part"></div>
                  <div class="tool-part"></div>
                </div>
              </div>
              <div class="island-name">工具岛</div>
              <div class="island-subtitle">机关万千</div>
            </div>
          </div>
        </div>
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

    <!-- v2.1 鼠标轨迹特效 -->
    <MouseTrail />

    <!-- v2.1 修为印章 -->
    <CultivationProgress />

    <!-- v2.2 装饰层（灯笼/丹炉/仙鹤/符文飘浮） -->
    <DecorationsLayer :shichen="shichenName" />

    <!-- v2.2 每日运势 -->
    <DailyFortune />

    <!-- v2.3 键盘帮助层 -->
    <KeyboardHelp :isHelpVisible="isHelpVisible" @close="isHelpVisible = false" />

    <!-- v2.4 随机事件层 -->
    <RandomEventsLayer :activeEvent="activeEvent" />

    <!-- v2.4 编年史弹窗 -->
    <CultivationChronicle :visible="showChronicleDialog" @close="showChronicleDialog = false" />

    <!-- v2.4 灵根测试弹窗 -->
    <SpiritRootQuiz :visible="showSpiritQuizDialog" @close="showSpiritQuizDialog = false" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import { CaretBottom, User, Lock, Avatar, Tools, SwitchButton, Calendar, Star, QuestionFilled } from '@element-plus/icons-vue'
import MouseTrail from '@/components/effects/MouseTrail.vue'
import CultivationProgress from '@/components/effects/CultivationProgress.vue'
import DecorationsLayer from '@/components/effects/DecorationsLayer.vue'
import DailyFortune from '@/components/effects/DailyFortune.vue'
import KeyboardHelp from '@/components/KeyboardHelp.vue'
import RandomEventsLayer from '@/components/effects/RandomEventsLayer.vue'
import CultivationChronicle from '@/components/common/CultivationChronicle.vue'
import SpiritRootQuiz from '@/components/common/SpiritRootQuiz.vue'
import { useCelestialSystem } from '@/composables/useCelestialSystem'
import { useRandomEvents } from '@/composables/useRandomEvents'
import { useKeyboardNavigation } from '@/composables/useKeyboardNavigation'
import { useGestureControl } from '@/composables/useGestureControl'
import { useIslandSound } from '@/composables/useIslandSound'

const router = useRouter()
const auth = useAuthStore()
const settingsStore = useSettingsStore()
const bgAudio = ref(null)
const magicMode = ref(false) // 阵法模式

// v2.2 天象系统
const { shichenName, solarTermName, solarTermIntensity } = useCelestialSystem()

// v2.3 键盘导航
const { setup: setupKeyboardNav, cleanup: cleanupKeyboardNav, isHelpVisible } = useKeyboardNavigation()

// v2.3 手势控制
const { setup: setupGestures, cleanup: cleanupGestures } = useGestureControl()

// v2.3 音效系统
const { setup: setupSounds, cleanup: cleanupSounds, toggleSound, isMuted, playHoverSound, stopHoverSound } = useIslandSound()

// 阵法模式切换
function toggleMagicMode() {
  magicMode.value = !magicMode.value
}

// 十二时辰动态背景更新
function updateAtmosphereTheme() {
  const hour = new Date().getHours()
  const themeIndex = hour % 12
  const root = document.documentElement
  root.style.setProperty('--color-bg-current', `var(--color-bg-theme-${themeIndex})`)
  root.style.setProperty('--color-glow-current', `var(--color-glow-theme-${themeIndex})`)
  root.style.setProperty('--color-cloud-current', `var(--color-cloud-theme-${themeIndex})`)
}

// 音乐相关
const availableBgmList = ref([
  { id: 'garden_music', name: '🎵 庭院音乐' },
  { id: 'pluck_lute', name: '🎸 青花瓷' },
  { id: 'bamboo_flute', name: '🎶 兰亭序' }
])

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

// v2.4 编年史/灵根测试
const showChronicleDialog = ref(false)
const showSpiritQuizDialog = ref(false)

// v2.4 随机事件
const { activeEvent } = useRandomEvents()

onMounted(async () => {
  // 更新十二时辰动态背景
  updateAtmosphereTheme()
  setInterval(updateAtmosphereTheme, 60000)

  await settingsStore.fetchBgMusic()
  setTimeout(() => {
    bgAudio.value?.play().catch(() => {})
  }, 500)

  // v2.3 初始化交互系统
  setupKeyboardNav()
  setupGestures()
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

function handleMusicSelect(bgmId) {
  settingsStore.currentBgmId = bgmId
  const bgm = availableBgmList.value.find(b => b.id === bgmId)
  if (bgm) {
    settingsStore.bgMusicUrl = `/api/settings/bg_music/stream/${bgmId}`
  }
  // 确保音乐播放状态为开启
  settingsStore.musicPlaying = true
  if (bgAudio.value) {
    bgAudio.value.src = settingsStore.bgMusicUrl
    bgAudio.value.load()
    setTimeout(() => {
      bgAudio.value?.play().catch(() => {})
    }, 200)
  }
}

function handleDropdownCommand(command) {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'password':
      showPasswordDialog.value = true
      passwordForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
      break
    case 'avatar':
      showAvatarDialog.value = true
      break
    case 'chronicle':
      showChronicleDialog.value = true
      break
    case 'spirit-quiz':
      showSpiritQuizDialog.value = true
      break
    case 'help':
      isHelpVisible.value = true
      break
    case 'logout':
      handleLogout()
      break
  }
}

function confirmAvatar() {
  // 保存头像选择
  auth.updateMe({ avatar_id: selectedAvatar.value })
    .then(() => {
      auth.fetchUser()
      ElMessage.success('头像已更新')
      showAvatarDialog.value = false
    })
    .catch(() => {
      ElMessage.error('头像更新失败')
    })
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
  if (passwordForm.value.newPassword.length < 8) {
    ElMessage.warning('新密码长度至少8位')
    return
  }
  // 调用修改密码API
  auth.changePassword(passwordForm.value.oldPassword, passwordForm.value.newPassword)
    .then(() => {
      ElMessage.success('密码修改成功')
      showPasswordDialog.value = false
      passwordForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
    })
    .catch((err) => {
      ElMessage.error(err.message || '密码修改失败')
    })
}

function handleLogout() {
  auth.logoutAction()
  router.push('/login')
  ElMessage.success('已退出账号')
}

function getDecoParticleStyle(i) {
  const delay = i * 0.3
  return {
    animationDelay: `${delay}s`
  }
}

// v2.3 清理交互系统
onUnmounted(() => {
  cleanupKeyboardNav()
  cleanupGestures()
  cleanupSounds()
})
</script>

<style scoped>
@import './hover-effects.css';

.home-page {
  min-height: 100vh;
  background: var(--color-bg-current);
  position: relative;
  overflow: hidden;
  transition: background 1s ease;
}

/* 云海背景 - 使用十二时辰变量 */
/* ===== 五层背景纵深 ===== */
.parallax-layers {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 1;
  overflow: hidden;
}

.layer {
  position: absolute;
  inset: 0;
  will-change: transform;
}

/* Layer 1: 天穹深处 - 深墨色+微弱星点 */
.layer-1 {
  opacity: var(--layer-1-opacity, 0.4);
  z-index: 1;
}

.star-field {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(1px 1px at 20% 30%, rgba(139, 122, 106, 0.5) 0%, transparent 100%),
    radial-gradient(1px 1px at 40% 70%, rgba(192, 142, 58, 0.4) 0%, transparent 100%),
    radial-gradient(1px 1px at 60% 20%, rgba(176, 140, 110, 0.45) 0%, transparent 100%),
    radial-gradient(1px 1px at 80% 60%, rgba(160, 130, 100, 0.35) 0%, transparent 100%),
    radial-gradient(1px 1px at 10% 80%, rgba(139, 157, 131, 0.4) 0%, transparent 100%),
    radial-gradient(1px 1px at 90% 10%, rgba(184, 134, 11, 0.35) 0%, transparent 100%);
  background-size: 200px 200px;
  animation: star-twinkle 8s ease-in-out infinite;
}

@keyframes star-twinkle {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.75; }
}

/* Layer 2: 远山如黛 - 淡墨山脉剪影 */
.layer-2 {
  opacity: var(--layer-2-opacity, 0.6);
  z-index: 2;
}

.mountain-range {
  position: absolute;
  bottom: 0;
  left: -10%;
  right: -10%;
  height: 45%;
  background: linear-gradient(
    to top,
    rgba(139, 122, 106, 0.25) 0%,
    rgba(160, 140, 120, 0.12) 50%,
    transparent 100%
  );
  clip-path: polygon(
    0% 100%, 3% 65%, 10% 80%, 18% 50%, 28% 70%, 38% 40%,
    48% 60%, 58% 35%, 68% 55%, 78% 45%, 88% 65%, 95% 55%, 100% 70%, 100% 100%
  );
  animation: mountain-drift 150s ease-in-out infinite;
}

@keyframes mountain-drift {
  0%, 100% { transform: translateX(0); }
  50% { transform: translateX(20px); }
}

/* Layer 3: 灵气涌动 - 半透明渐变呼吸 */
.layer-3 {
  opacity: var(--layer-3-opacity, 0.8);
  z-index: 3;
}

.qi-flow {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 50% at 50% 100%, rgba(139, 157, 131, 0.2) 0%, transparent 60%),
    radial-gradient(ellipse 60% 40% at 30% 80%, rgba(176, 140, 110, 0.15) 0%, transparent 50%),
    radial-gradient(ellipse 60% 40% at 70% 70%, rgba(192, 142, 58, 0.12) 0%, transparent 50%);
  animation: qi-breathe 19s ease-in-out infinite;
}

@keyframes qi-breathe {
  0%, 100% { opacity: 0.35; transform: scaleY(1); }
  21% { opacity: 0.6; transform: scaleY(1.06); }
  58% { opacity: 0.7; transform: scaleY(1.1); }
}

/* Layer 4: 中景云海 - 清晰云层 */
.layer-4 {
  opacity: var(--layer-4-opacity, 1);
  z-index: 4;
}

.cloud-bank {
  position: absolute;
  background: radial-gradient(ellipse at center, var(--color-cloud-current, rgba(212, 200, 184, 0.55)) 0%, transparent 70%);
  border-radius: 50%;
  transition: background 1s ease;
}

.cloud-bank.cloud-1 {
  width: 500px; height: 250px;
  top: 38%; left: -10%;
  animation: cloud-sea-drift 60s ease-in-out infinite;
}
.cloud-bank.cloud-2 {
  width: 400px; height: 200px;
  top: 55%; left: 25%;
  animation: cloud-sea-drift 60s ease-in-out infinite 8s;
}
.cloud-bank.cloud-3 {
  width: 600px; height: 300px;
  top: 72%; left: 50%;
  animation: cloud-sea-drift 60s ease-in-out infinite 16s;
}

@keyframes cloud-sea-drift {
  0% { transform: translateX(0) translateY(0); }
  25% { transform: translateX(30px) translateY(-8px); }
  50% { transform: translateX(60px) translateY(0); }
  75% { transform: translateX(30px) translateY(8px); }
  100% { transform: translateX(0) translateY(0); }
}

/* Layer 5: 近景薄雾 */
.layer-5 {
  opacity: var(--layer-5-opacity, 0.5);
  z-index: 5;
}

.mist-wisp {
  position: absolute;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 250, 245, 0.25) 20%,
    rgba(255, 250, 245, 0.3) 50%,
    rgba(255, 250, 245, 0.25) 80%,
    transparent 100%
  );
  border-radius: 50%;
  filter: blur(15px);
}

.mist-wisp.wisp-1 {
  width: 90%; height: 100px;
  top: 82%; left: -5%;
  animation: mist-drift 40s ease-in-out infinite;
}
.mist-wisp.wisp-2 {
  width: 70%; height: 80px;
  top: 90%; left: 25%;
  animation: mist-drift 40s ease-in-out infinite 12s;
}

@keyframes mist-drift {
  0% { transform: translateX(0); opacity: 0.3; }
  50% { transform: translateX(50px); opacity: 0.5; }
  100% { transform: translateX(0); opacity: 0.3; }
}

/* 移动端简化 */
@media (max-width: 768px) {
  .layer-1 { display: none; }
  .layer-5 .mist-wisp.wisp-1 { display: none; }
  .cloud-bank.cloud-3 { display: none; }
  .mountain-range { height: 30%; }
}

/* 减少动效模式 */
@media (prefers-reduced-motion: reduce) {
  .star-field, .mountain-range, .qi-flow, .cloud-bank, .mist-wisp {
    animation: none;
  }
  .layer-1, .layer-2, .layer-3, .layer-4, .layer-5 {
    opacity: 0.3;
  }
}

/* 阵法符文层 */
.array-symbol-layer {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 6;
  opacity: 0.08;
}

.array-symbol {
  position: absolute;
  border: 1px solid var(--color-gold);
  border-radius: 50%;
  animation: array-rotate 240s linear infinite;
}

.array-symbol-1 {
  width: 600px;
  height: 600px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.array-symbol-2 {
  width: 400px;
  height: 400px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation-direction: reverse;
  animation-duration: 180s;
  opacity: 0.6;
}

.array-symbol-3 {
  width: 800px;
  height: 800px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation-duration: 300s;
  opacity: 0.3;
}

@keyframes array-rotate {
  from { transform: translate(-50%, -50%) rotate(0deg); }
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

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
  background: linear-gradient(135deg, var(--color-gold) 0%, var(--color-gold-bright) 50%, var(--color-gold) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 2px 8px rgba(201, 169, 110, 0.3));
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.music-btn {
  background: var(--color-jade);
  border: 1px solid rgba(78, 205, 196, 0.4);
  color: var(--color-accent);
}

.magic-btn {
  background: rgba(201, 169, 110, 0.2);
  border: 1px solid rgba(201, 169, 110, 0.4);
  color: var(--color-gold);
  font-size: 18px;
  transition: all 0.3s ease;
}

.magic-btn:hover,
.magic-btn.active {
  background: rgba(201, 169, 110, 0.4);
  border-color: rgba(201, 169, 110, 0.6);
  box-shadow: 0 0 15px rgba(201, 169, 110, 0.3);
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
  color: var(--color-gold);
}

/* 顶部装饰区域 */
.top-decoration {
  position: relative;
  z-index: 5;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 20px;
}

.deco-line {
  width: 200px;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--color-gold), transparent);
  border-radius: 2px;
  box-shadow: 0 0 20px rgba(201, 169, 110, 0.3);
}

.deco-particles {
  display: flex;
  gap: 30px;
  margin-top: 15px;
}

.deco-particle {
  width: 4px;
  height: 4px;
  background: var(--color-gold);
  border-radius: 50%;
  opacity: 0.6;
  animation: float-particle 4s ease-in-out infinite;
  box-shadow: 0 0 6px var(--color-gold);
}

.deco-particle:nth-child(odd) {
  animation-duration: 5s;
  background: var(--color-jade);
  box-shadow: 0 0 6px var(--color-jade);
}

@keyframes float-particle {
  0%, 100% { transform: translateY(0); opacity: 0.6; }
  50% { transform: translateY(-8px); opacity: 1; }
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
  align-items: center;
  padding: 80px 40px 140px;
  min-height: calc(100vh - 200px);
}

/* 公转系统 */
.solar-system {
  position: relative;
  width: 800px;
  height: 800px;
  display: flex;
  justify-content: center;
  align-items: center;
}

/* 旋转组 - 整体旋转 */
.orbit-group {
  position: relative;
  width: 100%;
  height: 100%;
  animation: orbit-around 30s linear infinite;
}

@keyframes orbit-around {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 岛屿位置 - 均匀分布在圆环上 */
.island-pos {
  position: absolute;
  top: 50%;
  left: 50%;
  transform-origin: center center;
}

/* 音乐岛 - 0度 (顶部) */
.island-pos:nth-child(1) {
  transform: translate(-50%, -50%) rotate(0deg) translateY(-300px);
}
/* 小说岛 - 72度 */
.island-pos:nth-child(2) {
  transform: translate(-50%, -50%) rotate(72deg) translateY(-300px);
}
/* 视频岛 - 144度 */
.island-pos:nth-child(3) {
  transform: translate(-50%, -50%) rotate(144deg) translateY(-300px);
}
/* 日志岛 - 216度 */
.island-pos:nth-child(4) {
  transform: translate(-50%, -50%) rotate(216deg) translateY(-300px);
}
/* 工具岛 - 288度 */
.island-pos:nth-child(5) {
  transform: translate(-50%, -50%) rotate(288deg) translateY(-300px);
}

/* 悬停时公转暂停 */
.orbit-group:hover {
  animation-play-state: paused;
}

/* 悬停时岛屿上浮+发光（移除翻转） */
.island-pos:hover .island {
  filter: drop-shadow(0 0 30px var(--color-glow-current));
  transform: translateY(-20px) scale(1.05);
}

/* 岛屿卡片 */
.island {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  transition: transform 0.4s ease, filter 0.4s ease;
  transform-style: preserve-3d;
}

/* 岛屿卡片 - 2.5D立体效果 */
.island {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  transition: transform 0.4s ease, filter 0.4s ease;
  transform-style: preserve-3d;
}

/* 阵法模式背景灵气光晕 */
.magic-mode .islands-container::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 300px 200px at 15% 70%, rgba(78, 205, 196, 0.08) 0%, transparent 70%),
    radial-gradient(ellipse 250px 180px at 85% 50%, rgba(201, 169, 110, 0.06) 0%, transparent 60%),
    radial-gradient(ellipse 200px 150px at 50% 20%, rgba(155, 141, 201, 0.05) 0%, transparent 50%);
  pointer-events: none;
  animation: magic-aura 6s ease-in-out infinite;
}

@keyframes magic-aura {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

/* 岛屿卡片 - 2.5D立体效果 */
.island {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  transition: transform 0.4s ease, filter 0.4s ease;
  transform-style: preserve-3d;
}

.island-wrapper {
  position: relative;
  width: 320px;
  height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.island-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  filter: drop-shadow(0 25px 35px rgba(0,0,0,0.35));
  transition: transform 0.4s ease, filter 0.4s ease;
}

.island-glow {
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 200px;
  height: 60px;
  background: radial-gradient(ellipse, var(--color-purple) 0%, transparent 70%);
  filter: blur(10px);
  opacity: 0;
  transition: opacity 0.4s;
}

.island-name {
  font-family: var(--font-serif);
  font-size: 18px;
  color: var(--color-text);
  margin-top: 10px;
  text-shadow: 0 2px 8px rgba(0,0,0,0.5);
}

.island-subtitle {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-top: 4px;
}

/* 岛屿底部灵气光环 */
.island::after {
  content: '';
  position: absolute;
  bottom: -10px;
  left: 50%;
  transform: translateX(-50%);
  width: 120px;
  height: 40px;
  background: radial-gradient(ellipse, var(--color-jade) 0%, transparent 70%);
  border-radius: 50%;
  filter: blur(8px);
  animation: pulse-glow 3s ease-in-out infinite;
  pointer-events: none;
}

@keyframes pulse-glow {
  0%, 100% { opacity: 0.4; transform: translateX(-50%) scale(0.9); }
  50% { opacity: 0.7; transform: translateX(-50%) scale(1.1); }
}

.music-island::after { background: radial-gradient(ellipse, rgba(155, 141, 201, 0.3) 0%, transparent 70%); }
.novel-island::after { background: radial-gradient(ellipse, rgba(232, 213, 183, 0.25) 0%, transparent 70%); }
.video-island::after { background: radial-gradient(ellipse, rgba(167, 139, 201, 0.3) 0%, transparent 70%); }
.log-island::after { background: radial-gradient(ellipse, rgba(143, 188, 143, 0.25) 0%, transparent 70%); }
.tool-island::after { background: radial-gradient(ellipse, rgba(212, 165, 116, 0.3) 0%, transparent 70%); }

.island:hover::after {
  opacity: 0.9;
  transform: translateX(-50%) scale(1.3);
  animation: none;
  filter: blur(4px) brightness(1.5);
}

/* 灵气连线 */
.magic-links {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 5;
  opacity: 0;
  transition: opacity 0.5s ease;
}

.magic-mode .magic-links {
  opacity: 1;
}

.magic-line {
  stroke: rgba(78, 205, 196, 0.25);
  stroke-width: 0.5;
  stroke-dasharray: 3, 6;
  animation: flow-line 3s linear infinite;
}

.magic-node {
  fill: rgba(78, 205, 196, 0.4);
  animation: node-pulse 2s ease-in-out infinite;
}

@keyframes flow-line {
  to { stroke-dashoffset: -18; }
}

@keyframes node-pulse {
  0%, 100% { opacity: 0.4; r: 1; }
  50% { opacity: 0.8; r: 1.5; }
}

/* 阵法模式 - 岛屿环形旋转叠加效果 */
.magic-mode .orbit-group { animation: orbit-around 25s linear infinite, circular-magic 30s linear infinite; }

@keyframes circular-magic {
  0% { transform: translate(0, 0) rotate(0deg); }
  25% { transform: translate(80px, -40px) rotate(90deg); }
  50% { transform: translate(0, -80px) rotate(180deg); }
  75% { transform: translate(-80px, -40px) rotate(270deg); }
  100% { transform: translate(0, 0) rotate(360deg); }
}


.island:hover {
  transform: translateY(-20px) scale(1.05);
  z-index: 20;
}

.island:hover .island-image {
  filter: drop-shadow(0 30px 40px rgba(0,0,0,0.4)) brightness(1.1);
}

.island:hover .island-glow {
  opacity: 1;
}

/* P2: 岛屿hover光效增强 - 多层box-shadow */
.island:hover .island-wrapper {
  filter: drop-shadow(0 20px 30px rgba(0,0,0,0.3)) drop-shadow(0 0 20px var(--island-glow-color, rgba(78, 205, 196, 0.3)));
}

/* 岛屿hover效果 */
.island:hover .island-wrapper {
  filter: drop-shadow(0 20px 30px rgba(0,0,0,0.4)) drop-shadow(0 0 30px var(--color-gold));
}

/* 底部切换 */
.bottom-switcher {
  position: fixed;
  bottom: 60px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  background: rgba(255, 255, 255, 0.95);
  border: 2px solid var(--color-gold);
  border-radius: 20px;
  padding: 8px 20px;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.15);
}

.bottom-switcher:hover {
  border-color: var(--color-gold);
  box-shadow: 0 4px 20px var(--color-gold);
}

.switcher-hint {
  color: var(--color-gold);
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
  border: 2px solid var(--color-gold);
  border-bottom: none;
  border-radius: var(--radius) var(--radius) 0 0;
  padding: 20px 30px;
  animation: slide-up 300ms ease-out;
}

.panel-title {
  text-align: center;
  color: var(--color-text-dark);
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
  color: var(--color-text-dark);
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
  padding-bottom: calc(10px + env(safe-area-inset-bottom, 0px));
}

/* 移动端适配 - 避免与系统导航栏重叠 */
@media (max-width: 768px) {
  .filing-footer {
    padding-bottom: calc(10px + env(safe-area-inset-bottom, 10px));
  }
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
  color: var(--color-gold);
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
  border-color: var(--color-gold);
  background: rgba(102, 126, 234, 0.2);
  box-shadow: 0 0 15px var(--color-gold);
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

  /* 移动端阵法模式简化：禁用环形位移，保留上下浮动 */
  .magic-mode .islands-container::before {
    display: none;
  }

  .magic-mode .magic-links {
    display: none;
  }

  .magic-mode .island {
    animation-duration: 20s !important;
  }
}

/* 平板端 (768px - 1024px) */
@media (min-width: 769px) and (max-width: 1024px) {
  .islands-container {
    gap: 30px;
    padding: 50px 30px 120px;
  }

  .island {
    width: 180px;
    height: 200px;
  }

  .island-icon {
    font-size: 40px;
  }

  .island-name {
    font-size: 20px;
  }
}
</style>