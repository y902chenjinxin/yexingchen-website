<template>
  <div class="profile-page">
    <div class="page-header">
      <div class="header-with-back">
        <BackButton fallback="/workbench" style="margin-right: 12px;" />
        <h1 class="page-title font-serif">个人中心</h1>
      </div>
    </div>

    <div class="profile-content">
      <!-- 个人信息卡片 -->
      <div class="info-card">
        <div class="card-header">
          <h2>基本信息</h2>
        </div>
        <div class="card-body">
          <div class="info-item">
            <span class="info-label">邮箱</span>
            <span class="info-value">{{ userInfo.email }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">昵称</span>
            <span class="info-value">{{ userInfo.nickname || '未设置' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">角色</span>
            <span class="info-value role-tag" :class="userInfo.role">{{ getRoleLabel(userInfo.role) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">注册时间</span>
            <span class="info-value">{{ formatDate(userInfo.created_at) }}</span>
          </div>
        </div>
        <div class="card-footer">
          <el-button type="primary" @click="showEditDialog = true">编辑信息</el-button>
          <el-button @click="showPasswordDialog = true">修改密码</el-button>
        </div>
      </div>

      <!-- 界面偏好 -->
      <div class="info-card">
        <div class="card-header">
          <h2>界面偏好</h2>
        </div>
        <div class="card-body">
          <div class="info-item">
            <div class="pref-text">
              <span class="info-label">主题外观</span>
              <span class="pref-hint">白天 / 夜间固定外观，或自动跟随时间切换</span>
            </div>
            <div class="theme-seg" role="tablist" aria-label="主题外观">
              <button
                v-for="opt in themeOptions"
                :key="opt.value"
                class="theme-seg-btn"
                :class="{ active: themeOverride === opt.value }"
                role="tab"
                :aria-selected="themeOverride === opt.value"
                @click="prefs.setTheme(opt.value)"
              >{{ opt.label }}</button>
            </div>
          </div>

          <!-- 桌宠展示 -->
          <div class="info-item">
            <div class="pref-text">
              <span class="info-label">桌宠展示</span>
              <span class="pref-hint">关闭后全站不再出现右下角的鲸鱼；设置只对当前账号生效</span>
            </div>
            <el-switch
              v-model="petVisible"
              class="pref-switch"
              inline-prompt
              active-text="显示"
              inactive-text="隐藏"
              aria-label="桌宠展示开关"
            />
          </div>

          <!-- 安装到主屏幕（PWA）：仅在可安装/需手动引导时出现，已安装则整块隐藏 -->
          <div v-if="showInstallRow" class="info-item">
            <div class="pref-text">
              <span class="info-label">安装为应用</span>
              <span class="pref-hint">{{ iosGuide
                ? 'iPhone/iPad：点浏览器底部「分享」按钮，选择「添加到主屏幕」'
                : '安装到桌面 / 主屏幕，像原生应用一样全屏打开' }}</span>
            </div>
            <el-button
              v-if="!iosGuide"
              size="small" type="primary" plain
              :disabled="!canPrompt"
              @click="doInstall"
            >安装</el-button>
          </div>
        </div>
      </div>

      <!-- 品牌意象 -->
      <div class="info-card">
        <div class="card-header">
          <h2>玄黄 · 意象</h2>
        </div>
        <div class="card-body">
          <p class="pref-hint brand-tip">三款玄黄意象标识：<b>琉璃 · 月光</b>为本应用 2.1.0 正式图标，曜变 / 玄黄为同期设计的蔚蓝备选。</p>
          <div class="brand-grid">
            <figure v-for="it in brandIcons" :key="it.tag" class="brand-cell" :class="{ current: it.tag === 'liuli' }">
              <span class="brand-stage"><img :src="it.src" :alt="it.name" loading="lazy" /></span>
              <figcaption>{{ it.name }}<em v-if="it.tag === 'liuli'">当前图标</em></figcaption>
            </figure>
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑信息对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑个人信息" width="400px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="昵称">
          <el-input v-model="editForm.nickname" placeholder="请输入昵称" maxlength="50" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveProfile">保存</el-button>
      </template>
    </el-dialog>

    <!-- 修改密码对话框 -->
    <el-dialog v-model="showPasswordDialog" title="修改密码" width="400px">
      <el-form :model="passwordForm" label-width="100px">
        <el-form-item label="当前密码">
          <el-input v-model="passwordForm.oldPassword" type="password" show-password placeholder="请输入当前密码" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="passwordForm.newPassword" type="password" show-password placeholder="请输入新密码" />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="passwordForm.confirmPassword" type="password" show-password placeholder="请再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPasswordDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePassword">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
defineOptions({ name: 'ProfileView' })
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import BackButton from '@/components/BackButton.vue'
import { useAuthStore } from '@/stores/auth'
import { usePrefsStore } from '@/stores/prefs'
import { usePwaInstall } from '@/composables/usePwaInstall'
import { getMe, updateMe } from '@/api/auth'
import iconLiuli from '@/assets/brand/icon-liuli.png'
import iconYaobian from '@/assets/brand/icon-yaobian.png'
import iconXuanhuang from '@/assets/brand/icon-xuanhuang.png'

const brandIcons = [
  { tag: 'yaobian', name: '曜变', src: iconYaobian },
  { tag: 'liuli', name: '琉璃 · 月光', src: iconLiuli },
  { tag: 'xuanhuang', name: '玄黄 · 辉光', src: iconXuanhuang },
]

const router = useRouter()
const auth = useAuthStore()
const prefs = usePrefsStore()

// PWA 安装：Chromium 可直接弹原生安装框；iOS 只能文字引导「分享 → 添加到主屏幕」
const {
  canInstall, showIosGuide, promptInstall, installed,
} = usePwaInstall()
const iosGuide = showIosGuide
const canPrompt = canInstall
const showInstallRow = computed(() => !installed.value && (canInstall.value || showIosGuide.value))

async function doInstall() {
  const outcome = await promptInstall()
  if (outcome === 'accepted') ElMessage.success('安装成功，可从桌面 / 主屏幕打开')
}

// 桌宠开关：直接读写偏好 store，App.vue 里的 showWhale 会立即响应（无需刷新）
const petVisible = computed({
  get: () => prefs.petVisible,
  set: (v) => prefs.setPetVisible(v),
})

// 主题外观
const themeOverride = computed(() => prefs.themeOverride)
const themeOptions = [
  { value: 'auto', label: '自动' },
  { value: 'day', label: '白天' },
  { value: 'night', label: '夜间' },
]

// 用户信息
const userInfo = ref({
  email: '',
  nickname: '',
  role: '',
  is_super_admin: 0,
  created_at: ''
})

// 编辑对话框
const showEditDialog = ref(false)
const editForm = ref({ nickname: '' })
const saving = ref(false)

// 密码对话框
const showPasswordDialog = ref(false)
const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

onMounted(() => {
  fetchUserInfo()
})

async function fetchUserInfo() {
  try {
    const res = await getMe()
    if (res.data) {
      userInfo.value = res.data
      // 从昵称中解析头像（如果有的话）
      // 暂时用默认
    }
  } catch (e) {
    ElMessage.error('获取用户信息失败')
  }
}

function getRoleLabel(role) {
  const map = {
    'super_admin': '超级管理员',
    'admin': '管理员',
    'user': '普通用户'
  }
  return map[role] || role
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

async function saveProfile() {
  if (!editForm.value.nickname.trim()) {
    ElMessage.warning('请输入昵称')
    return
  }
  saving.value = true
  try {
    await updateMe({ nickname: editForm.value.nickname })
    userInfo.value.nickname = editForm.value.nickname
    showEditDialog.value = false
    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function savePassword() {
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
  saving.value = true
  try {
    await auth.changePassword(passwordForm.value.oldPassword, passwordForm.value.newPassword)
    ElMessage.success('密码修改成功')
    showPasswordDialog.value = false
    passwordForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
  } catch (e) {
    ElMessage.error('修改失败，请检查当前密码是否正确')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  background: var(--color-bg);
  /* 顶部 84px 避让全局固定顶栏（60px + 留白），否则页头返回按钮被顶栏盖住 */
  padding: 84px 40px 40px;
  font-family: var(--font-serif);
}

.page-header {
  max-width: 800px;
  margin: 0 auto 30px;
}

.page-title {
  font-size: 32px;
  font-weight: 600;
  letter-spacing: .1em;
  text-align: center;
  background: linear-gradient(135deg, #c9a96e 0%, #f0e6c8 48%, #c9a96e 100%);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 2px 8px rgba(201,169,110,.18));
}

.profile-content {
  max-width: 800px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
}

.info-card {
  position: relative;
  background: var(--xiu-card);
  backdrop-filter: blur(14px);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, .32), inset 0 1px 0 rgba(255, 255, 255, .04);
  border: 1px solid var(--xiu-line);
}
.info-card::before { content: ""; position: absolute; top: 0; left: 18%; right: 18%; height: 1px; background: linear-gradient(90deg, transparent, var(--xiu-gold), transparent); opacity: .5; }

.card-header {
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid rgba(201, 169, 108, 0.2);
}

.card-header h2 {
  font-size: 18px;
  color: var(--color-text);
  font-weight: 600;
}

.card-body {
  margin-bottom: 20px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid rgba(201, 169, 108, 0.1);
}

.info-item:last-child {
  border-bottom: none;
}

.info-label {
  color: var(--color-text-secondary);
  font-size: 14px;
}

.info-value {
  color: var(--color-text);
  font-size: 14px;
}

.role-tag {
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
}

.role-tag.super_admin {
  background: rgba(201, 169, 110, 0.2);
  color: var(--color-gold);
}

.role-tag.admin {
  background: rgba(139, 122, 174, 0.2);
  color: var(--color-purple-light);
}

.role-tag.user {
  background: rgba(154, 150, 142, 0.2);
  color: var(--color-text-secondary);
}

.card-footer {
  display: flex;
  gap: 12px;
}

.card-footer .el-button {
  flex: 1;
}

/* 界面偏好 */
.pref-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-right: 16px;
}

.pref-hint {
  font-size: 12px;
  color: var(--color-text-secondary);
  opacity: .8;
  line-height: 1.5;
}

.pref-switch {
  flex: none;
}

/* 主题外观分段控件 */
.theme-seg {
  display: inline-flex;
  padding: 3px;
  border-radius: 999px;
  background: rgba(127, 168, 163, 0.12);
  border: 1px solid rgba(127, 168, 163, 0.22);
  flex: none;
}
.theme-seg-btn {
  padding: 6px 14px;
  border: none;
  border-radius: 999px;
  font-size: 12.5px;
  color: var(--color-text-secondary);
  background: transparent;
  cursor: pointer;
  transition: all 0.22s ease;
  -webkit-tap-highlight-color: transparent;
}
.theme-seg-btn.active {
  color: #fff;
  background: linear-gradient(135deg, var(--color-gold), #b8894a);
  box-shadow: 0 4px 12px rgba(201, 169, 107, 0.35);
}
.theme-seg-btn:focus-visible { outline: var(--focus-outline); outline-offset: 2px; }

.header-with-back {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

/* 品牌意象 */
.brand-tip { margin-bottom: 16px; }
.brand-tip b { color: var(--color-gold); font-weight: 600; }

.brand-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.brand-cell { margin: 0; text-align: center; }
.brand-stage {
  display: block;
  aspect-ratio: 1 / 1;
  border-radius: 22%;
  padding: 10px;
  background:
    radial-gradient(120% 120% at 30% 20%, rgba(201, 169, 110, .14), transparent 55%),
    var(--xiu-card-2, rgba(201, 169, 110, .06));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .05), 0 8px 22px rgba(0, 0, 0, .18);
  border: 1px solid var(--xiu-line);
}
.brand-stage img {
  width: 100%; height: 100%;
  object-fit: contain;
  display: block;
}
.brand-cell.current .brand-stage {
  border-color: rgba(201, 169, 110, .55);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .08), 0 0 0 1px rgba(201, 169, 110, .25), 0 10px 26px rgba(201, 169, 110, .16);
}
.brand-cell figcaption {
  margin-top: 10px;
  font-size: 12.5px;
  color: var(--color-text-secondary);
  line-height: 1.4;
}
.brand-cell figcaption em {
  display: block;
  font-style: normal;
  font-size: 11px;
  color: var(--color-gold);
  margin-top: 2px;
  letter-spacing: .05em;
}

@media (max-width: 520px) {
  .brand-grid { gap: 10px; }
  .brand-stage { border-radius: 20%; padding: 8px; }
  .brand-cell figcaption { font-size: 11.5px; }
}
</style>