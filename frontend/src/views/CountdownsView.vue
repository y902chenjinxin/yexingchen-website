<template>
  <IslandInnerBase type="tool" title="倒计时" subtitle="记录每一个值得期待的日子">
    <template #toolbar>
      <el-button size="small" plain @click="showArchived = !showArchived">
        {{ showArchived ? '隐藏归档' : '显示归档' }}
      </el-button>
      <el-button type="primary" size="small" @click="openDialog()">新建倒计时</el-button>
    </template>

    <!-- 空状态 -->
    <div v-if="!loading && items.length === 0" class="cd-empty">
      <span class="cd-empty-icon">⏳</span>
      <span class="cd-empty-text">还没有倒计时事件</span>
      <el-button type="primary" size="small" @click="openDialog()">新建第一个</el-button>
    </div>

    <!-- 列表 -->
    <div v-else class="cd-grid">
      <!-- 归档分组 -->
      <template v-for="group in groups" :key="group.label">
        <div v-if="group.items.length > 0" class="cd-group">
          <div class="cd-group-label">{{ group.label }}</div>
          <div class="cd-cards">
            <div
              v-for="item in group.items"
              :key="item.id"
              class="cd-card jade-card"
              :class="{ 'cd-pinned': item.pinned }"
              @click="goDetail(item)"
            >
              <!-- 背景图 -->
              <div
                v-if="item.bg_image"
                class="cd-card-bg"
                :style="{ backgroundImage: `url(${item.bg_image})` }"
              ></div>
              <div v-else class="cd-card-bg" :style="{ background: bgGradient(item.color) }"></div>

              <!-- 玉简箔面效果 -->
              <div class="cd-card-foil"></div>

              <!-- 内容 -->
              <div class="cd-card-body">
                <div class="cd-card-top">
                  <span class="cd-icon">{{ item.icon || '📅' }}</span>
                  <span class="cd-days" :style="{ color: item.color || 'var(--xiu-primary)' }">
                    {{ item.days_left }}
                  </span>
                </div>
                <div class="cd-card-title">{{ item.title }}</div>
                <div class="cd-card-date">
                  {{ formatTarget(item) }}
                </div>
                <div class="cd-card-meta">
                  <span v-if="item.direction === 'count_up'" class="cd-tag cd-up">已过</span>
                  <span v-else class="cd-tag cd-down">还剩</span>
                  <span v-if="item.pinned" class="cd-tag cd-pin">置顶</span>
                  <span v-if="item.is_archived" class="cd-tag cd-arch">归档</span>
                </div>
              </div>

              <!-- 操作按钮 -->
              <div class="cd-card-actions" @click.stop>
                <el-button
                  size="small"
                  circle
                  :type="item.in_home ? 'primary' : 'default'"
                  :title="item.in_home ? '取消首页展示' : '首页展示'"
                  @click.stop="toggleHome(item)"
                >
                  🏠
                </el-button>
                <el-button size="small" circle title="编辑" @click.stop="openDialog(item)">
                  ✏️
                </el-button>
                <el-button size="small" circle type="danger" title="删除" @click.stop="doDelete(item)">
                  🗑️
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- 新建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editing ? '编辑倒计时' : '新建倒计时'"
      width="480px"
      :close-on-click-modal="false"
      class="cd-dialog"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px" size="default">
        <!-- 标题 -->
        <el-form-item label="名称" prop="title">
          <el-input v-model="form.title" maxlength="40" placeholder="如：结婚纪念日" />
        </el-form-item>

        <!-- 图标/颜色 -->
        <el-form-item label="外观">
          <div class="cd-look-row">
            <div class="cd-look-fields">
              <el-input v-model="form.icon" placeholder="emoji 或图标名" style="width:100px" />
              <el-input
                v-model="form.color"
                placeholder="#3db8b0"
                style="width:120px"
                maxlength="10"
              >
                <template #prepend>
                  <div
                    class="cd-color-swatch"
                    :style="{ background: form.color || '#3db8b0' }"
                  ></div>
                </template>
              </el-input>
            </div>
          </div>
        </el-form-item>

        <!-- 方向 -->
        <el-form-item label="类型" prop="direction">
          <el-radio-group v-model="form.direction">
            <el-radio value="count_down">倒数（还剩 N 天）</el-radio>
            <el-radio value="count_up">正数（已过 N 天）</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 农历开关 -->
        <el-form-item label="农历">
          <el-switch v-model="form.is_lunar" @change="onLunarChange" />
        </el-form-item>

        <!-- 公历日期 -->
        <el-form-item v-if="!form.is_lunar" label="目标日期" prop="target_date">
          <el-date-picker
            v-model="form.target_date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>

        <!-- 农历月日 -->
        <template v-if="form.is_lunar">
          <el-form-item label="农历月" prop="lunar_month">
            <el-select v-model="form.lunar_month" placeholder="选择农历月" style="width:48%">
              <el-option v-for="m in 12" :key="m" :label="m + ' 月'" :value="m" />
            </el-select>
            <el-select
              v-model="form.lunar_day"
              placeholder="选择农历日"
              style="width:48%; margin-left:4%"
            >
              <el-option v-for="d in 30" :key="d" :label="d + ' 日'" :value="d" />
            </el-select>
          </el-form-item>
          <el-form-item label="闰月">
            <el-switch v-model="form.lunar_leap" />
          </el-form-item>
        </template>

        <!-- 重复 -->
        <el-form-item label="重复">
          <el-select v-model="form.repeat_type" style="width:100%">
            <el-option value="none" label="不重复" />
            <el-option value="yearly" label="每年重复" />
            <el-option value="monthly" label="每月重复" />
            <el-option value="weekly" label="每周重复" />
          </el-select>
        </el-form-item>

        <!-- 背景图 -->
        <el-form-item label="背景图">
          <div class="cd-bg-upload">
            <el-upload
              :auto-upload="false"
              :show-file-list="false"
              accept="image/*"
              :on-change="onBgChange"
            >
              <el-button size="small" plain>选择图片</el-button>
            </el-upload>
            <img v-if="bgPreview" :src="bgPreview" class="cd-bg-thumb" />
            <el-button
              v-if="form.bg_image || bgPreview"
              size="small"
              type="danger"
              plain
              @click="clearBg"
            >移除</el-button>
          </div>
        </el-form-item>

        <!-- 备注 -->
        <el-form-item label="备注">
          <el-input
            v-model="form.memo"
            type="textarea"
            :rows="2"
            maxlength="200"
            placeholder="可选备注"
          />
        </el-form-item>

        <!-- 展示选项 -->
        <el-form-item label="展示">
          <el-checkbox v-model="form.in_home">首页玉简卡片展示</el-checkbox>
          <el-checkbox v-model="form.pinned">置顶</el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="doSave">保存</el-button>
      </template>
    </el-dialog>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import {
  listCountdowns,
  createCountdown,
  updateCountdown,
  deleteCountdown,
  uploadImage,
} from '@/api/countdown'

const router = useRouter()

// 数据
const items = ref([])
const loading = ref(true)
const showArchived = ref(false)
const dialogVisible = ref(false)
const editing = ref(null)
const saving = ref(false)
const formRef = ref()
const bgPreview = ref('')
const bgFile = ref(null)

// 默认表单
const defaultForm = () => ({
  title: '',
  target_date: '',
  is_lunar: false,
  lunar_month: null,
  lunar_day: null,
  lunar_leap: false,
  direction: 'count_down',
  repeat_type: 'none',
  in_home: false,
  pinned: false,
  icon: '',
  color: '#3db8b0',
  bg_image: '',
  memo: '',
})

const form = ref(defaultForm())

const rules = {
  title: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  direction: [{ required: true, message: '请选择类型', trigger: 'change' }],
  target_date: [{ required: true, message: '请选择目标日期', trigger: 'change' }],
}

// 分组：活跃 / 归档
const groups = computed(() => {
  const active = items.value.filter((i) => !i.is_archived)
  const archived = items.value.filter((i) => i.is_archived)

  return [
    { label: '当前', items: active },
    { label: '归档', items: showArchived.value ? archived : [] },
  ].filter((g) => g.items.length > 0)
})

// 背景渐变（无图片时的默认背景）
function bgGradient(color) {
  const c = color || '#3db8b0'
  return `linear-gradient(135deg, ${c}22 0%, ${c}44 100%)`
}

// 格式化目标日期
function formatTarget(item) {
  if (item.is_lunar) {
    const leap = item.lunar_leap ? '（闰）' : ''
    return `农历${leap}${item.lunar_month}月${item.lunar_day}日`
  }
  if (!item.target_date) return ''
  return item.target_date
}

// 加载数据
async function load() {
  loading.value = true
  try {
    const { data: resp } = await listCountdowns({ includeArchived: true })
    items.value = resp.data?.list || resp.list || []
  } catch {
    ElMessage.error('加载倒计时失败')
  } finally {
    loading.value = false
  }
}

// 打开对话框
function openDialog(item = null) {
  editing.value = item
  if (item) {
    form.value = {
      title: item.title || '',
      target_date: item.target_date || '',
      is_lunar: item.is_lunar || false,
      lunar_month: item.lunar_month || null,
      lunar_day: item.lunar_day || null,
      lunar_leap: item.lunar_leap || false,
      direction: item.direction || 'count_down',
      repeat_type: item.repeat_type || 'none',
      in_home: item.in_home || false,
      pinned: item.pinned || false,
      icon: item.icon || '',
      color: item.color || '#3db8b0',
      bg_image: item.bg_image || '',
      memo: item.memo || '',
    }
    bgPreview.value = item.bg_image || ''
  } else {
    form.value = defaultForm()
    bgPreview.value = ''
    bgFile.value = null
  }
  dialogVisible.value = true
}

// 农历切换清空公历日期
function onLunarChange() {
  form.value.target_date = ''
}

// 背景图选择
function onBgChange({ raw }) {
  bgFile.value = raw
  bgPreview.value = URL.createObjectURL(raw)
}

function clearBg() {
  bgFile.value = null
  bgPreview.value = ''
  form.value.bg_image = ''
}

// 保存
async function doSave() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    let bg_image = form.value.bg_image

    // 上传背景图
    if (bgFile.value) {
      const { data } = await uploadImage(bgFile.value)
      bg_image = data.url
    }

    const payload = { ...form.value, bg_image }

    // 农历模式下不传 target_date
    if (form.value.is_lunar) {
      delete payload.target_date
    }

    if (editing.value) {
      await updateCountdown(editing.value.id, payload)
      ElMessage.success('已更新')
    } else {
      await createCountdown(payload)
      ElMessage.success('已创建')
    }

    dialogVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

// 删除
async function doDelete(item) {
  await ElMessageBox.confirm(`确认删除「${item.title}」？`, '删除确认', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
  })
  await deleteCountdown(item.id)
  ElMessage.success('已删除')
  await load()
}

// 首页展示切换
async function toggleHome(item) {
  await updateCountdown(item.id, { in_home: !item.in_home })
  await load()
}

// 跳转详情
function goDetail(item) {
  router.push(`/tool/countdown/${item.id}`)
}
function goDetail(item) {
  router.push(`/tool/countdown/${item.id}`)
}

onMounted(load)
</script>

<style scoped>
/* 空状态 */
.cd-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 80px 0;
  color: var(--xiu-text-3);
}
.cd-empty-icon {
  font-size: 48px;
  opacity: 0.5;
}
.cd-empty-text {
  font-size: 15px;
}

/* 列表网格 */
.cd-grid {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.cd-group-label {
  font-size: 13px;
  color: var(--xiu-text-3);
  margin-bottom: 12px;
  padding-left: 4px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.cd-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

/* 卡片 */
.cd-card {
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
  cursor: pointer;
  aspect-ratio: 3 / 4;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  box-shadow: var(--shadow);
}
.cd-card:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: var(--shadow-lg);
}
.cd-card.cd-pinned {
  outline: 2px solid var(--yq-gold);
  outline-offset: 2px;
}

.cd-card-bg {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  transition: transform 0.3s ease;
}
.cd-card:hover .cd-card-bg {
  transform: scale(1.05);
}

.cd-card-foil {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  background: linear-gradient(
    135deg,
    transparent 40%,
    rgba(255, 255, 255, 0.08) 50%,
    transparent 60%
  );
  background-size: 200% 200%;
  animation: cd-shimmer 3s ease infinite;
}
@keyframes cd-shimmer {
  0% { background-position: 200% 200%; }
  100% { background-position: -200% -200%; }
}

.cd-card-body {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 14px;
  background: linear-gradient(to bottom, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0.55) 100%);
}

.cd-card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.cd-icon {
  font-size: 20px;
  line-height: 1;
}
.cd-days {
  font-size: 28px;
  font-weight: 700;
  font-family: var(--font-serif);
  line-height: 1;
  text-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.cd-card-title {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  text-shadow: 0 1px 4px rgba(0,0,0,0.4);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.4;
}
.cd-card-date {
  font-size: 11px;
  color: rgba(255,255,255,0.75);
}
.cd-card-meta {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.cd-tag {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
  font-weight: 500;
}
.cd-down { background: rgba(61,184,176,0.3); color: #a8d3ce; }
.cd-up { background: rgba(199,169,107,0.3); color: #e4d9bd; }
.cd-pin { background: rgba(199,169,107,0.3); color: var(--yq-gold); }
.cd-arch { background: rgba(150,150,150,0.2); color: rgba(255,255,255,0.5); }

.cd-card-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 3;
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}
.cd-card:hover .cd-card-actions {
  opacity: 1;
}

/* 对话框 */
.cd-look-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cd-look-fields {
  display: flex;
  gap: 8px;
}
.cd-color-swatch {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  flex-shrink: 0;
}
.cd-bg-upload {
  display: flex;
  align-items: center;
  gap: 10px;
}
.cd-bg-thumb {
  width: 60px;
  height: 40px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid var(--xiu-line);
}
</style>
