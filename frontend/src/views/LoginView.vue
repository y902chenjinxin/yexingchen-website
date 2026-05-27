<template>
  <div class="login-page">
    <!-- 动画层 -->
    <div class="animation-overlay" :class="{ 'clouds-open': showClouds}">
      <!-- 云雾左 -->
      <div class="cloud cloud-left"></div>
      <!-- 云雾右 -->
      <div class="cloud cloud-right"></div>
    </div>

    <!-- 木门 -->
    <div class="door-container" :class="{ 'doors-open': showDoors }">
      <div class="door door-left"></div>
      <div class="door door-right"></div>
      <!-- 纯净白光效 -->
      <div class="light-effect" v-if="showLight"></div>
      <!-- 开门光芒绽放 -->
      <div class="glow-burst" v-if="showGlow"></div>
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
const showLight = ref(false)
const showClouds = ref(false)
const showDoors = ref(false)
const showCard = ref(false)
const showGlow = ref(false)

onMounted(() => {
  // 动画时序：延长到1.5s，光效延长
  setTimeout(() => { showLight.value = true }, 300)
  setTimeout(() => { showClouds.value = true }, 900)
  setTimeout(() => { showDoors.value = true; showGlow.value = true }, 1500)
  setTimeout(() => { showCard.value = true }, 2500)
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
    ElMessage.success('验证码已发送到邮箱')
    registerStep.value = 2
  } catch {
    // 错误已在api拦截器处理
  } finally {
    loading.value = false
  }
}

async function handleVerifyCode() {
  if (!registerForm.value.code || registerForm.value.code.length !== 6) {
    ElMessage.warning('请输入6位验证码')
    return
  }
  if (!registerForm.value.password) {
    ElMessage.warning('请设置密码')
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
  background: #0a0f14;
  position: relative;
  overflow: hidden;
}

/* 水墨山水背景层 */
.login-page::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    /* 远山剪影 */
    radial-gradient(ellipse 80% 40% at 20% 70%, rgba(30, 50, 40, 0.6) 0%, transparent 70%),
    radial-gradient(ellipse 60% 35% at 80% 65%, rgba(25, 45, 35, 0.5) 0%, transparent 65%),
    radial-gradient(ellipse 40% 25% at 50% 80%, rgba(20, 40, 30, 0.4) 0%, transparent 60%),
    /* 月光 */
    radial-gradient(circle at 75% 15%, rgba(200, 210, 200, 0.08) 0%, transparent 40%),
    /* 整体氛围 */
    linear-gradient(180deg, #0d1215 0%, #151c1f 50%, #0a0f14 100%);
  pointer-events: none;
}

/* 墨韵层次 */
.login-page::after {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 100% 50% at 0% 100%, rgba(20, 35, 30, 0.4) 0%, transparent 60%),
    radial-gradient(ellipse 80% 40% at 100% 90%, rgba(25, 40, 35, 0.3) 0%, transparent 50%);
  pointer-events: none;
}

/* 云雾 */
.animation-overlay {
  position: absolute;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.cloud {
  position: absolute;
  width: 50%;
  height: 100%;
  background: linear-gradient(90deg,
    rgba(200, 210, 200, 0.05) 0%,
    rgba(200, 210, 200, 0.1) 50%,
    rgba(200, 210, 200, 0.05) 100%
  );
  transition: opacity 1000ms ease-out, transform 1000ms ease-out;
}

.cloud-left {
  left: 0;
  transform-origin: left center;
}

.cloud-right {
  right: 0;
  transform-origin: right center;
}

.clouds-open .cloud-left {
  transform: translateX(-100%);
  opacity: 0;
}

.clouds-open .cloud-right {
  transform: translateX(100%);
  opacity: 0;
}

/* 木门 */
.door-container {
  position: absolute;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.door {
  position: absolute;
  width: 50%;
  height: 100%;
  background: linear-gradient(180deg, #1a1512 0%, #0d0a08 100%);
  border: 2px solid rgba(201, 169, 110, 0.3);
  transition: transform 1200ms cubic-bezier(0.65, 0, 0.35, 1);
}

.door-left {
  left: 0;
  border-right: 1px solid rgba(201, 169, 110, 0.2);
  transform-origin: left center;
}

.door-right {
  right: 0;
  border-left: 1px solid rgba(201, 169, 110, 0.2);
  transform-origin: right center;
}

/* 门框金线 */
.door::before {
  content: '';
  position: absolute;
  inset: 20px 10px;
  border: 1px solid rgba(201, 169, 110, 0.15);
  pointer-events: none;
}

.doors-open .door-left {
  transform: scaleX(0);
}

.doors-open .door-right {
  transform: scaleX(0);
}

/* 灵气光效 - 青绿色 */
.light-effect {
  position: absolute;
  width: 20%;
  height: 300%;
  top: -100%;
  left: -20%;
  background: linear-gradient(90deg,
    transparent 0%,
    rgba(127, 255, 212, 0.05) 20%,
    rgba(127, 255, 212, 0.4) 45%,
    rgba(127, 255, 212, 0.6) 50%,
    rgba(127, 255, 212, 0.4) 55%,
    rgba(127, 255, 212, 0.05) 80%,
    transparent 100%
  );
  transform: rotate(-15deg);
  animation: spirit-flow 2000ms ease-out forwards;
  pointer-events: none;
  filter: blur(3px);
}

/* 开门灵气绽放 */
.glow-burst {
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  background: radial-gradient(ellipse at center, rgba(127, 255, 212, 0.3) 0%, rgba(127, 255, 212, 0.1) 30%, transparent 60%);
  animation: spirit-burst 1000ms ease-out forwards;
  pointer-events: none;
}

/* 登录卡片 - 磨砂玻璃+金边框 */
.login-card {
  position: relative;
  z-index: 10;
  width: 400px;
  padding: 45px 50px;
  background: rgba(20, 25, 22, 0.85);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(201, 169, 110, 0.25);
  border-radius: 4px;
  box-shadow:
    0 0 60px rgba(0, 0, 0, 0.5),
    0 0 30px rgba(127, 255, 212, 0.05),
    inset 0 1px 0 rgba(201, 169, 110, 0.1);
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 600ms ease-out, transform 600ms ease-out;
}

.login-card::before {
  content: '';
  position: absolute;
  top: -1px;
  left: 20%;
  right: 20%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(201, 169, 110, 0.5), transparent);
}

.card-visible {
  opacity: 1;
  transform: translateY(0);
}

.site-title {
  font-size: 24px;
  color: #e8f0e8;
  text-align: center;
  margin-bottom: 6px;
  font-weight: normal;
  letter-spacing: 4px;
  text-shadow: 0 0 30px rgba(127, 255, 212, 0.2);
}

.site-subtitle {
  text-align: center;
  color: rgba(201, 169, 110, 0.6);
  font-size: 13px;
  margin-bottom: 35px;
  letter-spacing: 2px;
}

.login-form {
  margin-top: 20px;
}

/* 表单样式override */
.login-form :deep(.el-input__wrapper) {
  background: rgba(15, 20, 18, 0.8);
  border: 1px solid rgba(201, 169, 110, 0.2);
  box-shadow: none;
}

.login-form :deep(.el-input__inner) {
  color: #e8f0e8;
}

.login-form :deep(.el-input__inner::placeholder) {
  color: rgba(201, 169, 110, 0.4);
}

.login-form :deep(.el-button--primary) {
  background: linear-gradient(135deg, rgba(127, 255, 212, 0.2) 0%, rgba(127, 255, 212, 0.1) 100%);
  border-color: rgba(127, 255, 212, 0.3);
  color: #e8f0e8;
}

.login-form :deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, rgba(127, 255, 212, 0.3) 0%, rgba(127, 255, 212, 0.2) 100%);
  border-color: rgba(127, 255, 212, 0.5);
}

.register-link,
.back-link {
  text-align: center;
  color: rgba(201, 169, 110, 0.6);
  font-size: 13px;
  cursor: pointer;
  margin-top: 15px;
  transition: color 0.3s;
}

.register-link:hover,
.back-link:hover {
  color: rgba(201, 169, 110, 0.9);
}

.register-flow {
  margin-top: 20px;
}

.step-content {
  margin-top: 15px;
}

.step-title {
  color: rgba(201, 169, 110, 0.8);
  font-size: 14px;
  margin-bottom: 15px;
  text-align: center;
}

.back-link {
  margin-top: 20px;
}

.text-center {
  text-align: center;
}

.text-secondary {
  color: rgba(201, 169, 110, 0.5);
  font-size: 13px;
  margin-top: 10px;
}

.success-icon {
  width: 50px;
  height: 50px;
  margin: 0 auto 20px;
  border: 1px solid rgba(127, 255, 212, 0.4);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: rgba(127, 255, 212, 0.8);
}

/* 灵气流动动画 */
@keyframes spirit-flow {
  0% {
    left: -30%;
    opacity: 0;
  }
  20% {
    opacity: 1;
  }
  80% {
    opacity: 1;
  }
  100% {
    left: 120%;
    opacity: 0;
  }
}

@keyframes spirit-burst {
  0% {
    opacity: 0.8;
    transform: scale(0.8);
  }
  100% {
    opacity: 0;
    transform: scale(1.5);
  }
}
</style>