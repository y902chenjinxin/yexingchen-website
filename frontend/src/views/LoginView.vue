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
      <!-- 光效 -->
      <div class="light-effect" v-if="showLight"></div>
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

onMounted(() => {
  // 动画时序：光效 → 云散 → 门开 → 卡片
  setTimeout(() => { showLight.value = true }, 200)
  setTimeout(() => { showClouds.value = true }, 800)
  setTimeout(() => { showDoors.value = true }, 1200)
  setTimeout(() => { showCard.value = true }, 2000)
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
  background: linear-gradient(180deg, var(--color-bg) 0%, var(--color-primary) 100%);
  position: relative;
  overflow: hidden;
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
  background: radial-gradient(ellipse at center, rgba(255,255,255,0.12) 0%, transparent 70%);
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
  background: linear-gradient(180deg, #3D2517 0%, #2A1A0F 100%);
  border: 4px solid var(--color-gold);
  transition: transform 1200ms cubic-bezier(0.65, 0, 0.35, 1);
}

.door-left {
  left: 0;
  border-right: 2px solid var(--color-gold);
  transform-origin: left center;
}

.door-right {
  right: 0;
  border-left: 2px solid var(--color-gold);
  transform-origin: right center;
}

.doors-open .door-left {
  transform: scaleX(0);
}

.doors-open .door-right {
  transform: scaleX(0);
}

/* 光效 */
.light-effect {
  position: absolute;
  width: 30%;
  height: 200%;
  top: -50%;
  left: -30%;
  background: linear-gradient(90deg, transparent, rgba(201,169,98,0.8), rgba(255,255,255,0.4), transparent);
  transform: rotate(-15deg);
  animation: light-sweep 800ms ease-in-out forwards;
  pointer-events: none;
}

/* 登录卡片 */
.login-card {
  position: relative;
  z-index: 10;
  width: 420px;
  padding: 40px 50px;
  background: rgba(26, 58, 74, 0.85);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(78, 205, 196, 0.3);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 600ms ease-out, transform 600ms ease-out;
}

.card-visible {
  opacity: 1;
  transform: translateY(0);
}

.site-title {
  font-size: 26px;
  color: var(--color-text);
  text-align: center;
  margin-bottom: 8px;
}

.site-subtitle {
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 14px;
  margin-bottom: 30px;
}

.login-form {
  margin-top: 20px;
}

.register-link,
.back-link {
  text-align: center;
  color: var(--color-accent);
  font-size: 14px;
  cursor: pointer;
  margin-top: 15px;
  transition: color 0.3s;
}

.register-link:hover,
.back-link:hover {
  color: var(--color-text);
}

.register-flow {
  margin-top: 20px;
}

.step-content {
  margin-top: 15px;
}

.step-title {
  color: var(--color-text);
  font-size: 16px;
  margin-bottom: 15px;
}

.back-link {
  margin-top: 20px;
}

.text-center {
  text-align: center;
}

.text-secondary {
  color: var(--color-text-secondary);
  font-size: 14px;
  margin-top: 10px;
}

.success-icon {
  width: 60px;
  height: 60px;
  margin: 0 auto 20px;
  border: 3px solid var(--color-accent);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  color: var(--color-accent);
}
</style>