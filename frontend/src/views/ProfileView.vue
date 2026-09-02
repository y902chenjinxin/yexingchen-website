<template>
  <div class="profile-page">
    <div class="page-header">
      <div class="header-with-back">
        <span class="back-btn" @click="router.push('/home')">← 返回主页</span>
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

      <!-- 头像选择 -->
      <div class="avatar-card">
        <div class="card-header">
          <h2>头像设置</h2>
        </div>
        <div class="card-body">
          <div class="current-avatar">
            <span class="avatar-emoji">{{ currentAvatarEmoji }}</span>
          </div>
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
        </div>
        <div class="card-footer">
          <el-button type="primary" :disabled="selectedAvatar === currentAvatarId" @click="saveAvatar">保存头像</el-button>
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import BackButton from '@/components/BackButton.vue'
import { useAuthStore } from '@/stores/auth'
import { getMe, updateMe } from '@/api/auth'

const router = useRouter()
const auth = useAuthStore()

// 用户信息
const userInfo = ref({
  email: '',
  nickname: '',
  role: '',
  is_super_admin: 0,
  created_at: ''
})

// 头像相关
const avatarOptions = [
  { id: 1, emoji: '🌙' },
  { id: 2, emoji: '☁️' },
  { id: 3, emoji: '⭐' },
  { id: 4, emoji: '🌸' }
]
const currentAvatarId = ref(1)
const selectedAvatar = ref(1)

const currentAvatarEmoji = computed(() => {
  const av = avatarOptions.find(a => a.id === currentAvatarId.value)
  return av?.emoji || '🌙'
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

async function saveAvatar() {
  saving.value = true
  try {
    await updateMe({ avatar_id: selectedAvatar.value })
    currentAvatarId.value = selectedAvatar.value
    ElMessage.success('头像已更新')
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
    // TODO: 调用修改密码API
    ElMessage.success('密码修改成功')
    showPasswordDialog.value = false
    passwordForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
  } catch (e) {
    ElMessage.error('修改失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  background: var(--color-bg);
  padding: 40px;
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
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.info-card, .avatar-card {
  position: relative;
  background: var(--xiu-card);
  backdrop-filter: blur(14px);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, .32), inset 0 1px 0 rgba(255, 255, 255, .04);
  border: 1px solid var(--xiu-line);
}
.info-card::before, .avatar-card::before { content: ""; position: absolute; top: 0; left: 18%; right: 18%; height: 1px; background: linear-gradient(90deg, transparent, var(--xiu-gold), transparent); opacity: .5; }

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

.current-avatar {
  text-align: center;
  margin-bottom: 20px;
}

.current-avatar .avatar-emoji {
  font-size: 64px;
}

.avatar-options {
  display: flex;
  justify-content: center;
  gap: 16px;
}

.avatar-option {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: rgba(201, 169, 108, 0.1);
  border: 2px solid rgba(201, 169, 108, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.avatar-option:hover {
  border-color: rgba(201, 169, 108, 0.5);
}

.avatar-option.selected {
  border-color: var(--color-gold);
  background: rgba(201, 169, 110, 0.2);
  box-shadow: 0 0 15px rgba(201, 169, 110, 0.3);
}

.avatar-option .avatar-emoji {
  font-size: 28px;
}

.header-with-back {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.back-btn {
  color: var(--color-gold);
  cursor: pointer;
  font-size: 14px;
  align-self: flex-start;
  margin-left: 20px;
}

.back-btn:hover {
  color: var(--color-gold-light);
}
</style>