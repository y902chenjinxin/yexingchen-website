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
      <el-form v-if="!isRegistering" class="login-form" :model="loginForm" @submit.prevent="handleLogin">
        <el-form-item>
          <el-input v-model="loginForm.email" placeholder="邮箱" size="large" clearable />
        </el-form-item>
        <el-form-item>
          <el-input v-model="loginForm.password" type="password" placeholder="密码" size="large" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" style="width: 100%" :loading="loading" native-type="submit">
            登 录
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 注册流程 -->
      <div v-else class="register-flow">
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
              <el-input v-model="registerForm.password" type="password" placeholder="设置密码" size="large" show-password />
            </el-form-item>
            <el-form-item>
              <el-input v-model="registerForm.confirmPassword" type="password" placeholder="确认密码" size="large" show-password />
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

const router = useRouter()
const auth = useAuthStore()

const loginForm = ref({ email: '', password: '' })
const registerForm = ref({ email: '', code: '', password: '', confirmPassword: '' })
const isRegistering = ref(false)
const registerStep = ref(1)
const loading = ref(false)

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
  // 动画时序（毫秒）
  const TIMING = {
    lightFlowOff1: 0,
    lightFlowOff2: 200,
    lightFlowOff3: 400,
    gapMist: 600,        // 门缝寒气出现
    doorStart: 800,      // 门开始打开
    doorPause: 1900,      // 门45度停顿（延长到1.5s）
    doorResume: 1950,     // 门继续开
    doorComplete: 2300,  // 门全开（1.5s延长）
    particleWind: 2350,  // 粒子风吹出
    lightRing: 2400,     // 光环涟漪
    // 去掉震动效果
    cardShow: 3300       // 登录卡片出现（延迟0.6s）
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

function getWindParticleStyle(i) {
  const x = 40 + Math.random() * 20
  const y = 30 + Math.random() * 40
  const delay = Math.random() * 0.5
  const duration = 0.5 + Math.random() * 0.5
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
    // 错误已在api拦截器处理
  } finally {
    loading.value = false
  }
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
  transform-origin: left center;
  transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  box-shadow:
    0 0 30px rgba(100, 180, 220, 0.2),
    inset 0 0 50px rgba(100, 180, 220, 0.1);
}

.door-left {
  left: 0;
  right: 50%;
  transform: translateZ(0) rotateY(0deg);
}

.door-right {
  left: 50%;
  right: 0;
  transform: translateZ(0) rotateY(0deg);
}

/* 门表面纹理 */
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

/* 开门动画 - 双门对称展开 */
.crystal-door-container.doors-opening .door-left {
  transform: translateZ(0) rotateY(-85deg);
  transition: transform 1.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.crystal-door-container.doors-opening .door-right {
  transform: translateZ(0) rotateY(85deg);
  transition: transform 1.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.crystal-door-container.doors-open .door-left {
  transform: translateZ(0) rotateY(-90deg);
}

.crystal-door-container.doors-open .door-right {
  transform: translateZ(0) rotateY(90deg);
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
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(201, 169, 110, 0.4);
  border-radius: 16px;
  box-shadow:
    0 20px 60px rgba(0, 0, 0, 0.3),
    0 0 40px rgba(201, 169, 110, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  opacity: 0;
  transform: translateY(30px);
  transition: opacity 0.8s ease, transform 0.8s ease;
}

.login-card.card-visible {
  opacity: 1;
  transform: translateY(0);
}

.site-title {
  font-size: 28px;
  color: #2D3748;
  text-align: center;
  margin-bottom: 8px;
  text-shadow: 0 2px 4px rgba(255, 255, 255, 0.5);
}

.site-subtitle {
  font-size: 14px;
  color: #6B7280;
  text-align: center;
  margin-bottom: 30px;
  letter-spacing: 4px;
}

.login-form {
  margin-top: 20px;
}

:deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.6) !important;
  border: 1px solid rgba(201, 169, 110, 0.3) !important;
  box-shadow: none !important;
}

:deep(.el-input__inner) {
  color: #2D3748 !important;
}

:deep(.el-input__inner::placeholder) {
  color: #9CA3AF !important;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, var(--color-gold) 0%, #B8956A 100%) !important;
  border: 1px solid rgba(201, 169, 110, 0.5) !important;
  box-shadow: 0 4px 15px rgba(201, 169, 110, 0.3) !important;
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #D4B872 0%, #C9A962 100%) !important;
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
  color: var(--color-text);
  text-align: center;
  margin-bottom: 20px;
}

.back-link {
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 13px;
  margin-top: 20px;
  cursor: pointer;
  transition: color 0.2s;
}

.back-link:hover {
  color: rgba(150, 200, 220, 1);
}

.text-center {
  text-align: center;
}

.text-secondary {
  color: rgba(150, 200, 220, 0.6);
  font-size: 14px;
  margin-top: 10px;
}

.success-icon {
  width: 60px;
  height: 60px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, rgba(60, 120, 160, 0.5) 0%, rgba(40, 80, 120, 0.6) 100%);
  border: 2px solid rgba(100, 180, 220, 0.4);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  color: #c8e8f8;
}

/* 备案信息 */
.filing-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 50;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
  border-top: 1px solid rgba(201, 169, 110, 0.2);
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
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: color 0.2s;
}

.filing-links a:hover {
  color: var(--color-gold);
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
</style>