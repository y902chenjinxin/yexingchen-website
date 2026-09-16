<template>
  <div class="cdd-page" :class="{ 'cdd-loaded': loaded }">
    <!-- 全屏背景 -->
    <div
      v-if="item && item.bg_image"
      class="cdd-bg"
      :style="{ backgroundImage: `url(${item.bg_image})` }"
    ></div>
    <div v-else class="cdd-bg cdd-bg-gradient" :style="bgStyle"></div>

    <!-- 背景遮罩 -->
    <div class="cdd-overlay"></div>

    <!-- 顶部操作栏 -->
    <div class="cdd-topbar">
      <button class="cdd-back" @click="router.back()">
        <span class="cdd-back-icon">←</span>
        <span>返回</span>
      </button>
      <div class="cdd-top-actions">
        <el-button size="small" circle :type="item?.in_home ? 'primary' : 'default'" @click="toggleHome" title="首页展示">
          🏠
        </el-button>
        <el-button size="small" circle @click="openEdit" title="编辑">✏️</el-button>
        <el-button size="small" circle type="danger" @click="doDelete" title="删除">🗑️</el-button>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="!loaded" class="cdd-loading">
      <div class="cdd-spinner"></div>
    </div>

    <!-- 主内容 -->
    <div v-else-if="item" class="cdd-content">
      <!-- 图标 -->
      <div class="cdd-icon">{{ item.icon || '📅' }}</div>

      <!-- 标题 -->
      <h1 class="cdd-title">{{ item.title }}</h1>

      <!-- 天数大数字 -->
      <div class="cdd-number-wrap">
        <span class="cdd-prefix">{{ item.direction === 'count_up' ? '已经' : '还有' }}</span>
        <span class="cdd-number" :style="{ color: item.color || 'var(--yq-rain-bright)' }">
          {{ item.days_left }}
        </span>
        <span class="cdd-unit">{{ item.direction === 'count_up' ? '天' : '天' }}</span>
      </div>

      <!-- 标签行 -->
      <div class="cdd-tags">
        <span v-if="item.direction === 'count_up'" class="cdd-tag cdd-up">已过</span>
        <span v-else class="cdd-tag cdd-down">倒计时</span>
        <span v-if="item.repeat_type !== 'none'" class="cdd-tag cdd-repeat">
          🔁 {{ repeatLabel(item.repeat_type) }}
        </span>
        <span v-if="item.pinned" class="cdd-tag cdd-pin">置顶</span>
      </div>

      <!-- 目标日期描述 -->
      <div class="cdd-target">
        <span class="cdd-target-label">目标</span>
        <span class="cdd-target-value">{{ formatTarget(item) }}</span>
      </div>

      <!-- 农历提示 -->
      <div v-if="item.is_lunar" class="cdd-lunar-hint">
        {{ item.lunar_leap ? '（闰月）' : '' }}每年重复
      </div>

      <!-- 备注 -->
      <div v-if="item.memo" class="cdd-memo">{{ item.memo }}</div>

      <!-- 历史记录（count_up 模式） -->
      <div v-if="item.direction === 'count_up' && item.days_left > 0" class="cdd-history">
        <div class="cdd-history-label">去年的今天</div>
        <div class="cdd-history-num">{{ item.days_left - 365 }} 天</div>
      </div>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="editVisible"
      title="编辑倒计时"
      width="480px"
      :close-on-click-modal="false"
      class="cdd-dialog"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px" size="default">
        <el-form-item label="名称" prop="title">
          <el-input v-model="form.title" maxlength="40" />
        </el-form-item>
        <el-form-item label="外观">
          <div style="display:flex;gap:8px">
            <el-input v-model="form.icon" placeholder="emoji" style="width:100px" />
            <el-input v-model="form.color" placeholder="#3db8b0" style="width:120px">
              <template #prepend>
                <div class="cdd-color-swatch" :style="{ background: form.color || '#3db8b0' }"></div>
              </template>
            </el-input>
          </div>
        </el-form-item>
        <el-form-item label="类型" prop="direction">
          <el-radio-group v-model="form.direction">
            <el-radio value="count_down">倒数</el-radio>
            <el-radio value="count_up">正数</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="农历">
          <el-switch v-model="form.is_lunar" @change="onLunarChange" />
        </el-form-item>
        <el-form-item v-if="!form.is_lunar" label="目标日期" prop="target_date">
          <el-date-picker
            v-model="form.target_date"
            type="date"
            value-format="YYYY-MM-DD"
            style="width:100%"
          />
        </el-form-item>
        <template v-if="form.is_lunar">
          <el-form-item label="农历月日">
            <el-select v-model="form.lunar_month" placeholder="月" style="width:48%">
              <el-option v-for="m in 12" :key="m" :label="m+'月'" :value="m" />
            </el-select>
            <el-select v-model="form.lunar_day" placeholder="日" style="width:48%;margin-left:4%">
              <el-option v-for="d in 30" :key="d" :label="d+'日'" :value="d" />
            </el-select>
          </el-form-item>
          <el-form-item label="闰月">
            <el-switch v-model="form.lunar_leap" />
          </el-form-item>
        </template>
        <el-form-item label="重复">
          <el-select v-model="form.repeat_type" style="width:100%">
            <el-option value="none" label="不重复" />
            <el-option value="yearly" label="每年重复" />
            <el-option value="monthly" label="每月重复" />
            <el-option value="weekly" label="每周重复" />
          </el-select>
        </el-form-item>
        <el-form-item label="背景图">
          <div style="display:flex;align-items:center;gap:10px">
            <el-upload :auto-upload="false" :show-file-list="false" accept="image/*" :on-change="onBgChange">
              <el-button size="small" plain>更换背景</el-button>
            </el-upload>
            <img v-if="bgPreview" :src="bgPreview" style="width:60px;height:40px;object-fit:cover;border-radius:6px;" />
            <el-button v-if="form.bg_image || bgPreview" size="small" type="danger" plain @click="clearBg">移除</el-button>
          </div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.memo" type="textarea" :rows="2" maxlength="200" />
        </el-form-item>
        <el-form-item label="展示">
          <el-checkbox v-model="form.in_home">首页展示</el-checkbox>
          <el-checkbox v-model="form.pinned">置顶</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="doSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCountdown, updateCountdown, deleteCountdown, uploadImage } from '@/api/countdown'

const route = useRoute()
const router = useRouter()

const item = ref(null)
const loaded = ref(false)
const editVisible = ref(false)
const saving = ref(false)
const formRef = ref()
const bgPreview = ref('')
const bgFile = ref(null)

const defaultForm = () => ({
  title: '', target_date: '', is_lunar: false,
  lunar_month: null, lunar_day: null, lunar_leap: false,
  direction: 'count_down', repeat_type: 'none',
  in_home: false, pinned: false, icon: '',
  color: '#3db8b0', bg_image: '', memo: '',
})
const form = ref(defaultForm())

const rules = {
  title: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  direction: [{ required: true, message: '请选择类型', trigger: 'change' }],
  target_date: [{ required: true, message: '请选择目标日期', trigger: 'change' }],
}

// 背景渐变
const bgStyle = computed(() => {
  const c = item.value?.color || '#3db8b0'
  return {
    background: `linear-gradient(135deg, ${c}30 0%, ${c}18 50%, rgba(0,0,0,0.6) 100%)`,
  }
})

// 格式化目标日期
function formatTarget(i) {
  if (i.is_lunar) {
    return `农历${i.lunar_leap ? '（闰）' : ''}${i.lunar_month}月${i.lunar_day}日`
  }
  return i.target_date || ''
}

function repeatLabel(r) {
  const map = { none: '无', yearly: '每年', monthly: '每月', weekly: '每周' }
  return map[r] || r
}

async function load() {
  loaded.value = false
  try {
    const { data } = await getCountdown(route.params.id)
    item.value = data
  } catch {
    ElMessage.error('加载失败')
    router.back()
  } finally {
    loaded.value = true
  }
}

async function toggleHome() {
  await updateCountdown(item.value.id, { in_home: !item.value.in_home })
  item.value.in_home = !item.value.in_home
  ElMessage.success(item.value.in_home ? '已加入首页' : '已从首页移除')
}

function openEdit() {
  const i = item.value
  form.value = {
    title: i.title, target_date: i.target_date,
    is_lunar: i.is_lunar, lunar_month: i.lunar_month, lunar_day: i.lunar_day,
    lunar_leap: i.lunar_leap, direction: i.direction,
    repeat_type: i.repeat_type, in_home: i.in_home, pinned: i.pinned,
    icon: i.icon || '', color: i.color || '#3db8b0',
    bg_image: i.bg_image || '', memo: i.memo || '',
  }
  bgPreview.value = i.bg_image || ''
  bgFile.value = null
  editVisible.value = true
}

function onLunarChange() {
  form.value.target_date = ''
}

function onBgChange({ raw }) {
  bgFile.value = raw
  bgPreview.value = URL.createObjectURL(raw)
}

function clearBg() {
  bgFile.value = null
  bgPreview.value = ''
  form.value.bg_image = ''
}

async function doSave() {
  try { await formRef.value.validate() } catch { return }
  saving.value = true
  try {
    let bg_image = form.value.bg_image
    if (bgFile.value) {
      const { data } = await uploadImage(bgFile.value)
      bg_image = data.url
    }
    const payload = { ...form.value, bg_image }
    if (form.value.is_lunar) delete payload.target_date
    await updateCountdown(item.value.id, payload)
    ElMessage.success('已更新')
    editVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function doDelete() {
  await ElMessageBox.confirm('确认删除？', '删除确认', {
    confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
  })
  await deleteCountdown(item.value.id)
  ElMessage.success('已删除')
  router.push('/tool/countdown')
}

onMounted(load)
</script>

<style scoped>
.cdd-page {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  opacity: 0;
  transition: opacity 0.4s ease;
}
.cdd-loaded {
  opacity: 1;
}

/* 背景 */
.cdd-bg {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  transition: transform 8s ease;
}
.cdd-page:hover .cdd-bg {
  transform: scale(1.03);
}
.cdd-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to bottom,
    rgba(0,0,0,0.3) 0%,
    rgba(0,0,0,0.2) 40%,
    rgba(0,0,0,0.6) 100%
  );
}

/* 顶栏 */
.cdd-topbar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
}
.cdd-back {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(0,0,0,0.35);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 20px;
  padding: 6px 14px 6px 10px;
  color: rgba(255,255,255,0.85);
  font-size: 14px;
  cursor: pointer;
  backdrop-filter: blur(12px);
  transition: background 0.2s;
}
.cdd-back:hover {
  background: rgba(0,0,0,0.55);
}
.cdd-back-icon {
  font-size: 16px;
}
.cdd-top-actions {
  display: flex;
  gap: 8px;
}

/* 加载 */
.cdd-loading {
  position: relative;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: center;
}
.cdd-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(255,255,255,0.15);
  border-top-color: var(--yq-rain-bright);
  border-radius: 50%;
  animation: cdd-spin 0.8s linear infinite;
}
@keyframes cdd-spin {
  to { transform: rotate(360deg); }
}

/* 主内容 */
.cdd-content {
  position: relative;
  z-index: 5;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 0 20px;
  animation: cdd-enter 0.6s cubic-bezier(0.22, 1, 0.36, 1) both;
}
@keyframes cdd-enter {
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: translateY(0); }
}

.cdd-icon {
  font-size: 48px;
  margin-bottom: 12px;
  filter: drop-shadow(0 4px 12px rgba(0,0,0,0.3));
}
.cdd-title {
  font-size: 22px;
  font-weight: 600;
  color: rgba(255,255,255,0.92);
  margin: 0 0 24px;
  text-shadow: 0 2px 8px rgba(0,0,0,0.4);
  font-family: var(--font-serif);
  letter-spacing: 0.04em;
}

/* 天数大数字 */
.cdd-number-wrap {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 20px;
}
.cdd-prefix {
  font-size: 20px;
  color: rgba(255,255,255,0.65);
  font-family: var(--font-serif);
}
.cdd-number {
  font-size: clamp(72px, 18vw, 128px);
  font-weight: 800;
  line-height: 1;
  text-shadow: 0 4px 24px rgba(0,0,0,0.4), 0 0 40px currentColor;
  font-family: var(--font-serif);
  transition: font-size 0.3s;
}
.cdd-unit {
  font-size: 28px;
  color: rgba(255,255,255,0.7);
  font-family: var(--font-serif);
}

/* 标签 */
.cdd-tags {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  flex-wrap: wrap;
  justify-content: center;
}
.cdd-tag {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 20px;
  backdrop-filter: blur(8px);
  font-weight: 500;
}
.cdd-down { background: rgba(61,184,176,0.25); color: #a8d3ce; border: 1px solid rgba(61,184,176,0.3); }
.cdd-up { background: rgba(199,169,107,0.25); color: #e4d9bd; border: 1px solid rgba(199,169,107,0.3); }
.cdd-repeat { background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.75); border: 1px solid rgba(255,255,255,0.2); }
.cdd-pin { background: rgba(199,169,107,0.25); color: var(--yq-gold); border: 1px solid rgba(199,169,107,0.3); }

/* 目标日期 */
.cdd-target {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(255,255,255,0.08);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 12px;
  padding: 8px 20px;
  margin-bottom: 12px;
}
.cdd-target-label {
  font-size: 12px;
  color: rgba(255,255,255,0.5);
}
.cdd-target-value {
  font-size: 15px;
  color: rgba(255,255,255,0.9);
  font-family: var(--font-serif);
}
.cdd-lunar-hint {
  font-size: 12px;
  color: rgba(255,255,255,0.45);
  margin-bottom: 12px;
}

/* 备注 */
.cdd-memo {
  font-size: 13px;
  color: rgba(255,255,255,0.55);
  max-width: 360px;
  line-height: 1.6;
  margin-top: 8px;
}

/* 历史 */
.cdd-history {
  margin-top: 32px;
  background: rgba(255,255,255,0.06);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  padding: 12px 24px;
  text-align: center;
}
.cdd-history-label {
  font-size: 12px;
  color: rgba(255,255,255,0.45);
  margin-bottom: 4px;
}
.cdd-history-num {
  font-size: 18px;
  color: rgba(255,255,255,0.7);
  font-family: var(--font-serif);
}

/* 编辑对话框 */
.cdd-color-swatch {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  flex-shrink: 0;
}
</style>
