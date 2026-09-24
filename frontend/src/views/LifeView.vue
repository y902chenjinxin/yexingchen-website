<!--
  LifeView.vue
  玄黄 · 生活岛（v2.15）
  - 家人共享：所有家庭成员都能看 / 改 / 删数据，按 member_id 切片展示
  - 体重：趋势图（按成员分线） + 时间轴列表
  - 三餐：瀑布流 + meal_type chip
-->
<template>
  <IslandInnerBase type="life" title="生活" subtitle="家人共享 · 体重 / 三餐">
    <template #toolbar>
      <div class="life-tb">
        <el-select v-model="filterMember" size="small" clearable placeholder="全部家人" class="life-tb-sel">
          <el-option label="全部家人" :value="''" />
          <el-option v-for="m in members" :key="m.id" :label="`${m.avatar} ${m.display_name}`" :value="m.id" />
        </el-select>
        <el-radio-group v-model="filterRange" size="small" class="life-tb-range">
          <el-radio-button value="7">7 天</el-radio-button>
          <el-radio-button value="30">30 天</el-radio-button>
          <el-radio-button value="90">90 天</el-radio-button>
          <el-radio-button value="all">全部</el-radio-button>
        </el-radio-group>
        <el-button type="primary" size="small" @click="openWeightDialog">＋ 记体重</el-button>
        <el-button size="small" plain @click="openMealDialog">📷 记一餐</el-button>
        <el-button size="small" plain @click="openMembersDialog">家人</el-button>
      </div>
    </template>

    <div class="life-layout">
      <!-- 左栏：体重 -->
      <section class="life-col life-weight">
        <div class="life-col-head">
          <h3>⚖️ 体重趋势</h3>
          <span class="life-col-meta" v-if="weightList.length">
            {{ members.length }} 位家人 · 共 {{ weightList.length }} 条记录
          </span>
        </div>

        <!-- 加载中：鎏金光扫骨架 -->
        <div v-if="loading && !weightList.length" class="life-skel">
          <SkeletonBlock v-for="i in 4" :key="i" width="100%" height="20px" style="margin-bottom: 8px;" />
        </div>

        <!-- 趋势图：每人一条折线 -->
        <div v-else-if="weightList.length" class="wt-chart-wrap">
          <svg :viewBox="`0 0 ${CHART_W} ${CHART_H}`" class="wt-chart" preserveAspectRatio="xMidYMid meet">
            <!-- 网格 -->
            <g class="wt-grid">
              <line v-for="i in 4" :key="'g' + i"
                :x1="CHART_PAD_L" :x2="CHART_W - CHART_PAD_R"
                :y1="CHART_PAD_T + (CHART_H - CHART_PAD_T - CHART_PAD_B) * i / 4"
                :y2="CHART_PAD_T + (CHART_H - CHART_PAD_T - CHART_PAD_B) * i / 4" />
            </g>
            <!-- X 轴：起始 / 结束日期 -->
            <g class="wt-axis-x">
              <text :x="CHART_PAD_L" :y="CHART_H - 8" text-anchor="start">{{ chartRange.from }}</text>
              <text :x="CHART_W - CHART_PAD_R" :y="CHART_H - 8" text-anchor="end">{{ chartRange.to }}</text>
            </g>
            <!-- Y 轴：min ~ max -->
            <g class="wt-axis-y" v-if="chartRange.yMin != null">
              <text :x="CHART_PAD_L - 6" :y="CHART_PAD_T + 4" text-anchor="end">{{ chartRange.yMax.toFixed(1) }}</text>
              <text :x="CHART_PAD_L - 6" :y="CHART_H - CHART_PAD_B" text-anchor="end">{{ chartRange.yMin.toFixed(1) }}</text>
            </g>
            <!-- 折线：每人一条 -->
            <g v-for="(line, idx) in weightLines" :key="line.memberId">
              <polyline
                :points="line.points"
                fill="none"
                :stroke="line.color"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                class="wt-line"
              />
              <circle v-for="p in line.dots" :key="p.k"
                :cx="p.x" :cy="p.y" r="3" :fill="line.color" class="wt-dot" />
            </g>
            <!-- 图例 -->
            <g class="wt-legend" v-if="weightLines.length">
              <g v-for="(line, idx) in weightLines" :key="'l' + line.memberId"
                 :transform="`translate(${CHART_PAD_L + idx * 90}, ${CHART_PAD_T - 14})`">
                <circle cx="4" cy="0" r="4" :fill="line.color" />
                <text x="12" y="4" :fill="line.color" class="wt-legend-text">
                  {{ line.name }} {{ line.latest }}
                </text>
              </g>
            </g>
          </svg>
        </div>
        <EmptyState
          v-else
          tone="generic"
          size="sm"
          title="还没有体重记录"
          description="点上方「＋ 记体重」添加第一条数据，体重曲线会按家人自动分线"
        />

        <!-- 列表 -->
        <div v-if="weightList.length" class="wt-list">
          <div v-for="g in weightGroups" :key="g.date" class="wt-day">
            <div class="wt-day-hd">
              <span class="wt-day-date">{{ g.date }}</span>
              <span class="wt-day-n">{{ g.items.length }} 条</span>
            </div>
            <div v-for="w in g.items" :key="w.id" class="wt-row">
              <span class="wt-row-avatar">{{ w.member_avatar || '🌿' }}</span>
              <div class="wt-row-main">
                <div class="wt-row-title">{{ w.member_name }} <span class="wt-row-w">{{ w.weight_kg }} kg</span></div>
                <div v-if="w.note" class="wt-row-note">{{ w.note }}</div>
              </div>
              <el-button link size="small" type="danger" @click="onDeleteWeight(w)">删除</el-button>
            </div>
          </div>
        </div>
      </section>

      <!-- 右栏：餐饮 -->
      <section class="life-col life-meal">
        <div class="life-col-head">
          <h3>🍱 三餐记录</h3>
          <span class="life-col-meta" v-if="mealList.length">{{ mealList.length }} 张</span>
        </div>

        <div v-if="loading && !mealList.length" class="life-skel life-skel-grid">
          <SkeletonBlock v-for="i in 6" :key="i" width="100%" height="160px" />
        </div>

        <div v-else-if="mealList.length" class="meal-grid">
          <figure v-for="m in mealList" :key="m.id" class="meal-card">
            <div class="meal-img-wrap">
              <img :src="mealPhotoUrl(m.photo_path)" :alt="m.note || m.member_name" class="meal-img" loading="lazy" />
              <span class="meal-type-tag" :class="'mt-' + m.meal_type">{{ mealLabel(m.meal_type) }}</span>
            </div>
            <figcaption class="meal-info">
              <div class="meal-meta">
                <span class="meal-avatar">{{ m.member_avatar || '🌿' }}</span>
                <span class="meal-name">{{ m.member_name }}</span>
                <span class="meal-date">{{ shortDateTime(m.taken_at) }}</span>
              </div>
              <p v-if="m.note" class="meal-note">{{ m.note }}</p>
              <el-button link size="small" type="danger" class="meal-del" @click="onDeleteMeal(m)">删除</el-button>
            </figcaption>
          </figure>
        </div>

        <EmptyState
          v-else
          tone="generic"
          size="sm"
          title="还没有三餐记录"
          description="点「📷 记一餐」上传第一张照片，三餐记录按家人自动归类"
        />
      </section>
    </div>

    <!-- 记体重弹窗 -->
    <el-dialog v-model="showWeightDialog" title="记体重" width="420px" append-to-body>
      <el-form :model="weightForm" label-width="80px">
        <el-form-item label="家人">
          <el-select v-model="weightForm.member_id" placeholder="选家人" style="width:100%">
            <el-option v-for="m in members" :key="m.id" :label="`${m.avatar} ${m.display_name}`" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="体重 (kg)">
          <el-input-number v-model="weightForm.weight_kg" :precision="1" :step="0.1" :min="10" :max="500" controls-position="right" style="width:100%" />
        </el-form-item>
        <el-form-item label="测量时间">
          <el-date-picker v-model="weightForm.measured_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss"
                          placeholder="默认现在" style="width:100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="weightForm.note" placeholder="可选：早起空腹 / 运动后…" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showWeightDialog = false">取消</el-button>
        <el-button type="primary" :loading="weightSubmitting" @click="submitWeight">记录</el-button>
      </template>
    </el-dialog>

    <!-- 记一餐弹窗 -->
    <el-dialog v-model="showMealDialog" title="记一餐" width="460px" append-to-body>
      <el-form :model="mealForm" label-width="80px">
        <el-form-item label="家人">
          <el-select v-model="mealForm.member_id" placeholder="选家人" style="width:100%">
            <el-option v-for="m in members" :key="m.id" :label="`${m.avatar} ${m.display_name}`" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="餐别">
          <el-radio-group v-model="mealForm.meal_type">
            <el-radio-button value="breakfast">🌅 早餐</el-radio-button>
            <el-radio-button value="lunch">☀️ 午餐</el-radio-button>
            <el-radio-button value="dinner">🌙 晚餐</el-radio-button>
            <el-radio-button value="snack">🍪 加餐</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="照片">
          <el-upload
            :auto-upload="false"
            :limit="1"
            accept=".jpg,.jpeg,.png,.webp,.gif"
            :file-list="mealFileList"
            :on-change="handleMealFileChange"
            :on-remove="handleMealFileRemove"
          >
            <el-button>选择照片</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="mealForm.note" placeholder="可选：妈妈做的红烧肉" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMealDialog = false">取消</el-button>
        <el-button type="primary" :loading="mealSubmitting" :disabled="!mealFileRaw" @click="submitMeal">上传</el-button>
      </template>
    </el-dialog>

    <!-- 家人管理弹窗 -->
    <el-dialog v-model="showMembersDialog" title="家人" width="500px" append-to-body>
      <div v-if="!members.length" class="life-empty">还没有家人档案</div>
      <div v-else class="members-grid">
        <div v-for="m in members" :key="m.id" class="member-card">
          <span class="member-card-avatar">{{ m.avatar || '🌿' }}</span>
          <div class="member-card-main">
            <div class="member-card-name">
              {{ m.display_name }}
              <el-tag v-if="m.is_owner" size="small" type="warning" effect="dark">房主</el-tag>
            </div>
            <div class="member-card-meta">
              {{ m.height_cm ? m.height_cm + 'cm' : '未填身高' }}
              · {{ m.birth_year || '未知年份' }}
            </div>
          </div>
          <div class="member-card-ops">
            <el-button size="small" plain @click="editMemberInline(m)">改名</el-button>
            <el-button v-if="!m.is_owner" size="small" plain type="danger" @click="onDeleteMember(m)">删除</el-button>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showMembersDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import EmptyState from '@/components/EmptyState.vue'
import SkeletonBlock from '@/components/common/SkeletonBlock.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useLifeStore } from '@/stores/life'

const store = useLifeStore()
const members = computed(() => store.members)
const weightList = computed(() => store.weightList)
const mealList = computed(() => store.mealList)
const loading = computed(() => store.loading)

// ============================== 顶部筛选 ==============================
const filterMember = ref('')
const filterRange = ref('30')

// ============================== 体重图表 ==============================
const CHART_W = 560
const CHART_H = 220
const CHART_PAD_L = 38
const CHART_PAD_R = 16
const CHART_PAD_T = 28
const CHART_PAD_B = 24

// 每位成员一条折线
const PALETTE = ['#c7a96b', '#7fa8a3', '#d97706', '#4f5ed1', '#16a34a', '#dc2626', '#a855f7']
const weightLines = computed(() => {
  const lines = []
  const filtered = filterMember.value
    ? weightList.value.filter((w) => String(w.member_id) === String(filterMember.value))
    : weightList.value

  const byMember = new Map()
  for (const w of filtered) {
    if (!byMember.has(w.member_id)) byMember.set(w.member_id, [])
    byMember.get(w.member_id).push(w)
  }
  let idx = 0
  for (const [memberId, items] of byMember) {
    // 按 measured_at 升序
    items.sort((a, b) => new Date(a.measured_at) - new Date(b.measured_at))
    const color = PALETTE[idx++ % PALETTE.length]
    const tsArr = items.map((w) => new Date(w.measured_at).getTime())
    const wArr = items.map((w) => Number(w.weight_kg))
    lines.push({
      memberId,
      name: items[0].member_name,
      avatar: items[0].member_avatar,
      color,
      items,
      latest: `${wArr[wArr.length - 1].toFixed(1)} kg`,
      points: '',
      dots: [],
      _ts: tsArr,
      _w: wArr,
    })
  }
  return lines
})

const chartRange = computed(() => {
  const lines = weightLines.value
  if (!lines.length) return { from: '', to: '', yMin: null, yMax: null }
  const allTs = lines.flatMap((l) => l._ts)
  const allW = lines.flatMap((l) => l._w)
  const minT = Math.min(...allTs), maxT = Math.max(...allTs)
  const yMin = Math.min(...allW), yMax = Math.max(...allW)
  const pad = (yMax - yMin) * 0.1 || 1
  // 算出坐标点
  const innerW = CHART_W - CHART_PAD_L - CHART_PAD_R
  const innerH = CHART_H - CHART_PAD_T - CHART_PAD_B
  const xScale = (ts) => CHART_PAD_L + ((ts - minT) / Math.max(1, maxT - minT)) * innerW
  const yScale = (w) => CHART_PAD_T + ((yMax + pad - w) / Math.max(0.1, (yMax + pad) - (yMin - pad))) * innerH
  for (const l of lines) {
    l.points = l._ts.map((ts, i) => `${xScale(ts).toFixed(1)},${yScale(l._w[i]).toFixed(1)}`).join(' ')
    l.dots = l._ts.map((ts, i) => ({ k: i, x: xScale(ts), y: yScale(l._w[i]) }))
  }
  const fmt = (ts) => {
    const d = new Date(ts)
    return `${d.getMonth() + 1}/${d.getDate()}`
  }
  return { from: fmt(minT), to: fmt(maxT), yMin: yMin - pad, yMax: yMax + pad }
})

// 列表按日期分组
const weightGroups = computed(() => {
  const filtered = filterMember.value
    ? weightList.value.filter((w) => String(w.member_id) === String(filterMember.value))
    : weightList.value
  const map = new Map()
  for (const w of filtered) {
    const key = w.measured_at.slice(0, 10)
    if (!map.has(key)) map.set(key, [])
    map.get(key).push(w)
  }
  return [...map.entries()]
    .sort((a, b) => b[0].localeCompare(a[0]))
    .map(([date, items]) => ({ date, items }))
})

// ============================== 餐饮 ==============================
function mealLabel(t) {
  return { breakfast: '早餐', lunch: '午餐', dinner: '晚餐', snack: '加餐' }[t] || t
}
function shortDateTime(s) {
  if (!s) return ''
  const d = new Date(s)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
function mealPhotoUrl(p) {
  if (!p) return ''
  // photo_path 是 /meals/xxx.jpg，由后端 /uploads/ 静态服务返回
  if (p.startsWith('http')) return p
  return p.startsWith('/') ? `/uploads${p}` : `/uploads/${p}`
}

// ============================== 弹窗 ==============================
const showWeightDialog = ref(false)
const weightSubmitting = ref(false)
const weightForm = ref({ member_id: null, weight_kg: 65.0, measured_at: '', note: '' })
function openWeightDialog() {
  weightForm.value = { member_id: members.value[0]?.id || null, weight_kg: 65.0, measured_at: '', note: '' }
  showWeightDialog.value = true
}
async function submitWeight() {
  if (!weightForm.value.member_id) { ElMessage.warning('请选家人'); return }
  if (!weightForm.value.weight_kg) { ElMessage.warning('请填体重'); return }
  weightSubmitting.value = true
  try {
    const payload = { ...weightForm.value }
    if (!payload.measured_at) delete payload.measured_at
    await store.addWeight(payload)
    ElMessage.success('已记录')
    showWeightDialog.value = false
  } catch (e) {
    const msg = e?.msg || e?.detail?.msg || e?.message || '记录失败'
    ElMessage.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  } finally {
    weightSubmitting.value = false
  }
}

const showMealDialog = ref(false)
const mealSubmitting = ref(false)
const mealForm = ref({ member_id: null, meal_type: 'breakfast', note: '' })
const mealFileList = ref([])
const mealFileRaw = ref(null)
function openMealDialog() {
  mealForm.value = { member_id: members.value[0]?.id || null, meal_type: 'breakfast', note: '' }
  mealFileList.value = []
  mealFileRaw.value = null
  showMealDialog.value = true
}
function handleMealFileChange(file) {
  if (!file || !file.raw) return
  mealFileRaw.value = file.raw
}
function handleMealFileRemove() {
  mealFileRaw.value = null
}
async function submitMeal() {
  if (!mealForm.value.member_id) { ElMessage.warning('请选家人'); return }
  if (!mealFileRaw.value) { ElMessage.warning('请选照片'); return }
  mealSubmitting.value = true
  try {
    await store.addMeal({ ...mealForm.value, photo: mealFileRaw.value })
    ElMessage.success('已上传')
    showMealDialog.value = false
  } catch (e) {
    const msg = e?.msg || e?.detail?.msg || e?.message || '上传失败'
    ElMessage.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  } finally {
    mealSubmitting.value = false
  }
}

// ============================== 删除 ==============================
async function onDeleteWeight(w) {
  try { await ElMessageBox.confirm(`确认删除 ${w.member_name} 的 ${w.weight_kg}kg？`, '提示', { type: 'warning' }) } catch { return }
  try { await store.removeWeight(w.id); ElMessage.success('已删除') } catch { /* 拦截器提示 */ }
}
async function onDeleteMeal(m) {
  try { await ElMessageBox.confirm('确认删除这张照片？', '提示', { type: 'warning' }) } catch { return }
  try { await store.removeMeal(m.id); ElMessage.success('已删除') } catch { /* 拦截器提示 */ }
}

// ============================== 家人管理 ==============================
const showMembersDialog = ref(false)
function openMembersDialog() { showMembersDialog.value = true }
async function editMemberInline(m) {
  let newName = ''
  try {
    const { value } = await ElMessageBox.prompt(`把「${m.display_name}」改成`, '改名', {
      inputValue: m.display_name,
      inputValidator: (v) => (v && v.trim() ? true : '昵称不能为空'),
    })
    newName = value.trim()
  } catch { return }
  try {
    await store.editMember(m.id, { display_name: newName })
    ElMessage.success('已更新')
  } catch { /* 拦截器提示 */ }
}
async function onDeleteMember(m) {
  try { await ElMessageBox.confirm(`确认删除家人「${m.display_name}」？其体重/三餐记录一并保留（仍归属于原 member_id）。`, '提示', { type: 'warning' }) } catch { return }
  try { await store.removeMember(m.id); ElMessage.success('已删除') } catch { /* 拦截器提示 */ }
}

// ============================== 初始化 ==============================
async function loadAll() {
  await store.fetchMembers()
  const params = {}
  if (filterMember.value) params.member_id = filterMember.value
  if (filterRange.value !== 'all') {
    const days = Number(filterRange.value)
    const from = new Date(Date.now() - days * 86400000).toISOString().slice(0, 10)
    params.from_date = from
  }
  await Promise.all([store.fetchWeight(params), store.fetchMeals(params)])
}
onMounted(loadAll)
watch([filterMember, filterRange], loadAll)
</script>

<style scoped>
.life-tb {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
}
.life-tb-sel { width: 140px; }
.life-tb-range { flex: 0 0 auto; }

.life-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr);
  gap: 18px;
  margin-top: 4px;
}
@media (max-width: 1000px) {
  .life-layout { grid-template-columns: 1fr; }
}

.life-col {
  background: var(--ls-paper);
  border: 1px solid var(--ls-line);
  border-radius: var(--ls-radius, 12px);
  padding: 18px 20px;
  box-shadow: var(--ls-shadow, 0 1px 2px rgba(0,0,0,.04));
}
.life-col-head {
  display: flex; justify-content: space-between; align-items: baseline;
  margin-bottom: 14px; padding-bottom: 8px;
  border-bottom: 1px solid var(--ls-line);
}
.life-col-head h3 { margin: 0; font-size: 15px; color: var(--lj-text); letter-spacing: .04em; }
.life-col-meta { font-size: 11.5px; color: var(--lj-text-3); font-variant-numeric: tabular-nums; }

/* 体重趋势图 */
.wt-chart-wrap {
  width: 100%;
  margin-bottom: 16px;
}
.wt-chart {
  width: 100%; height: 220px;
  display: block;
}
.wt-chart .wt-grid line {
  stroke: var(--ls-line, rgba(127,127,127,.18));
  stroke-width: 1;
  stroke-dasharray: 2 3;
}
.wt-chart .wt-axis-x text,
.wt-chart .wt-axis-y text {
  fill: var(--lj-text-3);
  font-size: 10px;
  font-family: inherit;
}
.wt-chart .wt-line {
  filter: drop-shadow(0 1px 2px rgba(0,0,0,.18));
  transition: stroke-width var(--motion-fast, .12s) var(--ease-standard, ease);
}
.wt-chart .wt-line:hover { stroke-width: 2.5; }
.wt-chart .wt-dot { transition: r var(--motion-fast) var(--ease-standard); }
.wt-chart .wt-dot:hover { r: 5; }
.wt-chart .wt-legend-text {
  font-size: 11px;
  font-family: inherit;
}

/* 体重列表 */
.wt-list { display: flex; flex-direction: column; gap: 10px; }
.wt-day {
  border: 1px solid var(--ls-line);
  border-radius: 8px;
  padding: 10px 12px;
  background: var(--ls-paper-2, rgba(127,127,127,.03));
}
.wt-day-hd {
  display: flex; justify-content: space-between; align-items: baseline;
  margin-bottom: 8px; padding-bottom: 6px;
  border-bottom: 1px dashed var(--ls-line);
}
.wt-day-date { font-size: 12px; font-weight: 600; color: var(--lj-text-2); }
.wt-day-n { font-size: 11px; color: var(--lj-text-3); }
.wt-row {
  display: flex; align-items: center; gap: 10px;
  padding: 5px 0;
}
.wt-row-avatar { font-size: 18px; }
.wt-row-main { flex: 1; min-width: 0; }
.wt-row-title { font-size: 13px; color: var(--lj-text); }
.wt-row-w { font-weight: 600; color: var(--yq-gold, #c7a96b); margin-left: 4px; }
.wt-row-note { font-size: 11.5px; color: var(--lj-text-3); margin-top: 2px; }

/* 三餐瀑布流 */
.meal-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 14px;
}
.meal-card {
  margin: 0;
  border: 1px solid var(--ls-line);
  border-radius: 10px;
  overflow: hidden;
  background: var(--ls-paper);
  box-shadow: 0 1px 3px rgba(0,0,0,.06);
  transition: transform var(--motion-med, .22s) var(--ease-standard, ease),
              box-shadow var(--motion-med) var(--ease-standard);
}
.meal-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 14px rgba(0,0,0,.12);
}
.meal-img-wrap { position: relative; aspect-ratio: 1 / 1; overflow: hidden; }
.meal-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.meal-type-tag {
  position: absolute; top: 8px; left: 8px;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 11px; font-weight: 600;
  backdrop-filter: blur(6px);
  background: rgba(0, 0, 0, .45);
  color: #fff;
}
.meal-type-tag.mt-breakfast { background: rgba(217, 119, 6, .85); }
.meal-type-tag.mt-lunch     { background: rgba(91, 106, 224, .85); }
.meal-type-tag.mt-dinner    { background: rgba(127, 168, 163, .85); }
.meal-type-tag.mt-snack     { background: rgba(168, 85, 247, .85); }
.meal-info { padding: 8px 10px 6px; position: relative; }
.meal-meta {
  display: flex; align-items: center; gap: 5px;
  font-size: 11.5px; color: var(--lj-text-2);
}
.meal-avatar { font-size: 14px; }
.meal-name { font-weight: 600; color: var(--lj-text); }
.meal-date { margin-left: auto; font-size: 10.5px; color: var(--lj-text-3); font-variant-numeric: tabular-nums; }
.meal-note { margin: 4px 0 0; font-size: 11.5px; color: var(--lj-text-3); line-height: 1.55; }
.meal-del { position: absolute; top: 6px; right: 6px; }

/* 骨架 */
.life-skel { padding: 4px 0; }
.life-skel-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px; }

/* 家人管理 */
.life-empty { padding: 30px; text-align: center; color: var(--lj-text-3); }
.members-grid { display: flex; flex-direction: column; gap: 10px; max-height: 60vh; overflow-y: auto; }
.member-card {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--ls-line);
  border-radius: 8px;
  background: var(--ls-paper-2, rgba(127,127,127,.03));
}
.member-card-avatar { font-size: 26px; line-height: 1; }
.member-card-main { flex: 1; min-width: 0; }
.member-card-name { font-size: 14px; color: var(--lj-text); display: flex; align-items: center; gap: 6px; }
.member-card-meta { font-size: 11.5px; color: var(--lj-text-3); margin-top: 2px; }
.member-card-ops { display: flex; gap: 4px; }
</style>
