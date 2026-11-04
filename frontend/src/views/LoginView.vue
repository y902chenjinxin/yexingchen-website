<template>
  <div class="login-page">
    <!-- 液态玻璃氛围层：三团彩晕漂移 + 透视网格（v2.46.364 方案④，替代旧粒子网） -->
    <div class="lg-ambient" aria-hidden="true">
      <span class="lg-orb lg-orb--a"></span>
      <span class="lg-orb lg-orb--b"></span>
      <span class="lg-orb lg-orb--c"></span>
      <span class="lg-grid"></span>
      <!-- v2.46.366 纯白浮尘：细白点慢漂 + 微闪，无光晕无连线 -->
      <canvas ref="dustCanvas" class="lg-dust"></canvas>
    </div>

    <!-- 登录卡片 -->
    <div ref="cardEl" class="login-card">
      <h1 class="site-title font-serif">星阁</h1>

      <!-- 登录表单 -->
      <el-form v-if="!isRegistering" class="login-form" :model="loginForm" @submit.prevent="handleLogin" aria-label="登录表单">
        <el-form-item>
          <!-- v2.40.22：spellcheck 关掉（浏览器给邮箱画红波浪线）；autocomplete 用标准语义，
               让密码管理器把这里识别成正经登录框，而不是在页面上乱弹悬浮推荐 -->
          <el-input v-model="loginForm.email" placeholder="邮箱" size="large" clearable aria-label="邮箱"
            name="email" autocomplete="username" spellcheck="false" autocapitalize="off" autocorrect="off" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="loginForm.password" :type="passwordVisible ? 'text' : 'password'" placeholder="密码" size="large" aria-label="密码"
            name="password" autocomplete="current-password">
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
          <div class="login-options">
            <label class="remember-label">
              <input v-model="rememberMe" type="checkbox" class="remember-check" />
              <span>记住我</span>
            </label>
            <span class="remember-hint">下次自动填充账号</span>
          </div>
        </el-form-item>
        <el-form-item>
          <TechButton block :loading="loading" native-type="submit" aria-label="登录按钮">登 录</TechButton>
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
              <el-input v-model="registerForm.email" placeholder="邮箱地址" size="large" clearable
                name="email" autocomplete="username" spellcheck="false" autocapitalize="off" autocorrect="off" />
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
              <el-input v-model="registerForm.password" :type="passwordVisible ? 'text' : 'password'" placeholder="设置密码" size="large"
                name="new-password" autocomplete="new-password">
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
              <el-input v-model="registerForm.confirmPassword" :type="confirmPasswordVisible ? 'text' : 'password'" placeholder="确认密码" size="large"
                name="new-password" autocomplete="new-password">
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
          <div class="success-icon"><AppIcon icon="✓" :size="30" /></div>
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
import TechButton from '@/components/common/TechButton.vue'
import AppIcon from '@/components/common/AppIcon.vue'

/** ============ 液态玻璃：卡片鼠标视差（v2.46.364 方案④） ============
 * 仅精确指针（桌面）且未开启「减弱动态效果」时启用，手机端自动跳过；
 * rAF 节流，指针离开窗口复位。氛围层（光晕/网格）为纯 CSS 动画，无 JS。 */
const cardEl = ref(null)
let tiltRaf = 0
let tiltEnabled = false

function onTiltMove(e) {
  const el = cardEl.value
  if (!el) return
  const r = el.getBoundingClientRect()
  const nx = (e.clientX - r.left) / r.width - 0.5
  const ny = (e.clientY - r.top) / r.height - 0.5
  if (tiltRaf) cancelAnimationFrame(tiltRaf)
  tiltRaf = requestAnimationFrame(() => {
    if (!cardEl.value) return
    cardEl.value.style.transform =
      `perspective(900px) rotateY(${(nx * 8).toFixed(2)}deg) rotateX(${(-ny * 6).toFixed(2)}deg)`
  })
}

function onTiltLeave() {
  if (tiltRaf) cancelAnimationFrame(tiltRaf)
  if (cardEl.value) cardEl.value.style.transform = ''
}

/** ============ 纯白粒子星座网（v2.46.367，v2.46.368 加密） ============
 * 夜星要求：线条那种粒子特效——白点之间互相连线成网，鼠标靠近也拉线；
 * 仍然纯度纯白、不带光晕。
 *
 * 做法：
 *  - 白点半径 0.7~2.1px、透明度 0.25~0.6，随机方向匀速漂移，撞边反弹
 *  - 两点距离 < linkDist（按屏幕短边自适应 90~150px）时连线，越近越亮，
 *    最亮 alpha 0.30，线宽 1px；按距离分 5 档批量 path 描边（省 draw call）
 *  - 指针 170px 内拉线（alpha 0.34），鼠标离开即断
 *  - 卡片区不消失而是「淡出」：卡矩形外 90px 内羽化，卡后压到 18%，
 *    避免线条糊在玻璃卡背后显脏
 * 全程不设 shadowBlur、不用径向渐变 → 零发光感。
 * 性能：DPR≤2、页面隐藏停 rAF、减动效只画静态帧、帧间隔归一化 60fps。
 * 密度：v2.46.368 按夜星「粒子有点少」把基准 120→180，同时把 linkDist
 *   系数 .20→.135 收窄——线数约等于 n²·L²，只加粒子会让网瞬间糊成一团，
 *   加密时两个旋钮要一起动（当前 1080p 约 430 条线，观感与加密前同级）。 */
const dustCanvas = ref(null)
let dustCtx = null
let dustDots = []
let dustRaf = 0
let dustTimer = 0
let dustLast = 0
let dustStatic = false
let dustLinkDist = 130
let dustCardBox = null          // 卡片相对 canvas 的矩形（用于卡区淡出）
const dustPointer = { x: -9999, y: -9999, on: false }

const TAU = Math.PI * 2
const DUST_REF_AREA = 1920 * 937
const DUST_BASE = 180            // 1920×937 基准 180 粒（v2.46.368：120→180）
const DUST_MIN = 64
const DUST_MAX = 210
const LINK_DIST_MIN = 90         // 连线距离下限（手机小屏）
const LINK_DIST_MAX = 150        // 连线距离上限（大屏）
const LINK_DIST_RATIO = 0.135    // 连线距离 = 屏幕短边 × 该系数
const LINK_ALPHA = 0.30          // 连线最亮值（两点重合时）
const LINK_BANDS = 5             // 连线亮度分档数
const POINTER_LINK_DIST = 170    // 指针拉线半径
const POINTER_LINK_ALPHA = 0.34
const CARD_FEATHER = 90          // 卡片区羽化宽度
const CARD_MIN_FADE = 0.18       // 卡片正后方压到的比例

function dustCount(w, h) {
  return Math.max(DUST_MIN, Math.min(DUST_MAX, Math.round((DUST_BASE * w * h) / DUST_REF_AREA)))
}

function initDust(w, h) {
  dustDots = []
  const n = dustCount(w, h)
  for (let i = 0; i < n; i++) {
    const ang = Math.random() * TAU
    const sp = 0.16 + Math.random() * 0.42
    dustDots.push({
      x: Math.random() * w,
      y: Math.random() * h,
      r: 0.7 + Math.random() * 1.4,
      a: 0.25 + Math.random() * 0.35,
      vx: Math.cos(ang) * sp,
      vy: Math.sin(ang) * sp,
      f: 1,                                 // 本帧的卡片淡出系数
    })
  }
}

// 卡片区淡出：矩形内 18%，外扩 CARD_FEATHER 内线性回升到 100%
function cardFade(x, y) {
  const b = dustCardBox
  if (!b) return 1
  const dx = x < b.x ? b.x - x : (x > b.x + b.w ? x - (b.x + b.w) : 0)
  const dy = y < b.y ? b.y - y : (y > b.y + b.h ? y - (b.y + b.h) : 0)
  if (!dx && !dy) return CARD_MIN_FADE
  const d = Math.sqrt(dx * dx + dy * dy)
  if (d >= CARD_FEATHER) return 1
  return CARD_MIN_FADE + (1 - CARD_MIN_FADE) * (d / CARD_FEATHER)
}

function measureCardBox() {
  const canvas = dustCanvas.value
  const card = cardEl.value
  if (!canvas || !card) { dustCardBox = null; return }
  const cr = card.getBoundingClientRect()
  const xr = canvas.getBoundingClientRect()
  dustCardBox = { x: cr.left - xr.left, y: cr.top - xr.top, w: cr.width, h: cr.height }
}

function setupDust() {
  const canvas = dustCanvas.value
  if (!canvas) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const w = canvas.clientWidth
  const h = canvas.clientHeight
  if (!w || !h) return
  canvas.width = Math.round(w * dpr)
  canvas.height = Math.round(h * dpr)
  dustCtx = canvas.getContext('2d')
  if (!dustCtx) return
  dustCtx.setTransform(dpr, 0, 0, dpr, 0, 0)
  dustLinkDist = Math.max(LINK_DIST_MIN, Math.min(LINK_DIST_MAX, Math.min(w, h) * LINK_DIST_RATIO))
  measureCardBox()
  initDust(w, h)
}

function paintDust(ts) {
  const canvas = dustCanvas.value
  const ctx = dustCtx
  if (!canvas || !ctx) return
  const w = canvas.clientWidth
  const h = canvas.clientHeight
  if (!w || !h) return
  // 帧间隔归一化到 60fps：掉帧不加速，长时间挂起后夹取
  const dt = dustLast ? Math.min(3, Math.max(0.2, (ts - dustLast) / 16.67)) : 1
  dustLast = ts
  ctx.clearRect(0, 0, w, h)

  // 1) 位置更新：匀速漂移，撞边反弹（不用回绕，网眼才不停重组）
  for (const d of dustDots) {
    d.x += d.vx * dt
    d.y += d.vy * dt
    if (d.x < d.r) { d.x = d.r; d.vx = Math.abs(d.vx) }
    else if (d.x > w - d.r) { d.x = w - d.r; d.vx = -Math.abs(d.vx) }
    if (d.y < d.r) { d.y = d.r; d.vy = Math.abs(d.vy) }
    else if (d.y > h - d.r) { d.y = h - d.r; d.vy = -Math.abs(d.vy) }
    d.f = cardFade(d.x, d.y)
  }

  // 2) 点间连线：按距离分档收集到 5 条 Path2D，一次一档 stroke
  const linkDist = dustLinkDist
  const ld2 = linkDist * linkDist
  const bands = []
  for (let i = 0; i < LINK_BANDS; i++) bands.push(new Path2D())
  const n = dustDots.length
  for (let i = 0; i < n; i++) {
    const a = dustDots[i]
    for (let j = i + 1; j < n; j++) {
      const b = dustDots[j]
      const dx = a.x - b.x
      if (dx > linkDist || dx < -linkDist) continue
      const dy = a.y - b.y
      if (dy > linkDist || dy < -linkDist) continue
      const d2 = dx * dx + dy * dy
      if (d2 > ld2) continue
      const f = a.f < b.f ? a.f : b.f
      if (f < 0.2) continue
      // 越近越亮：t=1 两点重合
      const t = 1 - Math.sqrt(d2) / linkDist
      const band = Math.min(LINK_BANDS - 1, Math.floor(t * LINK_BANDS))
      bands[band].moveTo(a.x, a.y)
      bands[band].lineTo(b.x, b.y)
    }
  }
  ctx.lineWidth = 1
  for (let i = 0; i < LINK_BANDS; i++) {
    const t = (i + 0.5) / LINK_BANDS
    ctx.strokeStyle = `rgba(255,255,255,${(LINK_ALPHA * t).toFixed(3)})`
    ctx.stroke(bands[i])
  }

  // 3) 指针拉线（只有桌面精确指针才有，触屏不会乱闪）
  if (dustPointer.on) {
    const pd2 = POINTER_LINK_DIST * POINTER_LINK_DIST
    const pp = new Path2D()
    let has = false
    for (const d of dustDots) {
      if (d.f < 0.2) continue
      const dx = d.x - dustPointer.x
      const dy = d.y - dustPointer.y
      if (dx * dx + dy * dy > pd2) continue
      pp.moveTo(d.x, d.y)
      pp.lineTo(dustPointer.x, dustPointer.y)
      has = true
    }
    if (has) {
      ctx.strokeStyle = `rgba(255,255,255,${POINTER_LINK_ALPHA})`
      ctx.stroke(pp)
    }
  }

  // 4) 白点本体（点在最后画，压住线头）
  ctx.fillStyle = '#ffffff'
  for (const d of dustDots) {
    if (d.f < 0.2) continue
    ctx.globalAlpha = d.a * d.f
    ctx.beginPath()
    ctx.arc(d.x, d.y, d.r, 0, TAU)
    ctx.fill()
  }
  ctx.globalAlpha = 1
}

function loopDust(ts) {
  paintDust(ts)
  dustRaf = requestAnimationFrame(loopDust)
}

function stopDust() {
  if (dustRaf) cancelAnimationFrame(dustRaf)
  dustRaf = 0
}

function startDust() {
  stopDust()
  dustLast = 0
  if (dustStatic) {
    paintDust(0)              // 减动效：只留一帧静态星座网
    return
  }
  dustRaf = requestAnimationFrame(loopDust)
}

function onDustResize() {
  clearTimeout(dustTimer)
  dustTimer = setTimeout(() => {
    setupDust()
    if (dustStatic) paintDust(0)
  }, 160)
}

function onDustVisibility() {
  if (document.hidden) stopDust()
  else if (!dustStatic) startDust()
}

// 指针位置（转成 canvas 坐标；登录页不滚动，矩形取一次即可）
function onDustPointer(e) {
  const canvas = dustCanvas.value
  if (!canvas) return
  const r = canvas.getBoundingClientRect()
  dustPointer.x = e.clientX - r.left
  dustPointer.y = e.clientY - r.top
  dustPointer.on = true
}

function onDustPointerLeave() {
  dustPointer.on = false
}

onMounted(() => {
  document.body.classList.add('login-route')
  tiltEnabled = window.matchMedia('(pointer: fine)').matches
    && !window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (tiltEnabled) {
    window.addEventListener('pointermove', onTiltMove, { passive: true })
    document.documentElement.addEventListener('pointerleave', onTiltLeave)
  }
  // 纯白粒子星座网
  dustStatic = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  setupDust()
  startDust()
  window.addEventListener('resize', onDustResize)
  document.addEventListener('visibilitychange', onDustVisibility)
  window.addEventListener('pointermove', onDustPointer, { passive: true })
  document.documentElement.addEventListener('pointerleave', onDustPointerLeave)
})

onBeforeUnmount(() => {
  if (tiltRaf) cancelAnimationFrame(tiltRaf)
  if (tiltEnabled) {
    window.removeEventListener('pointermove', onTiltMove)
    document.documentElement.removeEventListener('pointerleave', onTiltLeave)
  }
  stopDust()
  clearTimeout(dustTimer)
  window.removeEventListener('resize', onDustResize)
  document.removeEventListener('visibilitychange', onDustVisibility)
  window.removeEventListener('pointermove', onDustPointer)
  document.documentElement.removeEventListener('pointerleave', onDustPointerLeave)
  document.body.classList.remove('login-route')
})

const router = useRouter()
const auth = useAuthStore()

const route = useRoute()
const loginForm = ref({ email: '', password: '' })
const rememberMe = ref(false)
const registerForm = ref({ email: '', code: '', password: '', confirmPassword: '' })
const isRegistering = ref(false)
const registerStep = ref(1)
const loading = ref(false)
const passwordVisible = ref(false)
const confirmPasswordVisible = ref(false)

const REMEMBER_KEY = 'remember_credentials'

function loadRemembered() {
  try {
    const raw = localStorage.getItem(REMEMBER_KEY)
    if (!raw) return
    const data = JSON.parse(raw)
    if (data && data.email) {
      loginForm.value.email = data.email
      loginForm.value.password = data.password || ''
      rememberMe.value = true
    }
  } catch { /* ignore */ }
}
loadRemembered()

function saveRemembered(email, password) {
  if (rememberMe.value) {
    localStorage.setItem(REMEMBER_KEY, JSON.stringify({ email, password }))
  } else {
    localStorage.removeItem(REMEMBER_KEY)
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
    saveRemembered(loginForm.value.email, loginForm.value.password)
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
  /* 基础深空底；liquid-glass.css（最后加载）会按昼夜主题覆盖成
     「深空三彩晕 / 日间浅灰淡彩」，这里保持同族值避免闪烁 */
  background:
    radial-gradient(56rem 40rem at 14% -8%, rgba(14, 147, 184, .22), transparent 60%),
    radial-gradient(44rem 34rem at 86% 6%, rgba(110, 70, 190, .16), transparent 62%),
    radial-gradient(52rem 40rem at 50% 112%, rgba(201, 160, 107, .14), transparent 60%),
    linear-gradient(180deg, #0b111c 0%, #060a12 100%);
  position: relative;
  overflow: hidden;
}

/* ============ 液态玻璃氛围层（纯 CSS，无 JS） ============ */
.lg-ambient {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}
.lg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(70px);
  opacity: .9;
  will-change: transform;
}
.lg-orb--a {
  width: 46vmax; height: 46vmax; left: -12vmax; top: -16vmax;
  background: radial-gradient(circle at 35% 35%, rgba(20, 168, 208, .62), rgba(14, 147, 184, 0) 68%);
  animation: lg-drift-a 26s ease-in-out infinite alternate;
}
.lg-orb--b {
  width: 40vmax; height: 40vmax; right: -14vmax; top: -8vmax;
  background: radial-gradient(circle at 40% 40%, rgba(124, 82, 210, .52), rgba(110, 70, 190, 0) 68%);
  animation: lg-drift-b 32s ease-in-out infinite alternate;
}
.lg-orb--c {
  width: 44vmax; height: 44vmax; left: 30vw; bottom: -20vmax;
  background: radial-gradient(circle at 50% 40%, rgba(214, 172, 116, .46), rgba(201, 160, 107, 0) 68%);
  animation: lg-drift-c 38s ease-in-out infinite alternate;
}
@keyframes lg-drift-a { to { transform: translate(9vmax, 7vmax) scale(1.12); } }
@keyframes lg-drift-b { to { transform: translate(-8vmax, 9vmax) scale(1.15); } }
@keyframes lg-drift-c { to { transform: translate(6vmax, -8vmax) scale(1.1); } }
/* 透视网格：底部无限滚动，玻璃世界的「地面」 */
.lg-grid {
  position: absolute;
  left: -40%; right: -40%; bottom: -34%; height: 56%;
  background-image:
    linear-gradient(rgba(20, 168, 208, .30) 1px, transparent 1px),
    linear-gradient(90deg, rgba(20, 168, 208, .30) 1px, transparent 1px);
  background-size: 46px 46px;
  transform: perspective(700px) rotateX(64deg);
  transform-origin: center top;
  -webkit-mask-image: linear-gradient(transparent, #000 46%);
  mask-image: linear-gradient(transparent, #000 46%);
  animation: lg-grid-move 3.6s linear infinite;
  opacity: .9;
}
@keyframes lg-grid-move { from { background-position: 0 0; } to { background-position: 0 46px; } }
/* 纯白浮尘粒子层：canvas 铺满氛围层，压在彩晕/网格之上、玻璃卡之下。
   只画白点（无光晕、无连线、无彩色），细节全在脚本里 */
.lg-dust {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  opacity: .85;
}

/* 登录卡片：液态玻璃本体（v2.46.364 方案④）。
   背景描边阴影的最终生效值在 liquid-glass.css（后加载 !important），此处保持同族；
   鼠标视差 transform 由 JS 写入，transition 做平滑 */
.login-card {
  position: relative;
  z-index: 100;
  width: 360px;
  padding: 40px;
  background:
    linear-gradient(160deg, rgba(255, 255, 255, .14), rgba(255, 255, 255, .02) 46%),
    rgba(14, 21, 34, .38);
  -webkit-backdrop-filter: blur(40px) saturate(190%);
  backdrop-filter: blur(40px) saturate(190%);
  border: 1px solid rgba(255, 255, 255, .22);
  border-radius: 26px;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .22),
    0 24px 70px rgba(0, 0, 0, .45),
    0 6px 22px rgba(0, 0, 0, .28);
  will-change: transform;
  transition: transform .18s ease-out;
  opacity: 0;
  animation: card-in 0.5s ease-out 0.15s forwards;
}

@keyframes card-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* 旋转流光光环：藏在玻璃后面的呼吸光晕（雨青→鎏金），透过毛玻璃渗出来 */
.login-card::before {
  content: '';
  position: absolute;
  inset: -26px;
  border-radius: 40px;
  z-index: -1;
  background: conic-gradient(
    from var(--lg-spin, 0deg),
    rgba(14, 147, 184, 0) 0%,
    rgba(14, 147, 184, .55) 18%,
    rgba(201, 160, 107, .45) 30%,
    rgba(14, 147, 184, 0) 46%,
    rgba(110, 70, 190, .30) 66%,
    rgba(14, 147, 184, 0) 88%
  );
  filter: blur(22px);
  opacity: .72;
  animation: lg-ring 9s linear infinite;
  pointer-events: none;
}

@keyframes lg-ring {
  to { --lg-spin: 360deg; }
}

/* 顶部柔光高光（旧霓虹扫描线退役，换液态玻璃的「玻璃沿反光」） */
.login-card::after {
  content: '';
  position: absolute;
  top: 0;
  left: 14%;
  right: 14%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, .65), transparent);
  pointer-events: none;
}

.site-title {
  font-size: 28px;
  text-align: center;
  /* v2.46.260：副标题「神农遗风，云上洞天」已删（夜星：现在没有这块因素了），
     间距由原来「8 + 副标题 + 30」收成这里一手管，标题与表单之间不留空洞 */
  margin-bottom: 22px;
  background: linear-gradient(120deg, #8fdcf2 0%, #f0e6cf 52%, #8fdcf2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 2px 12px rgba(14, 147, 184, .35));
}

.login-form {
  margin-top: 20px;
}

/* 记住我 */
.login-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0 2px;
}
.remember-label {
  display: inline-flex; align-items: center; gap: 8px;
  font-size: 13px; color: rgba(220, 236, 232, 0.85); cursor: pointer;
}
.remember-check {
  width: 16px; height: 16px; accent-color: var(--tc-cyan, #17b0d6);
  cursor: pointer;
}
.remember-hint { font-size: 12px; color: rgba(157, 178, 212, 0.5); }

.password-toggle {
  cursor: pointer;
  color: rgba(220, 236, 232, 0.7);
  display: flex;
  align-items: center;
  transition: color 0.2s;
}

.password-toggle:hover {
  color: var(--tc-cyan, #17b0d6);
}

:deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.09) !important;
  -webkit-backdrop-filter: blur(14px);
  backdrop-filter: blur(14px);
  border: 1px solid rgba(255, 255, 255, 0.28) !important;
  border-radius: 12px !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.10) !important;
  transition: border-color 0.25s ease, box-shadow 0.25s ease;
}

:deep(.el-input__wrapper:hover),
:deep(.el-input__wrapper.is-focus) {
  border-color: rgba(14, 147, 184, 0.85) !important;
  box-shadow: 0 0 0 4px rgba(14, 147, 184, 0.16) !important;
}

:deep(.el-input__inner) {
  color: #eef4fb !important;
  -webkit-text-fill-color: #eef4fb;
  caret-color: #eef4fb;
}

/* 浏览器自动填充（记住我 / 密码管理器）：Chrome 会强制给 input 刷
   浅蓝底 + 自带文字色，普通 CSS 覆盖不了，必须用 inset box-shadow 遮蔽，
   并用 -webkit-text-fill-color 强制文字色 */
:deep(input:-webkit-autofill),
:deep(input:-webkit-autofill:hover),
:deep(input:-webkit-autofill:focus),
:deep(input:-webkit-autofill:active),
:deep(input:autofill),
:deep(input:autofill:hover),
:deep(input:autofill:focus) {
  -webkit-text-fill-color: #eef4fb !important;
  color: #eef4fb !important;
  -webkit-box-shadow: 0 0 0 1000px rgba(14, 21, 34, 0.94) inset !important;
  box-shadow: 0 0 0 1000px rgba(14, 21, 34, 0.94) inset !important;
  background-color: rgba(14, 21, 34, 0.94) !important;
  transition: background-color 9999s ease-out 0s;
  filter: none !important;
  caret-color: #eef4fb;
}
/* 自动填充时同步把外框描边维持雨青 */
:deep(.el-input__wrapper:has(input:-webkit-autofill)),
:deep(.el-input__wrapper:has(input:autofill)) {
  background: rgba(14, 21, 34, 0.94) !important;
  border-color: rgba(14, 147, 184, 0.5) !important;
}

:deep(.el-input__inner::placeholder) {
  color: rgba(210, 224, 240, 0.55) !important;
}

:deep(.el-input__suffix .el-icon),
:deep(.el-input__clear),
:deep(.el-input__password) {
  color: rgba(210, 224, 240, 0.75) !important;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #17b0d6 0%, #0a708c 100%) !important;
  border: none !important;
  color: #ffffff !important;
  box-shadow: 0 8px 22px rgba(14, 147, 184, 0.38) !important;
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #1fbfe4 0%, #0c7d9c 100%) !important;
}

.register-link {
  text-align: center;
  color: rgba(232, 244, 252, 0.78);
  font-size: 13px;
  margin-top: 20px;
  cursor: pointer;
  transition: color 0.2s;
}

.register-link:hover {
  color: var(--tc-cyan, #17b0d6);
}

/* 注册流程 */
.register-flow {
  margin-top: 20px;
}

.step-title {
  font-size: 16px;
  color: #f2f8f6;
  text-align: center;
  margin-bottom: 20px;
}

.back-link {
  text-align: center;
  color: rgba(232, 244, 252, 0.55);
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
  color: rgba(232, 244, 252, 0.62);
  font-size: 14px;
  margin-top: 10px;
}

.success-icon {
  width: 60px;
  height: 60px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, rgba(45, 226, 255, 0.3) 0%, rgba(26, 30, 74, 0.6) 100%);
  border: 2px solid rgba(45, 226, 255, 0.45);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  color: var(--tc-cyan, #17b0d6);
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
  background: radial-gradient(circle, rgba(14, 147, 184, 0.3) 0%, transparent 70%);
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
  border: 1.5px solid rgba(14, 147, 184, 0.45);
  border-radius: 50%;
  border-top-color: rgba(201, 160, 107, 0.85);
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
  background: rgba(10, 16, 26, 0.55);
  -webkit-backdrop-filter: blur(18px) saturate(160%);
  backdrop-filter: blur(18px) saturate(160%);
  border-top: 1px solid rgba(255, 255, 255, 0.12);
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
  color: rgba(232, 244, 252, 0.88);
  text-decoration: none;
  transition: color 0.2s;
  font-weight: 500;
}

.filing-links a:hover {
  color: var(--color-qi-primary);
}

.filing-divider {
  color: rgba(232, 244, 252, 0.55);
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
  .lg-orb,
  .lg-grid,
  .login-card::before {
    animation: none;
  }
}
</style>
