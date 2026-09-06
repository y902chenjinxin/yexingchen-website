<template>
  <div class="login-page">
    <!-- 雨青粒子网背景（博客式：粒子间连线，鼠标移过线条聚拢） -->
    <canvas ref="particleCanvas" class="particle-bg" aria-hidden="true"></canvas>

    <!-- 登录卡片 -->
    <div class="login-card">
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

      <!-- 登录加载特效 -->
      <div v-if="loading && !isRegistering" class="fairy-loading">
        <div class="fairy-glow"></div>
        <div class="fairy-ring"></div>
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
import { ref, onBeforeUnmount, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { register as registerApi, verifyCode as verifyCodeApi } from '@/api/auth'

const router = useRouter()
const auth = useAuthStore()

const route = useRoute()
const loginForm = ref({ email: '', password: '' })
const registerForm = ref({ email: '', code: '', password: '', confirmPassword: '' })
const isRegistering = ref(false)
const registerStep = ref(1)
const loading = ref(false)
const passwordVisible = ref(false)
const confirmPasswordVisible = ref(false)

/** ============ 雨青粒子网背景 ============ */
const particleCanvas = ref(null)
let pctx = null
let particles = []
let rafId = 0
let resizeTimer = 0
const pointer = { x: -9999, y: -9999 }
let reduceMotion = false

const PARTICLE_COUNT = 72       // 粒子数量
const LINK_DIST = 130           // 粒子间连线最大距离
const POINTER_DIST = 190        // 鼠标影响半径
const BASE_SPEED = 0.32         // 克制漂移速度
const MAX_SPEED = 0.9

const COL_LINE = '127, 168, 163'        // 雨青连线
const COL_POINTER = '168, 211, 206'     // 鼠标连线偏亮
const COL_HALO = '168, 211, 206'        // 粒子光晕
const COL_CORE = '206, 226, 220'        // 粒子核

function initParticles(w, h) {
  particles = []
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    particles.push({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 2 * BASE_SPEED,
      vy: (Math.random() - 0.5) * 2 * BASE_SPEED,
      r: 0.7 + Math.random() * 1.5
    })
  }
}

function setupCanvas() {
  const canvas = particleCanvas.value
  if (!canvas) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const w = canvas.clientWidth
  const h = canvas.clientHeight
  canvas.width = w * dpr
  canvas.height = h * dpr
  pctx = canvas.getContext('2d')
  pctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  initParticles(w, h)
}

function draw() {
  if (rafId) cancelAnimationFrame(rafId)
  if (reduceMotion) return
  rafId = requestAnimationFrame(draw)
  const canvas = particleCanvas.value
  if (!canvas || !pctx) return
  const w = canvas.clientWidth
  const h = canvas.clientHeight
  if (!w || !h) return
  pctx.clearRect(0, 0, w, h)

  // 更新位置 + 鼠标吸引
  for (const p of particles) {
    const dxp = pointer.x - p.x
    const dyp = pointer.y - p.y
    const dp = Math.hypot(dxp, dyp)
    if (dp < POINTER_DIST && dp > 0.5) {
      const pull = (1 - dp / POINTER_DIST) * 0.022
      p.vx += (dxp / dp) * pull
      p.vy += (dyp / dp) * pull
    }
    const sp = Math.hypot(p.vx, p.vy)
    if (sp > MAX_SPEED) {
      p.vx = (p.vx / sp) * MAX_SPEED
      p.vy = (p.vy / sp) * MAX_SPEED
    }
    p.x += p.vx
    p.y += p.vy
    if (p.x < 0) { p.x = 0; p.vx *= -1 }
    else if (p.x > w) { p.x = w; p.vx *= -1 }
    if (p.y < 0) { p.y = 0; p.vy *= -1 }
    else if (p.y > h) { p.y = h; p.vy *= -1 }
  }

  pctx.lineWidth = 1
  // 粒子间连线
  for (let i = 0; i < particles.length; i++) {
    const a = particles[i]
    for (let j = i + 1; j < particles.length; j++) {
      const b = particles[j]
      const dx = a.x - b.x
      const dy = a.y - b.y
      const d = Math.hypot(dx, dy)
      if (d < LINK_DIST) {
        const alpha = (1 - d / LINK_DIST) * 0.15
        pctx.strokeStyle = `rgba(${COL_LINE}, ${alpha.toFixed(3)})`
        pctx.beginPath()
        pctx.moveTo(a.x, a.y)
        pctx.lineTo(b.x, b.y)
        pctx.stroke()
      }
    }
    // 鼠标连线（指针周围线条聚拢）
    if (pointer.x > -9000 && pointer.y > -9000) {
      const dp = Math.hypot(a.x - pointer.x, a.y - pointer.y)
      if (dp < POINTER_DIST) {
        const alpha = (1 - dp / POINTER_DIST) * 0.30
        pctx.strokeStyle = `rgba(${COL_POINTER}, ${alpha.toFixed(3)})`
        pctx.beginPath()
        pctx.moveTo(a.x, a.y)
        pctx.lineTo(pointer.x, pointer.y)
        pctx.stroke()
      }
    }
  }

  // 粒子（光晕 + 核）
  for (const p of particles) {
    const halo = pctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 4)
    halo.addColorStop(0, `rgba(${COL_HALO}, 0.50)`)
    halo.addColorStop(1, `rgba(${COL_HALO}, 0)`)
    pctx.fillStyle = halo
    pctx.beginPath()
    pctx.arc(p.x, p.y, p.r * 4, 0, Math.PI * 2)
    pctx.fill()
    pctx.fillStyle = `rgba(${COL_CORE}, 0.9)`
    pctx.beginPath()
    pctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
    pctx.fill()
  }
}

function onPointerMove(e) {
  const canvas = particleCanvas.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  pointer.x = e.clientX - rect.left
  pointer.y = e.clientY - rect.top
}

function onPointerLeave() {
  pointer.x = -9999
  pointer.y = -9999
}

function onResize() {
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    setupCanvas()
  }, 150)
}

onMounted(() => {
  setupCanvas()
  window.addEventListener('resize', onResize)
  window.addEventListener('pointermove', onPointerMove, { passive: true })
  window.addEventListener('pointerout', onPointerLeave)
  draw()
})

onBeforeUnmount(() => {
  if (rafId) cancelAnimationFrame(rafId)
  clearTimeout(resizeTimer)
  window.removeEventListener('resize', onResize)
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerout', onPointerLeave)
})

async function handleLogin() {
  if (!loginForm.value.email || !loginForm.value.password) {
    ElMessage.warning('请填写邮箱和密码')
    return
  }
  loading.value = true
  try {
    await auth.loginAction(loginForm.value.email, loginForm.value.password)
    ElMessage.success('登录成功')
    // 登录后默认进入工作台
    const next = (route.query.next && String(route.query.next)) || '/workbench'
    router.push(next)
  } catch {
    // 错误已在api拦截器处理
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
  background:
    radial-gradient(ellipse 70% 50% at 20% 12%, rgba(127, 168, 163, 0.10), transparent 60%),
    radial-gradient(ellipse 60% 45% at 82% 78%, rgba(199, 169, 107, 0.07), transparent 60%),
    linear-gradient(180deg, #0a1218 0%, #111a22 52%, #0b1419 100%);
  position: relative;
  overflow: hidden;
}

/* 雨青粒子网画布 */
.particle-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

/* 登录卡片（克制淡入，无位移/无 blur 动画，避免逐帧重绘卡顿） */
.login-card {
  position: relative;
  z-index: 100;
  width: 360px;
  padding: 40px;
  background: rgba(20, 28, 36, 0.6);
  -webkit-backdrop-filter: blur(24px) saturate(185%);
  backdrop-filter: blur(24px) saturate(185%);
  border: 1px solid rgba(255, 255, 255, 0.10);
  border-radius: 20px;
  box-shadow:
    0 1px 1px rgba(0, 0, 0, 0.04),
    0 8px 24px rgba(0, 0, 0, 0.10),
    0 24px 60px rgba(0, 0, 0, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
  opacity: 0;
  animation: card-in 0.5s ease-out 0.15s forwards;
}

@keyframes card-in {
  from { opacity: 0; }
  to { opacity: 1; }
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
  background: rgba(24, 32, 41, 0.7) !important;
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(127, 168, 163, 0.3) !important;
  border-radius: 10px !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
  transition: border-color 0.25s ease, box-shadow 0.25s ease;
}

:deep(.el-input__wrapper:hover),
:deep(.el-input__wrapper.is-focus) {
  border-color: rgba(127, 168, 163, 0.6) !important;
}

:deep(.el-input__inner) {
  color: var(--color-text) !important;
}

:deep(.el-input__inner::placeholder) {
  color: rgba(200, 214, 208, 0.5) !important;
}

:deep(.el-input__suffix .el-icon),
:deep(.el-input__clear),
:deep(.el-input__password) {
  color: rgba(200, 214, 208, 0.7) !important;
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

/* 登录加载特效（克制：仅中央呼吸光 + 旋转细环） */
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
  pointer-events: none;
}

.fairy-glow {
  position: absolute;
  width: 110px;
  height: 110px;
  background: radial-gradient(circle, rgba(127, 168, 163, 0.25) 0%, transparent 70%);
  border-radius: 50%;
  animation: glow-pulse 2.2s ease-in-out infinite;
}

@keyframes glow-pulse {
  0%, 100% { transform: scale(0.85); opacity: 0.6; }
  50% { transform: scale(1.1); opacity: 1; }
}

.fairy-ring {
  position: absolute;
  width: 76px;
  height: 76px;
  border: 1.5px solid rgba(127, 168, 163, 0.45);
  border-radius: 50%;
  border-top-color: rgba(199, 169, 107, 0.7);
  animation: ring-rotate 1.1s linear infinite;
}

@keyframes ring-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
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
}

@media (prefers-reduced-motion: reduce) {
  .login-card {
    animation: none;
    opacity: 1;
  }
}
</style>