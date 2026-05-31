<template>
  <div class="home-page" tabindex="0">
    <!-- 水墨国风全屏背景 -->
    <div class="ink-bg-layer">
      <img src="@/assets/backgrounds/doubao.png" class="ink-bg-image" alt="背景"/>
      <div class="fog-overlay"></div>
    </div>

    <!-- 五层背景纵深 - Canvas 重构版 -->
    <!-- Layer 1: 星空（保留CSS） -->
    <div class="layer layer-1"><div class="star-field"></div></div>
    <!-- Layer 2: 山脉（保留CSS） -->
    <div class="layer layer-2">
      <div class="mountain-range">
        <div class="mountain-layer mountain-layer-3"></div>
        <div class="mountain-layer mountain-layer-2"></div>
        <div class="mountain-layer mountain-layer-1"></div>
      </div>
    </div>
    <!-- Layer 3: 灵气粒子（Canvas） -->
    <ParticleLayer :breath-value="breathValue" :particle-count="60" />
    <!-- Layer 4: 云海（Canvas） -->
    <CloudLayer :breath-value="breathValue" :cloud-count="3" />
    <!-- Layer 5: 丁达尔光柱（Canvas） -->
    <GodRayLayer :breath-value="breathValue" :ray-count="4" :particle-count="15" />
    <!-- 纸张纹理叠加 -->
    <GrainOverlay />

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
        <!-- 音乐+音效合一下拉 -->
        <el-dropdown trigger="click" ref="audioDropdownRef" @command="handleDropdownCommand" placement="bottom-end">
          <div class="audio-control" :class="{ 'audio-off': !audioEnabled }" @click="handleAudioToggle">
            <span class="audio-icon">{{ audioIcon }}</span>
          </div>
          <template #dropdown>
            <div class="audio-dropdown-panel" @click.stop>
              <div class="audio-row">
                <span class="audio-label">🎵 背景音乐</span>
                <div class="audio-slider-wrap" @mousedown="startMusicDrag">
                  <div class="audio-slider-track">
                    <div class="audio-slider-fill" :style="{ width: (musicVolume * 100) + '%' }"></div>
                    <div class="audio-slider-thumb" :style="{ left: (musicVolume * 100) + '%' }"></div>
                  </div>
                </div>
              </div>
              <div class="audio-row">
                <span class="audio-label">🔊 音效</span>
                <div class="audio-slider-wrap" @mousedown="startSoundDrag">
                  <div class="audio-slider-track">
                    <div class="audio-slider-fill" :style="{ width: (soundVolume * 100) + '%' }"></div>
                    <div class="audio-slider-thumb" :style="{ left: (soundVolume * 100) + '%' }"></div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </el-dropdown>
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

      <!-- 玉简3D透视轮播 - 近大远小 -->
      <div class="jade-carousel" ref="carouselRef">
        <div class="carousel-track" :style="carouselStyle">
          <div
            v-for="(card, index) in jadeCards"
            :key="card.id"
            class="jade-card"
            :class="[card.class, { 'is-active': activeCard === index }]"
            :style="getCardStyle(index)"
            @click="router.push(card.path)"
            @mouseenter="activeCard = index; playHoverSound(card.id)"
            @mouseleave="activeCard = -1; stopHoverSound"
          >
            <div class="card-glow"></div>
            <div class="card-inner">
              <div class="card-texture"></div>
              <div class="card-runes">{{ card.rune }}</div>
              <div class="card-label">{{ card.label }}</div>
            </div>
            <div class="card-particles">
              <span class="particle"></span><span class="particle"></span><span class="particle"></span>
            </div>
          </div>
        </div>
        <!-- 鼠标手势提示 -->
        <div class="carousel-hint">
          <span class="hint-arrow left">◀</span>
          <span class="hint-text">左右滑动切换</span>
          <span class="hint-arrow right">▶</span>
        </div>
      </div>
    </main>

    <!-- 全局背景音乐 -->
    <audio ref="bgAudio" :src="settingsStore.bgMusicUrl" loop preload="auto" autoplay />

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
import { useBreathCycle } from '@/composables/useBreathCycle'
import GodRayLayer from '@/components/background/GodRayLayer.vue'
import ParticleLayer from '@/components/background/ParticleLayer.vue'
import CloudLayer from '@/components/background/CloudLayer.vue'
import GrainOverlay from '@/components/background/GrainOverlay.vue'

const router = useRouter()
const auth = useAuthStore()
const settingsStore = useSettingsStore()
const bgAudio = ref(null)
const magicMode = ref(false) // 阵法模式

// v2.6 呼吸系统 - 控制所有 Canvas 背景动画
const { breathValue } = useBreathCycle()

// v2.2 天象系统
const { shichenName, solarTermName, solarTermIntensity } = useCelestialSystem()

// v2.3 键盘导航
const { setup: setupKeyboardNav, cleanup: cleanupKeyboardNav, isHelpVisible } = useKeyboardNavigation()

// v2.3 手势控制 - 玉简轮播手势
const { setup: setupGestures, cleanup: cleanupGestures } = useGestureControl({
  onSwipeLeft: () => {
    // 左滑：下一张玉简
    if (currentIndex.value < jadeCards.value.length - 1) {
      currentIndex.value++
    } else {
      currentIndex.value = 0
    }
  },
  onSwipeRight: () => {
    // 右滑：上一张玉简
    if (currentIndex.value > 0) {
      currentIndex.value--
    } else {
      currentIndex.value = jadeCards.value.length - 1
    }
  },
  onDoubleTap: () => {
    // 双击：进入当前玉简岛屿
    const card = jadeCards.value[currentIndex.value]
    if (card) {
      router.push(card.path)
    }
  }
})

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

// 音乐相关 - 仅保留兰亭序
const availableBgmList = ref([
  { id: 'bamboo_flute', name: '🎶 兰亭序' }
])

// 音乐+音效合一控制
const audioEnabled = ref(true)
const musicVolume = ref(0.3)
const soundVolume = ref(0.3)
const isDraggingMusic = ref(false)
const isDraggingSound = ref(false)
const dragStartX = ref(0)
const audioDropdownRef = ref(null)

const audioIcon = computed(() => {
  if (!audioEnabled.value) return '🔇'
  if (musicVolume.value < 0.3) return '🔈'
  if (musicVolume.value < 0.7) return '🔉'
  return '🔊'
})

function handleAudioToggle() {
  audioEnabled.value = !audioEnabled.value
  if (audioEnabled.value) {
    // 启用音乐
    if (!settingsStore.musicPlaying && bgAudio.value) {
      settingsStore.toggleMusic()
    }
    if (bgAudio.value) {
      bgAudio.value.play().catch(() => {})
    }
  } else {
    // 禁用音乐
    if (settingsStore.musicPlaying && bgAudio.value) {
      settingsStore.toggleMusic()
      bgAudio.value.pause()
    }
    // 同时禁用音效
    if (!isMuted.value) {
      toggleSound()
    }
  }
}

function startMusicDrag(e) {
  isDraggingMusic.value = true
  dragStartX.value = e.clientX
  const track = e.currentTarget.querySelector('.audio-slider-track')
  const rect = track.getBoundingClientRect()
  const initialVolume = (e.clientX - rect.left) / rect.width
  musicVolume.value = Math.max(0, Math.min(1, initialVolume))
  setMusicVolume(musicVolume.value)
  document.addEventListener('mousemove', handleMusicDrag)
  document.addEventListener('mouseup', stopMusicDrag)
}

function handleMusicDrag(e) {
  if (!isDraggingMusic.value) return
  const track = document.querySelector('.audio-slider-wrap:first-of-type .audio-slider-track')
  if (!track) return
  const rect = track.getBoundingClientRect()
  const volume = (e.clientX - rect.left) / rect.width
  musicVolume.value = Math.max(0, Math.min(1, volume))
  setMusicVolume(musicVolume.value)
}

function stopMusicDrag() {
  isDraggingMusic.value = false
  document.removeEventListener('mousemove', handleMusicDrag)
  document.removeEventListener('mouseup', stopMusicDrag)
}

function startSoundDrag(e) {
  isDraggingSound.value = true
  const track = e.currentTarget.querySelector('.audio-slider-track')
  const rect = track.getBoundingClientRect()
  const initialVolume = (e.clientX - rect.left) / rect.width
  soundVolume.value = Math.max(0, Math.min(1, initialVolume))
  setSoundVolume(soundVolume.value)
  document.addEventListener('mousemove', handleSoundDrag)
  document.addEventListener('mouseup', stopSoundDrag)
}

function handleSoundDrag(e) {
  if (!isDraggingSound.value) return
  const track = document.querySelector('.audio-slider-wrap:last-of-type .audio-slider-track')
  if (!track) return
  const rect = track.getBoundingClientRect()
  const volume = (e.clientX - rect.left) / rect.width
  soundVolume.value = Math.max(0, Math.min(1, volume))
  setSoundVolume(soundVolume.value)
}

function stopSoundDrag() {
  isDraggingSound.value = false
  document.removeEventListener('mousemove', handleSoundDrag)
  document.removeEventListener('mouseup', stopSoundDrag)
}

function setMusicVolume(vol) {
  if (bgAudio.value) {
    bgAudio.value.volume = vol
  }
}

function setSoundVolume(vol) {
  // 音效音量通过修改 localStorage 或直接设置 Audio 对象
  try {
    localStorage.setItem('sound_volume', vol.toString())
  } catch (e) {
    console.warn('Failed to save sound volume:', e)
  }
}

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

// v2.6 玉简3D轮播数据
const jadeCards = ref([
  { id: 'music', rune: '音', label: '宫商流转', path: '/island/music', class: 'music-card' },
  { id: 'novel', rune: '書', label: '卷帙浩繁', path: '/island/novel', class: 'novel-card' },
  { id: 'video', rune: '影', label: '光影交织', path: '/island/video', class: 'video-card' },
  { id: 'log', rune: '墨', label: '翰墨丹青', path: '/island/log', class: 'log-card' },
  { id: 'tool', rune: '器', label: '机关百变', path: '/island/tool', class: 'tool-card' }
])
const activeCard = ref(-1)
const carouselRef = ref(null)
let startX = 0
let isDragging = false

// 轮播相关
const currentIndex = ref(2) // 中间位置
const carouselStyle = computed(() => ({
  transform: `translateX(${-currentIndex.value * 180}px)`
}))
let autoScrollTimer = null

// 自动轮播 - 每3秒右侧玉简滑到中间（小樱翻牌式）
function startAutoScroll() {
  autoScrollTimer = setInterval(() => {
    // 循环：0→1→2→3→4→0
    if (currentIndex.value < jadeCards.value.length - 1) {
      currentIndex.value++
    } else {
      currentIndex.value = 0
    }
  }, 3000)
}

function stopAutoScroll() {
  if (autoScrollTimer) {
    clearInterval(autoScrollTimer)
    autoScrollTimer = null
  }
}

// 计算卡片3D透视样式 - 魔卡少女樱扇形阶梯布局
function getCardStyle(index) {
  const offset = index - currentIndex.value
  const absOffset = Math.abs(offset)

  // 扇形展开：中间最大最前，两侧递减小
  const scale = absOffset === 0 ? 1.1 : Math.max(0.75, 1 - absOffset * 0.15)
  const translateZ = absOffset === 0 ? 60 : -absOffset * 40
  // 阶梯：translateY 中间最高，两侧低；translateX 扇形展开
  const translateY = absOffset === 0 ? -30 : (offset > 0 ? absOffset * 15 : -absOffset * 10)
  const translateX = offset * 80 // 扇形横向展开
  const rotateZ = offset * 5 // 轻微扇形旋转
  const opacity = absOffset === 0 ? 1 : Math.max(0.5, 1 - absOffset * 0.25)
  const zIndex = 5 - absOffset

  return {
    transform: `translateX(${translateX}px) translateY(${translateY}px) translateZ(${translateZ}px) scale(${scale}) rotateZ(${rotateZ}deg)`,
    opacity: opacity,
    zIndex: zIndex
  }
}

// 鼠标拖动切换
function handleMouseDown(e) {
  startX = e.clientX
  isDragging = true
}

function handleMouseUp(e) {
  if (!isDragging) return
  isDragging = false
  const diff = e.clientX - startX
  if (Math.abs(diff) > 50) {
    if (diff > 0 && currentIndex.value > 0) {
      currentIndex.value--
    } else if (diff < 0 && currentIndex.value < jadeCards.value.length - 1) {
      currentIndex.value++
    }
  }
}

// 触摸切换
function handleTouchStart(e) {
  startX = e.touches[0].clientX
}

function handleTouchEnd(e) {
  const diff = e.changedTouches[0].clientX - startX
  if (Math.abs(diff) > 50) {
    if (diff > 0 && currentIndex.value > 0) {
      currentIndex.value--
    } else if (diff < 0 && currentIndex.value < jadeCards.value.length - 1) {
      currentIndex.value++
    }
  }
}

// 键盘切换
function handleKeyDown(e) {
  if (e.key === 'ArrowLeft' && currentIndex.value > 0) {
    currentIndex.value--
  } else if (e.key === 'ArrowRight' && currentIndex.value < jadeCards.value.length - 1) {
    currentIndex.value++
  }
}

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

  // v2.6 轮播手势监听
  document.addEventListener('keydown', handleKeyDown)

  // v2.6 自动轮播
  startAutoScroll()
  // 鼠标悬停时暂停自动轮播
  const carouselEl = document.querySelector('.jade-carousel')
  if (carouselEl) {
    carouselEl.addEventListener('mouseenter', stopAutoScroll)
    carouselEl.addEventListener('mouseleave', startAutoScroll)
  }
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
  stopAutoScroll()
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

/* 水墨国风全屏背景层 */
.ink-bg-layer {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}
/* 动态雾层叠加 - 多层飘动 */
.ink-bg-layer::before {
  content: "";
  position: absolute;
  left: -15%;
  top: -15%;
  width: 130%;
  height: 130%;
  background:
    radial-gradient(ellipse at 30% 70%, rgba(200, 210, 220, 0.1) 0%, transparent 50%),
    radial-gradient(ellipse at 70% 60%, rgba(180, 200, 210, 0.08) 0%, transparent 45%),
    radial-gradient(ellipse at 50% 85%, rgba(220, 230, 240, 0.06) 0%, transparent 55%);
  animation: fog-drift 20s ease-in-out infinite alternate;
  pointer-events: none;
}
/* 第二层雾 - 反向飘动增加层次感 */
.ink-bg-layer::after {
  content: "";
  position: absolute;
  left: -20%;
  top: -20%;
  width: 140%;
  height: 140%;
  background:
    radial-gradient(ellipse at 60% 40%, rgba(200, 220, 230, 0.07) 0%, transparent 50%),
    radial-gradient(ellipse at 20% 80%, rgba(180, 200, 210, 0.05) 0%, transparent 40%);
  animation: fog-drift-reverse 25s ease-in-out infinite alternate;
  pointer-events: none;
}
@keyframes fog-drift {
  0% { transform: translate(-8%, -5%) rotate(0deg); }
  50% { transform: translate(-3%, -8%) rotate(2deg); }
  100% { transform: translate(8%, 5%) rotate(0deg); }
}
@keyframes fog-drift-reverse {
  0% { transform: translate(10%, 8%) rotate(0deg); }
  50% { transform: translate(5%, 3%) rotate(-2deg); }
  100% { transform: translate(-10%, -8%) rotate(0deg); }
}
/* 半透明深色蒙版 - 弱化背景突出玉简 */
.fog-overlay {
  position: absolute;
  inset: 0;
  background: rgba(12, 20, 35, 0.28);
  pointer-events: none;
  animation: fog-overlay-breathe 8s ease-in-out infinite;
}
@keyframes fog-overlay-breathe {
  0%, 100% { opacity: 0.9; }
  50% { opacity: 1; }
}
.ink-bg-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center center;
  /* 背景水墨化色调，与岛屿一致 */
  filter: brightness(0.48) saturate(0.4) contrast(1.1) sepia(0.4) blur(1px);
}

/* ===== 五层背景纵深 - 水墨国风 ===== */
.parallax-layers {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 2;
  overflow: hidden;
}

.layer {
  position: absolute;
  inset: 0;
  will-change: transform;
}

/* Layer 1: 星空 - 星尘弥散感 */
.layer-1 {
  opacity: var(--layer-1-opacity, 0.6);
  z-index: 1;
}

.star-field {
  position: absolute;
  inset: 0;
  background:
    /* 大星 - 暗淡柔和 */
    radial-gradient(2.5px 2.5px at 12% 22%, rgba(200, 190, 170, 0.4) 0%, transparent 100%),
    radial-gradient(2px 2px at 68% 12%, rgba(190, 185, 165, 0.35) 0%, transparent 100%),
    radial-gradient(2.2px 2.2px at 85% 38%, rgba(195, 188, 168, 0.38) 0%, transparent 100%),
    radial-gradient(2px 2px at 92% 75%, rgba(185, 180, 160, 0.32) 0%, transparent 100%),
    /* 中星 */
    radial-gradient(1.5px 1.5px at 22% 52%, rgba(180, 172, 155, 0.3) 0%, transparent 100%),
    radial-gradient(1.4px 1.4px at 42% 15%, rgba(188, 180, 162, 0.28) 0%, transparent 100%),
    radial-gradient(1.5px 1.5px at 55% 68%, rgba(182, 175, 158, 0.32) 0%, transparent 100%),
    radial-gradient(1.3px 1.3px at 78% 62%, rgba(178, 172, 155, 0.28) 0%, transparent 100%),
    radial-gradient(1.4px 1.4px at 8% 78%, rgba(185, 178, 160, 0.26) 0%, transparent 100%),
    radial-gradient(1.2px 1.2px at 32% 85%, rgba(180, 175, 158, 0.24) 0%, transparent 100%),
    /* 小星 - 星尘感 */
    radial-gradient(1px 1px at 18% 35%, rgba(175, 170, 155, 0.2) 0%, transparent 100%),
    radial-gradient(1px 1px at 35% 8%, rgba(180, 175, 160, 0.22) 0%, transparent 100%),
    radial-gradient(1px 1px at 48% 42%, rgba(178, 173, 158, 0.2) 0%, transparent 100%),
    radial-gradient(1px 1px at 62% 28%, rgba(182, 177, 162, 0.24) 0%, transparent 100%),
    radial-gradient(1px 1px at 72% 88%, rgba(176, 171, 156, 0.2) 0%, transparent 100%),
    radial-gradient(1px 1px at 88% 55%, rgba(180, 175, 160, 0.22) 0%, transparent 100%),
    radial-gradient(1px 1px at 5% 62%, rgba(178, 173, 158, 0.18) 0%, transparent 100%),
    radial-gradient(1px 1px at 28% 45%, rgba(182, 177, 162, 0.2) 0%, transparent 100%),
    radial-gradient(1px 1px at 65% 95%, rgba(176, 171, 156, 0.18) 0%, transparent 100%),
    radial-gradient(1px 1px at 95% 18%, rgba(180, 175, 160, 0.2) 0%, transparent 100%);
  background-size: 280px 280px;
  animation: star-twinkle 18s ease-in-out infinite;
}

@keyframes star-twinkle {
  0%, 100% { opacity: 0.5; }
  25% { opacity: 0.7; }
  50% { opacity: 0.55; }
  75% { opacity: 0.75; }
}

/* Layer 2: 远山 - 水墨晕染风格 */
.layer-2 {
  opacity: var(--layer-2-opacity, 0.7);
  z-index: 2;
}

.mountain-range {
  position: absolute;
  bottom: 0;
  left: -8%;
  right: -8%;
  height: 55%;
}

.mountain-layer {
  position: absolute;
  bottom: 0;
  left: -10%;
  right: -10%;
  height: 100%;
  /* 边缘模糊 - 水墨晕染效果 */
  filter: blur(2px);
}

/* 最远山 - 极淡 */
.mountain-layer-3 {
  opacity: 0.12;
  background: linear-gradient(to top, rgba(70, 90, 100, 0.6) 0%, rgba(80, 100, 110, 0.25) 50%, transparent 100%);
  clip-path: polygon(
    0% 100%, 4% 72%, 10% 80%, 18% 58%, 28% 72%, 38% 50%,
    48% 65%, 58% 48%, 68% 60%, 78% 52%, 88% 62%, 95% 55%, 100% 65%, 100% 100%
  );
  animation: mountain-drift-slow 250s ease-in-out infinite;
}

/* 中间山 */
.mountain-layer-2 {
  opacity: 0.2;
  background: linear-gradient(to top, rgba(60, 80, 85, 0.7) 0%, rgba(70, 90, 95, 0.3) 50%, transparent 100%);
  clip-path: polygon(
    0% 100%, 3% 70%, 9% 78%, 16% 55%, 26% 68%, 36% 45%,
    46% 60%, 56% 42%, 66% 55%, 76% 48%, 86% 58%, 93% 50%, 100% 60%, 100% 100%
  );
  animation: mountain-drift 180s ease-in-out infinite;
}

/* 近山 */
.mountain-layer-1 {
  opacity: 0.28;
  background: linear-gradient(to top, rgba(50, 70, 72, 0.8) 0%, rgba(60, 80, 82, 0.35) 50%, transparent 100%);
  clip-path: polygon(
    0% 100%, 5% 68%, 12% 75%, 20% 52%, 30% 65%, 40% 42%,
    50% 55%, 60% 40%, 70% 52%, 80% 45%, 90% 55%, 96% 48%, 100% 58%, 100% 100%
  );
  animation: mountain-drift-fast 140s ease-in-out infinite;
}

/* 最近山 */
.mountain-layer-0 {
  opacity: 0.35;
  background: linear-gradient(to top, rgba(45, 65, 68, 0.9) 0%, rgba(55, 75, 78, 0.4) 50%, transparent 100%);
  clip-path: polygon(
    0% 100%, 4% 65%, 10% 72%, 18% 48%, 28% 60%, 38% 38%,
    48% 50%, 58% 35%, 68% 48%, 78% 42%, 88% 52%, 95% 45%, 100% 55%, 100% 100%
  );
  animation: mountain-drift-faster 100s ease-in-out infinite;
}

@keyframes mountain-drift-slow {
  0%, 100% { transform: translateX(0) translateY(0); }
  50% { transform: translateX(12px) translateY(3px); }
}

@keyframes mountain-drift {
  0%, 100% { transform: translateX(0) translateY(0); }
  50% { transform: translateX(20px) translateY(5px); }
}

@keyframes mountain-drift-fast {
  0%, 100% { transform: translateX(0) translateY(0); }
  50% { transform: translateX(28px) translateY(7px); }
}

@keyframes mountain-drift-faster {
  0%, 100% { transform: translateX(0) translateY(0); }
  50% { transform: translateX(35px) translateY(10px); }
}

/* 移动端简化 */
@media (max-width: 768px) {
  .layer-1 { display: none; }
  .mountain-layer-3 { display: none; }
  .mountain-layer-2 { opacity: 0.15; }
  .mountain-layer-1 { opacity: 0.2; }
  .mountain-layer-0 { opacity: 0.25; }
}

/* 减少动效模式 */
@media (prefers-reduced-motion: reduce) {
  .star-field, .mountain-range, .mountain-layer {
    animation: none;
  }
  .layer-1, .layer-2 {
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

/* 移动端简化 */
@media (max-width: 768px) {
  .layer-1 { display: none; }
  .mountain-layer-3 { display: none; }
  .mountain-layer-2 { opacity: 0.15; }
  .mountain-layer-1 { opacity: 0.2; }
  .mountain-layer-0 { opacity: 0.25; }
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

/* 音乐+音效合一控制按钮 */
.audio-control {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--color-jade);
  border: 1px solid rgba(78, 205, 196, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  user-select: none;
}

.audio-control:hover {
  background: rgba(78, 205, 196, 0.3);
  border-color: rgba(78, 205, 196, 0.6);
  box-shadow: 0 0 15px rgba(78, 205, 196, 0.3);
}

.audio-control.audio-off {
  background: rgba(100, 100, 100, 0.2);
  border-color: rgba(150, 150, 150, 0.4);
}

.audio-icon {
  font-size: 16px;
  line-height: 1;
}

/* 音乐+音效下拉面板 */
.audio-dropdown-panel {
  padding: 12px 16px;
  min-width: 220px;
  background: rgba(30, 35, 45, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(78, 205, 196, 0.3);
  border-radius: 8px;
}

.audio-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

.audio-row:not(:last-child) {
  border-bottom: 1px solid rgba(78, 205, 196, 0.15);
}

.audio-label {
  font-size: 13px;
  color: rgba(200, 200, 200, 0.9);
  min-width: 80px;
  font-family: var(--font-serif);
}

.audio-slider-wrap {
  flex: 1;
  height: 24px;
  display: flex;
  align-items: center;
  cursor: pointer;
}

.audio-slider-track {
  position: relative;
  width: 100%;
  height: 4px;
  background: rgba(78, 205, 196, 0.2);
  border-radius: 2px;
}

.audio-slider-fill {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  background: linear-gradient(90deg, rgba(78, 205, 196, 0.5), rgba(78, 205, 196, 0.8));
  border-radius: 2px;
  transition: width 0.1s;
}

.audio-slider-thumb {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 14px;
  height: 14px;
  background: var(--color-jade);
  border: 2px solid rgba(78, 205, 196, 0.8);
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(78, 205, 196, 0.5);
  transition: left 0.1s;
}

.audio-slider-wrap:hover .audio-slider-thumb {
  box-shadow: 0 0 12px rgba(78, 205, 196, 0.7);
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
  animation: orbit-around 60s linear infinite;
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

/* ===================================
   玉简3D透视轮播样式
   =================================== */

/* 轮播容器 */
.jade-carousel {
  position: absolute;
  top: 45%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 400px;
  perspective: 1500px;
  perspective-origin: 50% 40%;
  overflow: hidden;
}

.carousel-track {
  position: absolute;
  top: 50%;
  left: 50%;
  transform-style: preserve-3d;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  transition: transform 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

/* 轮播卡片 - 羊脂玉质感 + 鎏金渐变边框 */
.jade-card {
  position: relative;
  width: 130px;
  height: 170px;
  cursor: pointer;
  transition: all 0.5s cubic-bezier(0.2, 0.8, 0.2, 1);
  transform-style: preserve-3d;
  /* 基础悬浮阴影 */
  box-shadow:
    0 6px 18px rgba(0,0,0,0.35),
    0 2px 6px rgba(0,0,0,0.2),
    inset 0 1px 2px rgba(255,255,255,0.7);
  border-radius: 12px;
}
/* 鎏金渐变描边 */
.jade-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 12px;
  border: 1.5px solid transparent;
  background: linear-gradient(145deg, rgba(212,175,55,0.3), rgba(232,210,140,0.5), rgba(212,175,55,0.3)) border-box;
  mask: linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0);
  mask-composite: exclude;
  pointer-events: none;
}

.jade-card.is-active {
  box-shadow:
    0 15px 35px rgba(0,0,0,0.45),
    0 0 25px rgba(212, 178, 70, 0.5),
    0 0 50px rgba(212, 178, 70, 0.2),
    inset 0 1px 2px rgba(255,255,255,0.8);
  animation: card-float-magic 3s ease-in-out infinite, card-glow-magic 3.5s ease-in-out infinite;
}

/* video卡片使用专属呼吸动画 */
.video-card.is-active {
  animation: card-float-magic 3s ease-in-out infinite, card-glow-breathe 4s ease-in-out infinite;
}

@keyframes card-float-magic {
  0%, 100% { transform: translateY(-30px) translateZ(60px) scale(1.1) rotateY(0deg) rotateZ(0deg); }
  25% { transform: translateY(-32px) translateZ(60px) scale(1.1) rotateY(2deg) rotateZ(1deg); }
  50% { transform: translateY(-38px) translateZ(60px) scale(1.1) rotateY(0deg) rotateZ(0deg); }
  75% { transform: translateY(-32px) translateZ(60px) scale(1.1) rotateY(-2deg) rotateZ(-1deg); }
}

/* 核心玉简呼吸光晕 - "影"玉简专属 */
.video-card.is-active .card-glow {
  animation: card-glow-breathe 4s ease-in-out infinite;
}
.video-card.is-active::after {
  animation: card-inner-glow 4s ease-in-out infinite;
}
@keyframes card-glow-breathe {
  0%, 100% {
    opacity: 0.6;
    transform: scale(1);
    background: radial-gradient(ellipse, rgba(212, 178, 70, 0.3) 0%, transparent 60%);
  }
  50% {
    opacity: 1;
    transform: scale(1.15);
    background: radial-gradient(ellipse, rgba(212, 178, 70, 0.5) 0%, transparent 65%);
  }
}
@keyframes card-inner-glow {
  0%, 100% { box-shadow: inset 3px 3px 8px rgba(255, 255, 255, 0.5); }
  50% { box-shadow: inset 5px 5px 12px rgba(255, 255, 255, 0.7); }
}

/* 通用光晕动画（用于非video卡片） */
@keyframes card-glow-magic {
  0%, 100% { filter: brightness(1) drop-shadow(0 0 25px rgba(212, 178, 70, 0.5)); }
  50% { filter: brightness(1.15) drop-shadow(0 0 35px rgba(212, 178, 70, 0.7)); }
}

/* 悬停效果 - 被灵气吹动的轻微摇摆 */
.jade-card:hover {
  transform: translateY(-10px) scale(1.06) rotateY(3deg);
  box-shadow:
    0 12px 30px rgba(0,0,0,0.4),
    0 0 15px rgba(220, 190, 110, 0.35);
  animation: card-hover-sway 2s ease-in-out infinite;
}
.jade-card.is-active:hover {
  transform: translateY(-12px) scale(1.1) rotateY(0deg);
}
@keyframes card-hover-sway {
  0%, 100% { transform: translateY(-10px) scale(1.06) rotateY(3deg); }
  50% { transform: translateY(-12px) scale(1.06) rotateY(-1deg); }
}

/* 轮播手势提示 */
.carousel-hint {
  position: absolute;
  bottom: 10%;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 15px;
  opacity: 0.5;
  font-size: 14px;
  color: rgba(200, 200, 180, 0.6);
  pointer-events: none;
}
.hint-arrow {
  font-size: 12px;
  animation: hint-pulse 2s ease-in-out infinite;
}
.hint-arrow.left { animation-delay: 0s; }
.hint-arrow.right { animation-delay: 1s; }
@keyframes hint-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

/* 卡片主体 - 羊脂白玉质感 + 鎏金描边 */
.card-inner {
  position: absolute;
  inset: 0;
  border-radius: 10px;
  /* 玉石渐变底色 */
  background: linear-gradient(145deg, #f3ede0 0%, #e6d9c3 50%, #f0e7d6 100%);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
/* 玉石暗纹（伪元素模拟肌理） */
.card-inner::before {
  content: '';
  position: absolute;
  inset: 2px;
  border-radius: 8px;
  background: rgba(210, 185, 130, 0.08);
  pointer-events: none;
}

/* 卡片篆纹边框 - hover时亮起 */
.jade-card::after {
  content: '';
  position: absolute;
  inset: 6px;
  border: 1px solid rgba(212, 175, 55, 0.2);
  border-radius: 8px;
  opacity: 0.3;
  transition: all 0.4s;
  pointer-events: none;
}
.jade-card:hover::after {
  border-color: rgba(212, 175, 55, 0.6);
  opacity: 1;
  box-shadow: inset 0 0 12px rgba(212, 175, 55, 0.15);
}
.jade-card.is-active::after {
  border-color: rgba(212, 175, 55, 0.7);
  opacity: 1;
  box-shadow: inset 0 0 15px rgba(212, 175, 55, 0.2);
}

/* 玉石纹理 - 冰裂纹理感 */
.card-texture {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 45% 20% at 30% 20%, rgba(255,255,255,0.4) 0%, transparent 50%),
    radial-gradient(ellipse 30% 40% at 70% 70%, rgba(180,165,140,0.2) 0%, transparent 45%);
  pointer-events: none;
}

/* 道纹文字 - 思源宋体 + 鎏金描边 */
.card-runes {
  font-family: 'Noto Serif SC', 'Source Han Serif CN', 'SimSun', serif;
  font-size: 44px;
  color: #4a3f2e;
  letter-spacing: 0.2em;
  position: relative;
  z-index: 1;
  /* 鎏金描边效果 */
  -webkit-text-stroke: 0.5px rgba(180, 140, 60, 0.4);
  text-shadow:
    0 0 6px rgba(210, 180, 100, 0.4),
    1px 1px 0 rgba(255, 255, 255, 0.9),
    -0.5px -0.5px 0 rgba(180, 140, 60, 0.2);
  transition: all 0.4s ease;
}
.jade-card:hover .card-runes,
.jade-card.is-active .card-runes {
  color: #3a2f1e;
  -webkit-text-stroke: 0.5px rgba(212, 175, 55, 0.7);
  text-shadow:
    0 0 12px rgba(210, 180, 100, 0.6),
    1px 1px 0 rgba(255, 255, 255, 0.95),
    -0.5px -0.5px 0 rgba(180, 140, 60, 0.3);
  filter: brightness(1.15);
  transform: scale(1.05);
}

/* 标签文字 - 古风统一 */
.card-label {
  font-family: 'Noto Serif SC', 'Source Han Serif CN', 'SimSun', serif;
  font-size: 13px;
  color: #4a3f2e;
  margin-top: 18px;
  letter-spacing: 0.25em;
  text-shadow: 0 0 3px rgba(210, 180, 100, 0.25);
  position: relative;
  z-index: 1;
}

/* 卡片光晕 - 淡金色 */
.card-glow {
  position: absolute;
  inset: -15px;
  border-radius: 30px;
  background: radial-gradient(ellipse, rgba(212, 175, 55, 0.2) 0%, transparent 60%);
  opacity: 0.5;
  transition: all 0.5s ease;
  pointer-events: none;
  z-index: -1;
  animation: glow-breathe 4s ease-in-out infinite;
}
.jade-card.is-active .card-glow {
  opacity: 1;
  background: radial-gradient(ellipse, rgba(212, 178, 70, 0.4) 0%, transparent 65%);
  inset: -20px;
}
@keyframes glow-breathe {
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.08); }
}

/* 周围灵气粒子 - 扇形布局轨道 + 魔法阵包裹感 */
.card-particles {
  position: absolute;
  inset: -40px;
  pointer-events: none;
}
.card-particles .particle {
  position: absolute;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(212, 175, 55, 0.9) 0%, rgba(180, 200, 190, 0.6) 100%);
  box-shadow: 0 0 8px rgba(212, 175, 55, 0.6), 0 0 15px rgba(180, 200, 190, 0.3);
  animation: particle-orbit 8s linear infinite;
  transform-origin: center center;
}
/* 淡青粒子 - 椭圆内侧轨道 */
.card-particles .particle:nth-child(1) {
  top: 50%;
  left: 50%;
  animation-delay: 0s;
  background: radial-gradient(circle, rgba(180, 200, 190, 0.9) 0%, rgba(212, 175, 55, 0.5) 100%);
  box-shadow: 0 0 10px rgba(180, 200, 190, 0.7), 0 0 20px rgba(212, 175, 55, 0.3);
}
/* 淡金粒子 - 椭圆外侧轨道 */
.card-particles .particle:nth-child(2) {
  top: 50%;
  left: 50%;
  animation-delay: -2.6s;
}
/* 第二圈淡青 - 倾斜椭圆轨道 */
.card-particles .particle:nth-child(3) {
  top: 50%;
  left: 50%;
  animation-delay: -5.3s;
  background: radial-gradient(circle, rgba(212, 175, 55, 0.8) 0%, rgba(180, 200, 190, 0.4) 100%);
  box-shadow: 0 0 6px rgba(212, 175, 55, 0.5), 0 0 12px rgba(180, 200, 190, 0.25);
}
/* 核心卡片粒子 - 更大更亮 */
.jade-card.is-active .particle {
  width: 5px;
  height: 5px;
  animation-duration: 4s;
}
.jade-card.is-active .particle:nth-child(1) { box-shadow: 0 0 15px rgba(180, 200, 190, 0.9), 0 0 30px rgba(212, 175, 55, 0.5); }
.jade-card.is-active .particle:nth-child(2) { box-shadow: 0 0 15px rgba(212, 175, 55, 0.9), 0 0 30px rgba(180, 200, 190, 0.5); }
.jade-card.is-active .particle:nth-child(3) { box-shadow: 0 0 12px rgba(212, 175, 55, 0.7), 0 0 25px rgba(180, 200, 190, 0.4); }
/* hover时粒子向玉简汇聚 */
.jade-card:hover .particle {
  animation-direction: reverse;
  animation-duration: 3s;
}
/* 点击时粒子散开 */
.jade-card:active .particle {
  animation: particle-burst 0.5s ease-out forwards;
}
/* 扇形轨道 - 椭圆轨迹模拟魔法阵 */
@keyframes particle-orbit {
  0% { transform: rotate(0deg) translateX(35px) translateY(-15px) scale(1); opacity: 0.7; }
  25% { transform: rotate(90deg) translateX(20px) translateY(-30px) scale(1.15); opacity: 1; }
  50% { transform: rotate(180deg) translateX(-35px) translateY(-15px) scale(1); opacity: 0.7; }
  75% { transform: rotate(270deg) translateX(-20px) translateY(-30px) scale(1.15); opacity: 1; }
  100% { transform: rotate(360deg) translateX(35px) translateY(-15px) scale(1); opacity: 0.7; }
}
@keyframes particle-burst {
  0% { transform: rotate(0deg) translateX(35px) scale(1); opacity: 1; }
  100% { transform: rotate(180deg) translateX(80px) scale(0); opacity: 0; }
}

/* 各卡片微调颜色 - 统一羊脂白玉质感 */
.music-card .card-inner { background: linear-gradient(145deg, #f5f0e6 0%, #e8ded0 50%, #f0e8dc 100%); }
.novel-card .card-inner { background: linear-gradient(145deg, #f0ede5 0%, #e5dcd0 50%, #ece4d8 100%); }
/* 视频玉简 - 斜向高光模拟光线照射 */
.video-card .card-inner {
  background: linear-gradient(145deg, #f2f0e8 0%, #e6e2d8 50%, #ece8dc 100%);
  box-shadow:
    inset 3px 3px 8px rgba(255, 255, 255, 0.5),
    inset -2px -2px 6px rgba(180, 170, 155, 0.15),
    inset 25px 25px 30px rgba(255, 255, 255, 0.08);
}
.log-card .card-inner { background: linear-gradient(145deg, #f0ece0 0%, #e5ddd0 50%, #ece6d8 100%); }
.tool-card .card-inner { background: linear-gradient(145deg, #f0f2f5 0%, #e2e8ed 50%, #e8ecf2 100%); }

/* 玉简入场动画 - 从两侧向中间依次淡入，呼应扇形布局 */
.jade-card {
  opacity: 0;
  animation: jade-enter 1s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
}
/* 扇形布局顺序：左右对称向中间聚拢 */
.jade-card:nth-child(1) { animation-delay: 0s; transform-origin: right center; }
.jade-card:nth-child(2) { animation-delay: 0.15s; transform-origin: right center; }
.jade-card:nth-child(3) { animation-delay: 0.35s; transform-origin: center center; }
.jade-card:nth-child(4) { animation-delay: 0.15s; transform-origin: left center; }
.jade-card:nth-child(5) { animation-delay: 0s; transform-origin: left center; }

/* 键盘导航聚焦态 */
.jade-focused {
  outline: 2px solid rgba(212, 175, 55, 0.6) !important;
  outline-offset: 4px;
  box-shadow:
    0 0 20px rgba(212, 175, 55, 0.4),
    0 0 40px rgba(212, 175, 55, 0.2),
    0 12px 30px rgba(0, 0, 0, 0.4) !important;
  animation: jade-focus-pulse 1.5s ease-in-out infinite !important;
}

@keyframes jade-focus-pulse {
  0%, 100% {
    outline-color: rgba(212, 175, 55, 0.4);
    box-shadow:
      0 0 15px rgba(212, 175, 55, 0.3),
      0 0 30px rgba(212, 175, 55, 0.15),
      0 12px 30px rgba(0, 0, 0, 0.4) !important;
  }
  50% {
    outline-color: rgba(212, 175, 55, 0.8);
    box-shadow:
      0 0 25px rgba(212, 175, 55, 0.5),
      0 0 50px rgba(212, 175, 55, 0.25),
      0 12px 30px rgba(0, 0, 0, 0.4) !important;
  }
}
@keyframes jade-enter {
  0% {
    opacity: 0;
    transform: translateY(50px) scale(0.85) rotateY(15deg);
    filter: blur(6px);
  }
  50% {
    opacity: 0.6;
    filter: blur(2px);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1) rotateY(0deg);
    filter: blur(0);
  }
}

/* 岛屿相关的旧样式保持兼容（选择性隐藏） */
.island { display: none; }
.island-pos { display: none; }
.island-glow { display: none; }
.island-wrapper { display: none; }
.island-image { display: none; }
.island-name { display: none; }
.island-subtitle { display: none; }

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
  width: 360px;
  height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
  /* 岛屿底部云雾 - 与背景融合 */
}
.island-wrapper::after {
  content: '';
  position: absolute;
  bottom: -15px;
  left: 50%;
  transform: translateX(-50%);
  width: 300px;
  height: 90px;
  background: radial-gradient(ellipse, rgba(25,38,48,0.7) 0%, rgba(20,30,40,0.4) 40%, transparent 75%);
  filter: blur(18px);
  pointer-events: none;
  z-index: 0;
}

.island-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  position: relative;
  z-index: 1;
  /* 岛屿保持清晰只调色温，不过度模糊 */
  filter: drop-shadow(0 12px 35px rgba(0,0,0,0.6))
          drop-shadow(0 2px 8px rgba(0,0,0,0.3))
          grayscale(0.15) sepia(0.25) brightness(0.8) saturate(0.7) contrast(0.95);
  transition: transform 0.5s ease, filter 0.5s ease;
}

.island-wrapper::before {
  display: none;
}

.island-glow {
  display: none;
}

.island-name {
  font-family: var(--font-serif);
  font-size: 20px;
  color: var(--color-text);
  margin-top: 12px;
  text-shadow: 0 2px 12px rgba(0,0,0,0.7);
  letter-spacing: 0.1em;
}

.island-subtitle {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-top: 4px;
  letter-spacing: 0.15em;
  opacity: 0.8;
}

/* 岛屿底部灵气光环 - 已禁用，岛屿与背景融合 */
.island::after {
  display: none;
}

@keyframes pulse-glow {
  0%, 100% { opacity: 0.4; transform: translateX(-50%) scale(0.9); }
  50% { opacity: 0.7; transform: translateX(-50%) scale(1.1); }
}

.island:hover::after {
  display: none;
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
  filter: drop-shadow(0 15px 40px rgba(0,0,0,0.65))
          drop-shadow(0 2px 8px rgba(0,0,0,0.3))
          grayscale(0.15) sepia(0.25) brightness(0.95) saturate(0.7) contrast(0.95);
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

/* 备案信息 - 玉色半透明 + 鎏金边框 */
.filing-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 50;
  background: rgba(243, 237, 224, 0.15);
  backdrop-filter: blur(4px);
  border-top: 1px solid rgba(212, 175, 55, 0.25);
  padding: 8px 20px;
  padding-bottom: calc(8px + env(safe-area-inset-bottom, 0px));
}

/* 移动端适配 */
@media (max-width: 768px) {
  .filing-footer {
    padding-bottom: calc(8px + env(safe-area-inset-bottom, 10px));
    background: rgba(243, 237, 224, 0.1);
  }
}

.filing-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.filing-icon {
  width: 18px;
  height: 18px;
  object-fit: contain;
  opacity: 0.7;
}

.filing-links {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}
.filing-links a {
  color: rgba(180, 150, 80, 0.7);
  text-decoration: none;
  letter-spacing: 0.05em;
  transition: color 0.3s;
}
.filing-links a:hover {
  color: rgba(212, 175, 55, 0.9);
}
.filing-links span {
  color: rgba(180, 150, 80, 0.5);
}
.filing-divider {
  color: rgba(180, 150, 80, 0.4);
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