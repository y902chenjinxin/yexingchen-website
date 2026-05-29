<template>
  <div class="login-page">
    <!-- 星辰夜空背景 -->
    <div class="starry-bg">
      <div class="star" v-for="i in 100" :key="i" :style="getStarStyle(i)"></div>
    </div>

    <!-- 云雾层 -->
    <div class="mist-layer">
      <div class="mist mist-1"></div>
      <div class="mist mist-2"></div>
      <div class="mist mist-3"></div>
    </div>

    <!-- 冰晶琉璃门 -->
    <div class="crystal-door-container" :class="{ 'doors-opening': doorsOpening, 'doors-open': doorsOpen }">
      <!-- 左门 -->
      <div class="crystal-door door-left" :class="{ 'door-closing': !doorsOpening && doorsOpen }">
        <div class="door-surface">
          <div class="ice-texture"></div>
          <div class="light-flow light-flow-1"></div>
          <div class="light-flow light-flow-2"></div>
          <div class="light-flow light-flow-3"></div>
        </div>
        <div class="door-edge"></div>
        <!-- 门上的符文装饰 -->
        <div class="door-runes">
          <div class="rune rune-1"></div>
          <div class="rune rune-2"></div>
          <div class="rune rune-3"></div>
        </div>
      </div>

      <!-- 右门 -->
      <div class="crystal-door door-right" :class="{ 'door-closing': !doorsOpening && doorsOpen }">
        <div class="door-surface">
          <div class="ice-texture"></div>
          <div class="light-flow light-flow-1"></div>
          <div class="light-flow light-flow-2"></div>
          <div class="light-flow light-flow-3"></div>
        </div>
        <div class="door-edge"></div>
        <div class="door-runes">
          <div class="rune rune-1"></div>
          <div class="rune rune-2"></div>
          <div class="rune rune-3"></div>
        </div>
      </div>

      <!-- 门缝寒气星光 -->
      <div class="gap-mist" :class="{ 'mist-visible': showGapMist }">
        <div class="mist-particle" v-for="i in 20" :key="i" :style="getMistParticleStyle(i)"></div>
      </div>

      <!-- 光环涟漪 -->
      <div class="light-ring" :class="{ 'ring-visible': showLightRing }">
        <div class="ring ring-1"></div>
        <div class="ring ring-2"></div>
        <div class="ring ring-3"></div>
      </div>

      <!-- 粒子风 -->
      <div class="particle-wind" :class="{ 'wind-active': showParticleWind }">
        <div class="wind-particle" v-for="i in 50" :key="i" :style="getWindParticleStyle(i)"></div>
      </div>
    </div>

    <!-- 画面震动效果 -->
    <div class="shake-overlay" :class="{ 'shake-active': showShake }"></div>

    <!-- 空间扭曲波纹 -->
    <div class="distortion-wave" :class="{ 'wave-visible': showDistortion }">
      <div class="wave-ring" v-for="i in 3" :key="i" :style="getWaveRingStyle(i)"></div>
    </div>

    <!-- 登录卡片 -->
    <div class="login-card" :class="{ 'card-visible': showCard }">
      <h1 class="site-title font-serif">叶兴辰的个人网站</h1>
      <p class="site-subtitle">神农遗风，云上洞天</p>

      <!-- 登录表单 -->
      <el-form v-if="!isRegistering" class="login-form" :model="loginForm" @submit.prevent="handleLogin" aria-label="登录表单">
        <el-form-item>
          <el-input v-model="loginForm.email" placeholder="邮箱" size="large" clearable aria-label="邮箱" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="loginForm.password" :type="passwordVisible ? 'text' : 'password'" placeholder="密码" size="large" aria-label="密码">
            <template #suffix>
              <span class="password-toggle" @click="passwordVisible = !passwordVisible" role="button" :aria-label="passwordVisible ? '隐藏密码' : '显示密码'" tabindex="0" @keydown.enter="passwordVisible = !passwordVisible" @keydown.space.prevent="passwordVisible = !passwordVisible">
                <!-- 闭眼 SVG -->
                <svg v-if="!passwordVisible" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                  <line x1="1" y1="1" x2="23" y2="23"></line>
                </svg>
                <!-- 睁眼 SVG -->
                <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
              </span>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" style="width: 100%" :loading="loading" native-type="submit" aria-label="登录按钮">
            登 录
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 仙气飘飘加载特效 -->
      <div v-if="loading && !isRegistering" class="fairy-loading">
        <div class="fairy-bg"></div>
        <div class="fairy-curtain curtain-1"></div>
        <div class="fairy-curtain curtain-2"></div>
        <div class="fairy-curtain curtain-3"></div>
        <div class="fairy-glow"></div>
        <div class="fairy-ring"></div>
        <div class="fairy-particles">
          <span v-for="i in 6" :key="i" class="fairy-particle" :style="getParticleStyle(i)"></span>
        </div>
      </div>

      <!-- 注册流程 -->
      <div v-if="isRegistering" class="register-flow">
        <!-- Step 1: 输入邮箱 -->
        <div v-if="registerStep === 1" class="step-content">
          <p class="step-title">输入注册邮箱</p>
          <el-form :model="registerForm" @submit.prevent="handleSendCode">
            <el-form-item>
              <el-input v-model="registerForm.email" placeholder="邮箱地址" size="large" clearable />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" size="large" style="width: 100%" :loading="loading" native-type="submit">
                获取验证码
              </el-button>
            </el-form-item>
          </el-form>
          <p class="back-link" @click="isRegistering = false">返回登录</p>
        </div>

        <!-- Step 2: 输入验证码和密码 -->
        <div v-if="registerStep === 2" class="step-content">
          <p class="step-title">验证码已发送至 {{ registerForm.email }}</p>
          <el-form :model="registerForm" @submit.prevent="handleVerifyCode">
            <el-form-item>
              <el-input v-model="registerForm.code" placeholder="6位验证码" size="large" maxlength="6" clearable />
            </el-form-item>
            <el-form-item>
              <el-input v-model="registerForm.password" :type="passwordVisible ? 'text' : 'password'" placeholder="设置密码" size="large">
              <template #suffix>
                <span class="password-toggle" @click="passwordVisible = !passwordVisible">
                  <svg v-if="!passwordVisible" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                    <line x1="1" y1="1" x2="23" y2="23"></line>
                  </svg>
                  <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                  </svg>
                </span>
              </template>
            </el-input>
            </el-form-item>
            <el-form-item>
              <el-input v-model="registerForm.confirmPassword" :type="confirmPasswordVisible ? 'text' : 'password'" placeholder="确认密码" size="large">
              <template #suffix>
                <span class="password-toggle" @click="confirmPasswordVisible = !confirmPasswordVisible">
                  <svg v-if="!confirmPasswordVisible" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                    <line x1="1" y1="1" x2="23" y2="23"></line>
                  </svg>
                  <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                  </svg>
                </span>
              </template>
            </el-input>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" size="large" style="width: 100%" :loading="loading" native-type="submit">
                完成注册
              </el-button>
            </el-form-item>
          </el-form>
          <p class="back-link" @click="registerStep = 1">返回上一步</p>
        </div>

        <!-- Step 3: 注册完成 -->
        <div v-if="registerStep === 3" class="step-content text-center">
          <div class="success-icon">✓</div>
          <p class="step-title">注册申请已提交</p>
          <p class="text-secondary">请等待管理员审批后登录</p>
          <p class="back-link" @click="resetRegister">返回登录</p>
        </div>
      </div>

      <p v-if="!isRegistering" class="register-link" @click="isRegistering = true">
        没有账号？注册申请
      </p>
    </div>

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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { register as registerApi, verifyCode as verifyCodeApi } from '@/api/auth'
import { randFloat } from '@/utils/random'

const router = useRouter()
const auth = useAuthStore()

const loginForm = ref({ email: '', password: '' })
const registerForm = ref({ email: '', code: '', password: '', confirmPassword: '' })
const isRegistering = ref(false)
const registerStep = ref(1)
const loading = ref(false)
const passwordVisible = ref(false)
const confirmPasswordVisible = ref(false) // 注册确认密码可见性 // 密码可见性切换

// 动画状态
const showGapMist = ref(false)
const showLightRing = ref(false)
const showParticleWind = ref(false)
const showShake = ref(false)
const showDistortion = ref(false)
const doorsOpening = ref(false)
const doorsOpen = ref(false)
const showCard = ref(false)

// 光纹熄灭动画
const lightFlowsOff = ref([false, false, false])

onMounted(() => {
  // 动画时序（毫秒）- 优化版：压缩总时长
  // 动画时序（毫秒）- v1.7.2优化版：卡片提前出现，节奏更紧凑
  const TIMING = {
    lightFlowOff1: 0,
    lightFlowOff2: 150,
    lightFlowOff3: 300,
    gapMist: 450,        // 门缝寒气出现
    doorStart: 600,      // 门开始打开
    doorPause: 1300,     // 门45度停顿
    doorResume: 1350,    // 门继续开
    doorComplete: 1600,  // 门全开
    particleWind: 1600,  // 粒子风吹出（与门全开同步）
    lightRing: 1600,     // 光环涟漪（与门全开同步）
    cardShow: 1000       // 登录卡片出现（优化：门开过程中逐渐显现）
  }

  // 光纹逐圈熄灭
  setTimeout(() => { lightFlowsOff.value[0] = true }, TIMING.lightFlowOff1)
  setTimeout(() => { lightFlowsOff.value[1] = true }, TIMING.lightFlowOff2)
  setTimeout(() => { lightFlowsOff.value[2] = true }, TIMING.lightFlowOff3)

  // 门缝寒气
  setTimeout(() => { showGapMist.value = true }, TIMING.gapMist)

  // 门开始打开
  setTimeout(() => { doorsOpening.value = true }, TIMING.doorStart)

  // 门45度时停顿（模拟封印挣脱）
  setTimeout(() => {
    doorsOpening.value = false
    setTimeout(() => { doorsOpening.value = true }, 50)
  }, TIMING.doorPause)

  // 门全开 + 粒子风 + 光环
  setTimeout(() => {
    doorsOpen.value = true
    showParticleWind.value = true
    showLightRing.value = true
  }, TIMING.doorComplete)

  // 登录卡片（延迟显示）
  setTimeout(() => { showCard.value = true }, TIMING.cardShow)
})

function getStarStyle(i) {
  const seed = i * 137.508
  const x = (seed % 100)
  const y = ((seed * 1.618) % 100)
  const size = 0.5 + (seed % 2)
  const duration = 3 + (seed % 5)
  const delay = seed % 3
  return {
    left: `${x}%`,
    top: `${y}%`,
    width: `${size}px`,
    height: `${size}px`,
    animationDuration: `${duration}s`,
    animationDelay: `${delay}s`
  }
}

function getMistParticleStyle(i) {
  const angle = (i / 20) * 360
  const delay = i * 0.05
  return {
    '--angle': `${angle}deg`,
    animationDelay: `${delay}s`
  }
}

// 仙气飘飘加载特效粒子样式
function getParticleStyle(i) {
  const angle = (i / 6) * 360
  return {
    '--angle': `${angle}deg`,
    left: '50%',
    top: '50%',
    transform: `rotate(${angle}deg) translateX(50px)`
  }
}

function getWindParticleStyle(i) {
  // 使用伪随机数生成器，保证每次页面刷新粒子位置一致
  const x = 40 + randFloat(0, 20)
  const y = 30 + randFloat(0, 40)
  const delay = randFloat(0, 0.5)
  const duration = 0.5 + randFloat(0, 0.5)
  return {
    left: `${x}%`,
    top: `${y}%`,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`
  }
}

function getWaveRingStyle(i) {
  return {
    animationDelay: `${i * 0.15}s`
  }
}

async function handleLogin() {
  if (!loginForm.value.email || !loginForm.value.password) {
    ElMessage.warning('请填写邮箱和密码')
    return
  }
  loading.value = true
  try {
    await auth.loginAction(loginForm.value.email, loginForm.value.password)
    ElMessage.success('登录成功')
    router.push('/home')
  } catch {
    // 错误已在api拦截器处理，显示仙气飘飘特效
    // 延迟关闭loading，让特效显示2秒
    setTimeout(() => {
      loading.value = false
    }, 2000)
    return
  }
  loading.value = false
}

async function handleSendCode() {
  if (!registerForm.value.email) {
    ElMessage.warning('请输入邮箱')
    return
  }
  loading.value = true
  try {
    await registerApi(registerForm.value.email)
    registerStep.value = 2
    ElMessage.success('验证码已发送')
  } catch {
    // 错误已在api拦截器处理
  } finally {
    loading.value = false
  }
}

async function handleVerifyCode() {
  if (!registerForm.value.code || !registerForm.value.password) {
    ElMessage.warning('请填写验证码和密码')
    return
  }
  if (registerForm.value.password !== registerForm.value.confirmPassword) {
    ElMessage.warning('两次密码不一致')
    return
  }
  loading.value = true
  try {
    await verifyCodeApi(registerForm.value.email, registerForm.value.code, registerForm.value.password)
    registerStep.value = 3
    ElMessage.success('注册成功')
  } catch {
    // 错误已在api拦截器处理
  } finally {
    loading.value = false
  }
}

function resetRegister() {
  isRegistering.value = false
  registerStep.value = 1
  registerForm.value = { email: '', code: '', password: '', confirmPassword: '' }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #0a1218 0%, #1a2530 50%, #0d1a24 100%);
  position: relative;
  overflow: hidden;
}

/* 星辰夜空背景 */
.starry-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.star {
  position: absolute;
  background: radial-gradient(circle, rgba(200, 220, 240, 0.9) 0%, transparent 70%);
  border-radius: 50%;
  animation: twinkle 3s ease-in-out infinite;
}

@keyframes twinkle {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}

/* 云雾层 */
.mist-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.mist {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.15;
}

.mist-1 {
  width: 600px;
  height: 300px;
  background: linear-gradient(135deg, #4a6a7a 0%, #2a4a5a 100%);
  top: 20%;
  left: -10%;
  animation: mist-drift 20s ease-in-out infinite;
}

.mist-2 {
  width: 500px;
  height: 250px;
  background: linear-gradient(225deg, #3a5a6a 0%, #1a3a4a 100%);
  top: 60%;
  right: -5%;
  animation: mist-drift 25s ease-in-out infinite reverse;
}

.mist-3 {
  width: 700px;
  height: 200px;
  background: linear-gradient(0deg, #5a7a8a 0%, #2a4a5a 100%);
  bottom: 10%;
  left: 20%;
  animation: mist-drift 30s ease-in-out infinite 5s;
}

@keyframes mist-drift {
  0%, 100% { transform: translateX(0) translateY(0); }
  50% { transform: translateX(30px) translateY(-20px); }
}

/* 冰晶琉璃门容器 */
.crystal-door-container {
  position: absolute;
  width: 500px;
  height: 600px;
  display: flex;
  justify-content: center;
  align-items: center;
  perspective: 1000px;
  transform-style: preserve-3d;
}

/* 冰晶门 */
.crystal-door {
  position: absolute;
  width: 200px;
  height: 500px;
  background: linear-gradient(180deg,
    rgba(20, 40, 60, 0.9) 0%,
    rgba(30, 50, 70, 0.85) 30%,
    rgba(40, 60, 80, 0.8) 100%
  );
  border: 2px solid rgba(100, 180, 220, 0.3);
  border-radius: 8px 8px 0 0;
  transition: transform 1.5s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  box-shadow:
    0 0 30px rgba(100, 180, 220, 0.2),
    inset 0 0 50px rgba(100, 180, 220, 0.1);
}

.door-left {
  left: 50%;
  margin-left: -200px;
  transform: translateX(0);
  transform-origin: right center;
}

.door-right {
  left: 50%;
  margin-right: -200px;
  transform: translateX(0);
  transform-origin: left center;
}

/* 开门动画 - 双门往两边水平滑开 */
.crystal-door-container.doors-opening .door-left {
  transform: translateX(-200px);
}

.crystal-door-container.doors-opening .door-right {
  transform: translateX(200px);
}

.crystal-door-container.doors-open .door-left {
  transform: translateX(-200px);
}

.crystal-door-container.doors-open .door-right {
  transform: translateX(200px);
}
.door-surface {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.ice-texture {
  position: absolute;
  inset: 0;
  background:
    repeating-linear-gradient(
      90deg,
      transparent 0px,
      rgba(100, 180, 220, 0.05) 2px,
      transparent 4px
    ),
    repeating-linear-gradient(
      0deg,
      transparent 0px,
      rgba(100, 180, 220, 0.03) 2px,
      transparent 4px
    );
}

/* 流淌的光纹 */
.light-flow {
  position: absolute;
  width: 4px;
  height: 100%;
  background: linear-gradient(180deg,
    transparent 0%,
    rgba(100, 180, 255, 0.6) 20%,
    rgba(150, 220, 255, 0.8) 50%,
    rgba(100, 180, 255, 0.6) 80%,
    transparent 100%
  );
  animation: flow-down 3s linear infinite;
  filter: blur(1px);
  transition: opacity 0.5s ease;
}

.light-flow-1 { left: 20%; animation-delay: 0s; }
.light-flow-2 { left: 50%; animation-delay: 1s; }
.light-flow-3 { left: 80%; animation-delay: 2s; }

.light-flow-1.off { opacity: 0; }
.light-flow-2.off { opacity: 0; }
.light-flow-3.off { opacity: 0; }

@keyframes flow-down {
  0% { transform: translateY(-100%); }
  100% { transform: translateY(100%); }
}

/* 门边缘 */
.door-edge {
  position: absolute;
  top: 0;
  right: 0;
  width: 4px;
  height: 100%;
  background: linear-gradient(180deg,
    rgba(150, 220, 255, 0.8) 0%,
    rgba(100, 180, 220, 0.5) 50%,
    rgba(150, 220, 255, 0.8) 100%
  );
  box-shadow: 0 0 10px rgba(100, 180, 220, 0.5);
}

/* 符文装饰 */
.door-runes {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  align-items: center;
  padding: 40px 0;
}

.rune {
  width: 60px;
  height: 60px;
  border: 2px solid rgba(100, 180, 220, 0.3);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: rune-glow 4s ease-in-out infinite;
}

.rune::before {
  content: '☯';
  font-size: 24px;
  color: rgba(100, 180, 220, 0.5);
}

.rune-1 { animation-delay: 0s; }
.rune-2 { animation-delay: 1.3s; }
.rune-3 { animation-delay: 2.6s; }

@keyframes rune-glow {
  0%, 100% {
    box-shadow: 0 0 5px rgba(100, 180, 220, 0.2);
    border-color: rgba(100, 180, 220, 0.3);
  }
  50% {
    box-shadow: 0 0 20px rgba(100, 180, 220, 0.5);
    border-color: rgba(100, 180, 220, 0.6);
  }
}

/* 门缝寒气 */
.gap-mist {
  position: absolute;
  width: 60px;
  height: 400px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  opacity: 0;
  transition: opacity 0.5s ease;
  pointer-events: none;
}

.gap-mist.mist-visible {
  opacity: 1;
}

.mist-particle {
  position: absolute;
  width: 8px;
  height: 8px;
  background: radial-gradient(circle, rgba(150, 220, 255, 0.8) 0%, transparent 70%);
  border-radius: 50%;
  animation: mist-rise 2s ease-out infinite;
  transform: rotate(var(--angle)) translateY(0);
}

@keyframes mist-rise {
  0% {
    opacity: 0;
    transform: rotate(var(--angle)) translateY(50px) scale(0.5);
  }
  50% {
    opacity: 0.8;
  }
  100% {
    opacity: 0;
    transform: rotate(var(--angle)) translateY(-100px) scale(1.5);
  }
}

/* 粒子风 */
.particle-wind {
  position: absolute;
  width: 300px;
  height: 400px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.particle-wind.wind-active {
  opacity: 1;
}

.wind-particle {
  position: absolute;
  width: 4px;
  height: 4px;
  background: radial-gradient(circle, rgba(150, 220, 255, 0.8) 0%, transparent 70%);
  border-radius: 50%;
  animation: wind-blow 0.8s ease-out forwards;
}

@keyframes wind-blow {
  0% {
    opacity: 1;
    transform: translate(0, 0) scale(1);
  }
  100% {
    opacity: 0;
    transform: translate(calc((var(--x, 100) - 50) * 2px), -80px) scale(0);
  }
}

/* 光环涟漪 */
.light-ring {
  position: absolute;
  width: 200px;
  height: 100px;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  opacity: 0;
  pointer-events: none;
}

.light-ring.ring-visible {
  opacity: 1;
}

.ring {
  position: absolute;
  border: 2px solid rgba(150, 220, 255, 0.5);
  border-radius: 50%;
  animation: ring-expand 1.5s ease-out forwards;
}

.ring-1 {
  width: 100px;
  height: 50px;
  left: 50%;
  transform: translateX(-50%) scale(0);
}

.ring-2 {
  width: 150px;
  height: 75px;
  left: 50%;
  transform: translateX(-50%) scale(0);
  animation-delay: 0.1s;
}

.ring-3 {
  width: 200px;
  height: 100px;
  left: 50%;
  transform: translateX(-50%) scale(0);
  animation-delay: 0.2s;
}

@keyframes ring-expand {
  0% {
    transform: translateX(-50%) scale(0);
    opacity: 1;
  }
  100% {
    transform: translateX(-50%) scale(1);
    opacity: 0;
  }
}

/* 画面震动 */
.shake-overlay {
  position: fixed;
  inset: 0;
  pointer-events: none;
}

.shake-overlay.shake-active {
  animation: screen-shake 0.15s ease-out;
}

@keyframes screen-shake {
  0%, 100% { transform: translate(0, 0); }
  25% { transform: translate(-1px, 1px); }
  50% { transform: translate(1px, -1px); }
  75% { transform: translate(-1px, -0.5px); }
}

/* 空间扭曲波纹 */
.distortion-wave {
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: 0;
}

.distortion-wave.wave-visible {
  opacity: 1;
}

.wave-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border: 1px solid rgba(150, 220, 255, 0.3);
  border-radius: 50%;
  animation: wave-distort 1s ease-out forwards;
}

@keyframes wave-distort {
  0% {
    width: 0;
    height: 0;
    opacity: 0.8;
    filter: blur(0px);
  }
  100% {
    width: 150vw;
    height: 150vh;
    opacity: 0;
    filter: blur(5px);
  }
}

/* 登录卡片 */
.login-card {
  position: relative;
  z-index: 100;
  width: 360px;
  padding: 40px;
  background: rgba(26, 58, 74, 0.85);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(201, 169, 110, 0.3);
  border-radius: 16px;
  box-shadow:
    0 20px 60px rgba(0, 0, 0, 0.5),
    0 0 60px rgba(78, 205, 196, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  opacity: 0;
  transform: translateY(30px);
  transition: opacity 0.4s ease, transform 0.4s ease;
}

/* 金色顶边高光 */
.login-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 10%;
  right: 10%;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--color-gold), transparent);
  border-radius: 0 0 4px 4px;
}

.login-card.card-visible {
  opacity: 1;
  transform: translateY(0);
}

.site-title {
  font-size: 28px;
  text-align: center;
  margin-bottom: 8px;
  background: linear-gradient(135deg, #C9A96E 0%, #F0E6C8 50%, #C9A96E 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 2px 8px rgba(201, 169, 110, 0.3));
}

.site-subtitle {
  font-size: 14px;
  color: var(--color-text-secondary);
  text-align: center;
  margin-bottom: 30px;
  letter-spacing: 4px;
}

.login-form {
  margin-top: 20px;
}

.password-toggle {
  cursor: pointer;
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  transition: color 0.2s;
}

.password-toggle:hover {
  color: var(--color-gold);
}

:deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.95) !important;
  border: 1px solid rgba(78, 205, 196, 0.3) !important;
  box-shadow: none !important;
}

:deep(.el-input__inner) {
  color: #1a1a2e !important;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, var(--color-qi-primary) 0%, #3DB8B0 100%) !important;
  border: 1px solid rgba(78, 205, 196, 0.4) !important;
  box-shadow: 0 4px 15px rgba(78, 205, 196, 0.2) !important;
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #5DE0D8 0%, var(--color-qi-primary) 100%) !important;
}

.register-link {
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 13px;
  margin-top: 20px;
  cursor: pointer;
  transition: color 0.2s;
}

.register-link:hover {
  color: var(--color-gold);
}

/* 注册流程 */
.register-flow {
  margin-top: 20px;
}

.step-title {
  font-size: 16px;
  color: var(--color-text-primary);
  text-align: center;
  margin-bottom: 20px;
}

.back-link {
  text-align: center;
  color: rgba(232, 244, 252, 0.5);
  font-size: 13px;
  margin-top: 20px;
  cursor: pointer;
  transition: color 0.2s;
}

.back-link:hover {
  color: var(--color-qi-primary);
}

.text-center {
  text-align: center;
}

.text-secondary {
  color: rgba(232, 244, 252, 0.6);
  font-size: 14px;
  margin-top: 10px;
}

.success-icon {
  width: 60px;
  height: 60px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, rgba(78, 205, 196, 0.3) 0%, rgba(26, 58, 74, 0.6) 100%);
  border: 2px solid rgba(78, 205, 196, 0.4);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  color: var(--color-qi-primary);
}

/* 备案信息 */
.filing-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 50;
  background: rgba(13, 31, 39, 0.9);
  backdrop-filter: blur(8px);
  border-top: 1px solid rgba(78, 205, 196, 0.15);
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
  color: rgba(232, 244, 252, 0.5);
  text-decoration: none;
  transition: color 0.2s;
}

.filing-links a:hover {
  color: var(--color-qi-primary);
}

.filing-divider {
  color: #ddd;
}

@media (max-width: 768px) {
  .login-card {
    width: 90%;
    padding: 30px 20px;
  }

  .crystal-door-container {
    transform: scale(0.7);
  }
}

/* 仙气飘飘加载特效 */
.fairy-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: inherit;
  overflow: hidden;
}

.fairy-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #E8D5F0 0%, #D0E8F0 100%);
  opacity: 0.95;
}

.fairy-curtain {
  position: absolute;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
  height: 100%;
  width: 60%;
  filter: blur(20px);
  animation: curtain-drift 8s ease-in-out infinite;
}

.fairy-curtain.curtain-1 {
  top: 0;
  animation-delay: 0s;
}

.fairy-curtain.curtain-2 {
  top: 20%;
  animation-delay: -2.5s;
  opacity: 0.7;
}

.fairy-curtain.curtain-3 {
  top: 40%;
  animation-delay: -5s;
  opacity: 0.5;
}

@keyframes curtain-drift {
  0% { left: -60%; transform: translateY(0); }
  50% { transform: translateY(20px); }
  100% { left: 140%; transform: translateY(0); }
}

.fairy-glow {
  position: absolute;
  width: 150px;
  height: 150px;
  background: radial-gradient(circle, rgba(255,255,255,0.8) 0%, transparent 70%);
  border-radius: 50%;
  animation: glow-pulse 3s ease-in-out infinite;
}

@keyframes glow-pulse {
  0%, 100% { transform: scale(0.8); opacity: 0.6; }
  50% { transform: scale(1.2); opacity: 1; }
}

.fairy-ring {
  position: absolute;
  width: 80px;
  height: 80px;
  border: 2px solid rgba(255,255,255,0.6);
  border-radius: 50%;
  animation: ring-rotate 3s linear infinite;
}

.fairy-ring::before {
  content: '';
  position: absolute;
  top: -4px;
  left: 50%;
  width: 8px;
  height: 8px;
  background: rgba(255,255,255,0.9);
  border-radius: 50%;
  box-shadow: 0 0 15px 5px rgba(255,255,255,0.5);
}

@keyframes ring-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.fairy-particles {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.fairy-particle {
  position: absolute;
  width: 6px;
  height: 6px;
  background: radial-gradient(circle, rgba(255,255,255,0.9) 0%, transparent 70%);
  border-radius: 50%;
  animation: particle-orbit 6s ease-in-out infinite;
}

.fairy-particle:nth-child(1) { animation-delay: 0s; }
.fairy-particle:nth-child(2) { animation-delay: -1s; }
.fairy-particle:nth-child(3) { animation-delay: -2s; }
.fairy-particle:nth-child(4) { animation-delay: -3s; }
.fairy-particle:nth-child(5) { animation-delay: -4s; }
.fairy-particle:nth-child(6) { animation-delay: -5s; }

@keyframes particle-orbit {
  0% {
    transform: rotate(0deg) translateX(50px) rotate(0deg);
    opacity: 0.3;
  }
  25% {
    opacity: 0.9;
  }
  50% {
    transform: rotate(180deg) translateX(80px) rotate(-180deg);
    opacity: 0.3;
  }
  75% {
    opacity: 0.9;
  }
  100% {
    transform: rotate(360deg) translateX(50px) rotate(-360deg);
    opacity: 0.3;
  }
}
</style>
