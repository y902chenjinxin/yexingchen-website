<!--
  LifeView.vue
  玄黄 · 生活岛
  - 家人共享：所有家庭成员都能看 / 改 / 删数据，按 member_id 切片展示
  - v2.41：原「体重三餐」拆成两个菜单，同一视图靠 mode 切换
      mode="weight" → 体重记录（趋势图 + 时间轴列表）
      mode="meals"  → 美食记忆（只记大餐 / 纪念餐，支持编辑 / 删除 / 大图预览）
-->
<template>
  <IslandInnerBase
    type="life"
    :title="isMeals ? '美食记忆' : '体重记录'"
    :subtitle="isMeals ? '家人共享 · 只记大餐与值得纪念的一顿' : '家人共享 · 体重趋势与记录'"
  >
    <template #toolbar>
      <div class="life-tb">
        <el-radio-group v-model="filterRange" size="small" class="life-tb-range">
          <el-radio-button value="7">7 天</el-radio-button>
          <el-radio-button value="30">30 天</el-radio-button>
          <el-radio-button value="90">90 天</el-radio-button>
          <el-radio-button value="all">全部</el-radio-button>
        </el-radio-group>
        <el-button v-if="!isMeals" type="primary" size="small" @click="openWeightDialog">＋ 记体重</el-button>
        <el-button v-else type="primary" size="small" @click="openMealDialog">📷 记一顿</el-button>
        <el-button size="small" plain @click="openMembersDialog">家人</el-button>
      </div>
    </template>

    <!-- 人员标签 + 家人汇总：数据全家共享，按成员切片查看 -->
    <section class="life-members">
      <div class="life-members-head">
        <h3>👨‍👩‍👧 家人</h3>
        <span class="life-col-meta">{{ rangeLabel }} · 点标签看各自的，汇总为全家</span>
      </div>

      <div class="life-mtags">
        <button class="life-mtag" :class="{ on: !filterMember }" @click="pickMember('')">
          <span class="life-mtag-avatar">🏠</span>
          <span class="life-mtag-name">全部家人</span>
          <span class="life-mtag-meta">{{ allCountText }}</span>
        </button>
        <button
          v-for="m in members"
          :key="m.id"
          class="life-mtag"
          :class="{ on: String(filterMember) === String(m.id) }"
          @click="pickMember(m.id)"
        >
          <span class="life-mtag-avatar">{{ m.avatar || '🌿' }}</span>
          <span class="life-mtag-name">{{ m.display_name }}</span>
          <span class="life-mtag-meta">{{ memberCountText(m.id) }}</span>
        </button>
      </div>

      <div class="life-sum-grid">
        <!-- 体重汇总 -->
        <div v-if="!isMeals" class="life-sum-card">
          <div class="life-sum-title">⚖️ 体重汇总</div>
          <div class="life-sum-table-wrap" v-if="weightSummary.length">
          <table class="life-sum-table">
            <thead>
              <tr><th class="c-name">成员</th><th>记录</th><th>最新</th><th>区间变化</th><th>最近测量</th></tr>
            </thead>
            <tbody>
              <tr
                v-for="s in weightSummary"
                :key="s.memberId"
                class="life-sum-row"
                :class="{ on: String(filterMember) === String(s.memberId) }"
                @click="pickMember(s.memberId)"
              >
                <td class="c-name"><span class="life-sum-avatar">{{ s.avatar }}</span>{{ s.name }}</td>
                <td>{{ s.count }}</td>
                <td class="life-sum-strong">{{ s.latest }} kg</td>
                <td :class="s.deltaClass">{{ s.deltaText }}</td>
                <td>{{ s.lastAt }}</td>
              </tr>
            </tbody>
          </table>
          </div>
          <div v-else class="life-sum-empty">区间内没有体重记录</div>
        </div>

        <!-- 美食记忆汇总：按「场合」统计，帮家人回看这些值得记的饭 -->
        <div v-else class="life-sum-card">
          <div class="life-sum-title">🍱 美食汇总</div>
          <div class="life-sum-table-wrap" v-if="mealSummary.length">
          <table class="life-sum-table">
            <thead>
              <tr><th class="c-name">成员</th><th>张数</th><th>大餐</th><th>纪念日</th><th>旅行</th><th>家常</th></tr>
            </thead>
            <tbody>
              <tr
                v-for="s in mealSummary"
                :key="s.memberId"
                class="life-sum-row"
                :class="{ on: String(filterMember) === String(s.memberId) }"
                @click="pickMember(s.memberId)"
              >
                <td class="c-name"><span class="life-sum-avatar">{{ s.avatar }}</span>{{ s.name }}</td>
                <td class="life-sum-strong">{{ s.count }}</td>
                <td>{{ s.feast }}</td>
                <td>{{ s.memory }}</td>
                <td>{{ s.travel }}</td>
                <td>{{ s.home }}</td>
              </tr>
            </tbody>
          </table>
          </div>
          <div v-else class="life-sum-empty">区间内还没有美食记忆</div>
        </div>
      </div>
    </section>

    <!-- ===== 体重记录 ===== -->
    <div v-if="!isMeals" class="life-layout">
      <section class="life-col">
        <div class="life-col-head">
          <h3>⚖️ 体重趋势</h3>
          <span class="life-col-meta" v-if="weightList.length">
            <template v-if="filterMember">仅看 {{ activeMemberName }} · </template>{{ weightFiltered.length }} 条记录
          </span>
        </div>

        <!-- 加载中：鎏金光扫骨架 -->
        <div v-if="loading && !weightList.length" class="life-skel">
          <SkeletonBlock v-for="i in 4" :key="i" width="100%" height="20px" style="margin-bottom: 8px;" />
        </div>

        <!-- 趋势图：每人一条折线 -->
        <div v-else-if="weightFiltered.length" class="wt-chart-wrap">
          <svg
            ref="wtSvg"
            :viewBox="`0 0 ${CHART_W} ${CHART_H}`"
            class="wt-chart"
            preserveAspectRatio="xMidYMid meet"
            @mousemove="onMove"
            @mouseleave="onLeave"
            @touchstart.passive="onTouchStart"
            @touchmove.passive="onTouchMove"
            @touchend.passive="onTouchEnd"
          >
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
            <g v-for="line in weightLines" :key="line.memberId">
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
            <!-- 悬浮十字线：吸附到最近一次的测量日期 -->
            <g v-if="hoverCol" class="wt-hover">
              <line :x1="hoverCol.x" :x2="hoverCol.x"
                :y1="CHART_PAD_T" :y2="CHART_H - CHART_PAD_B" class="wt-cross" />
              <circle v-for="h in hoverDots" :key="'h' + h.memberId"
                :cx="h.x" :cy="h.y" r="4.5" :fill="h.color" class="wt-hover-dot" />
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
          <ChartTip
            :show="hoverCol !== null"
            :x="hoverX"
            :vw="CHART_W"
            :title="hoverTitle"
            :rows="hoverRows"
          />
        </div>
        <EmptyState
          v-else
          tone="generic"
          size="sm"
          :title="filterMember ? `${activeMemberName} 还没有体重记录` : '还没有体重记录'"
          :description="filterMember ? '切回「全部家人」看其他家人的记录' : '点上方「＋ 记体重」添加第一条数据，体重曲线会按家人自动分线'"
        />
      </section>

      <section class="life-col">
        <div class="life-col-head">
          <h3>📋 体重明细</h3>
          <span class="life-col-meta" v-if="weightGroups.length">按日期倒序 · {{ weightFiltered.length }} 条</span>
        </div>
        <div v-if="weightGroups.length" class="wt-list">
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
        <EmptyState
          v-else
          tone="generic"
          size="sm"
          title="还没有明细"
          description="记录体重后，这里按日期倒序列出每一条"
        />
      </section>
    </div>

    <!-- ===== 美食记忆 ===== -->
    <div v-else class="life-layout life-layout-single">
      <section class="life-col life-meal">
        <div class="life-col-head">
          <h3>🍱 美食记忆</h3>
          <span class="life-col-meta" v-if="mealList.length">
            <template v-if="filterMember">仅看 {{ activeMemberName }} · </template>{{ mealFiltered.length }} 张
          </span>
        </div>
        <p class="meal-hint">只记大餐与值得纪念的一顿 —— 日常三餐不必上传，这里留给回头会想念的味道。</p>

        <div v-if="loading && !mealList.length" class="life-skel life-skel-grid">
          <SkeletonBlock v-for="i in 6" :key="i" width="100%" height="160px" />
        </div>

        <div v-else-if="mealFiltered.length" class="meal-grid">
          <figure v-for="m in mealFiltered" :key="m.id" class="meal-card">
            <button class="meal-img-wrap" type="button" :aria-label="`预览 ${m.note || m.member_name} 的照片`" @click="openPreview(m)">
              <img :src="mealPhotoUrl(m.photo_path)" :alt="m.note || m.member_name" class="meal-img" loading="lazy" />
              <span class="meal-type-tag" :class="mealKindClass(m.meal_type)">{{ mealLabel(m.meal_type) }}</span>
              <span class="meal-zoom">🔍</span>
            </button>
            <figcaption class="meal-info">
              <div class="meal-meta">
                <span class="meal-avatar">{{ m.member_avatar || '🌿' }}</span>
                <span class="meal-name">{{ m.member_name }}</span>
                <span class="meal-date">{{ shortDateTime(m.taken_at) }}</span>
              </div>
              <p v-if="m.note" class="meal-note">{{ m.note }}</p>
              <div class="meal-ops">
                <button type="button" class="meal-op" @click="openPreview(m)">预览</button>
                <button type="button" class="meal-op" @click="openMealEdit(m)">编辑</button>
                <button type="button" class="meal-op danger" @click="onDeleteMeal(m)">删除</button>
              </div>
            </figcaption>
          </figure>
        </div>

        <EmptyState
          v-else
          tone="generic"
          size="sm"
          :title="filterMember ? `${activeMemberName} 还没有美食记忆` : '还没有美食记忆'"
          :description="filterMember ? '切回「全部家人」看其他家人的记录' : '点「📷 记一顿」上传大餐或纪念餐的照片，按家人自动归类'"
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

    <!-- 记一顿 / 编辑美食记忆（同一表单，靠 mealEditingId 区分） -->
    <el-dialog v-model="showMealDialog" :title="mealDialogTitle" width="460px" append-to-body>
      <el-form :model="mealForm" label-width="80px">
        <el-form-item label="家人">
          <el-select v-model="mealForm.member_id" placeholder="选家人" style="width:100%">
            <el-option v-for="m in members" :key="m.id" :label="`${m.avatar} ${m.display_name}`" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="场合">
          <el-radio-group v-model="mealForm.meal_type">
            <el-radio-button v-if="legacyKind" :value="mealForm.meal_type">{{ legacyKind }}</el-radio-button>
            <el-radio-button v-for="k in MEAL_KINDS" :key="k.value" :value="k.value">{{ k.icon }} {{ k.label }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="时间">
          <el-date-picker v-model="mealForm.taken_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss"
                          placeholder="默认现在" style="width:100%" />
        </el-form-item>
        <el-form-item label="照片">
          <!-- v2.40.24：手机上新增「拍照」直接调起后置相机（capture），原「从相册选」保留 -->
          <div class="meal-photo-row">
            <label class="meal-photo-btn">
              📸 拍照
              <input type="file" accept="image/*" capture="environment" hidden @change="onMealPick($event)">
            </label>
            <label class="meal-photo-btn">
              🖼 从相册选
              <input type="file" accept="image/*" hidden @change="onMealPick($event)">
            </label>
            <div v-if="mealPhotoShown" class="meal-photo-preview">
              <img :src="mealPhotoShown" alt="已选照片">
              <button type="button" class="meal-photo-del" aria-label="移除照片" @click="clearMealPhoto">×</button>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="mealForm.note" maxlength="60" show-word-limit placeholder="可选：妈妈做的红烧肉" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMealDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="mealSubmitting"
          :disabled="!mealPhotoShown"
          @click="submitMeal"
        >{{ mealEditingId ? '保存' : '上传' }}</el-button>
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

    <!-- 大图预览：整屏毛玻璃灯箱，点背景 / 按 Esc 关闭 -->
    <Teleport to="body">
      <div v-if="previewMeal" ref="lightboxEl" class="meal-lb" tabindex="-1" @click.self="closePreview">
        <figure class="meal-lb-box">
          <img :src="mealPhotoUrl(previewMeal.photo_path)" :alt="previewMeal.note || previewMeal.member_name" class="meal-lb-img">
          <figcaption class="meal-lb-bar">
            <div class="meal-lb-meta">
              <span class="meal-type-tag" :class="mealKindClass(previewMeal.meal_type)">{{ mealLabel(previewMeal.meal_type) }}</span>
              <span class="meal-lb-name">{{ previewMeal.member_avatar || '🌿' }} {{ previewMeal.member_name }}</span>
              <span class="meal-lb-date">{{ longDateTime(previewMeal.taken_at) }}</span>
            </div>
            <p v-if="previewMeal.note" class="meal-lb-note">{{ previewMeal.note }}</p>
            <div class="meal-lb-ops">
              <button type="button" class="meal-lb-btn" @click="editFromPreview">编辑</button>
              <button type="button" class="meal-lb-btn danger" @click="deleteFromPreview">删除</button>
              <button type="button" class="meal-lb-btn" @click="closePreview">关闭</button>
            </div>
          </figcaption>
          <button type="button" class="meal-lb-x" aria-label="关闭预览" @click="closePreview">✕</button>
        </figure>
      </div>
    </Teleport>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import IslandInnerBase from './islands/IslandInnerBase.vue'
import EmptyState from '@/components/EmptyState.vue'
import SkeletonBlock from '@/components/common/SkeletonBlock.vue'
import ChartTip from '@/components/charts/ChartTip.vue'
import { useChartHover } from '@/composables/useChartHover'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useLifeStore } from '@/stores/life'
import { useAuthStore } from '@/stores/auth'

// mode 由路由 props 注入：'weight' 体重记录 / 'meals' 美食记忆
const props = defineProps({
  mode: { type: String, default: 'weight' },
})
const isMeals = computed(() => props.mode === 'meals')

const store = useLifeStore()
const auth = useAuthStore()
const members = computed(() => store.members)
const weightList = computed(() => store.weightList)
const mealList = computed(() => store.mealList)
const loading = computed(() => store.loading)

// ============================== 顶部筛选 ==============================
// 成员筛选走客户端切片：列表按人过滤，但汇总始终保留全家的口径
const filterMember = ref('')
const filterRange = ref('30')

const rangeLabel = computed(() => (filterRange.value === 'all' ? '全部时间' : `近 ${filterRange.value} 天`))

const activeMemberName = computed(() => {
  const hit = members.value.find((m) => String(m.id) === String(filterMember.value))
  return hit ? hit.display_name : '家人'
})

function pickMember(id) {
  const next = id === '' || id == null ? '' : id
  filterMember.value = String(filterMember.value) === String(next) ? '' : next
}

const weightFiltered = computed(() => (filterMember.value
  ? weightList.value.filter((w) => String(w.member_id) === String(filterMember.value))
  : weightList.value))

const mealFiltered = computed(() => (filterMember.value
  ? mealList.value.filter((m) => String(m.member_id) === String(filterMember.value))
  : mealList.value))

// 标签上的计数：体重看条数，美食看张数
const allCountText = computed(() => (isMeals.value
  ? `${mealList.value.length} 张`
  : `${weightList.value.length} 条记录`))
function memberCountText(id) {
  const n = isMeals.value
    ? mealSummary.value.find((s) => String(s.memberId) === String(id))?.count || 0
    : weightSummary.value.find((s) => String(s.memberId) === String(id))?.count || 0
  return isMeals.value ? `${n} 张` : `${n} 条`
}

// ============================== 家人汇总 ==============================
// 体重：每人 记录数 / 最新值 / 区间首末变化 / 最近测量日
const weightSummary = computed(() => {
  const byMember = new Map()
  for (const w of weightList.value) {
    if (!byMember.has(w.member_id)) byMember.set(w.member_id, [])
    byMember.get(w.member_id).push(w)
  }
  const out = []
  for (const [memberId, items] of byMember) {
    const asc = [...items].sort((a, b) => new Date(a.measured_at) - new Date(b.measured_at))
    const first = Number(asc[0].weight_kg)
    const last = Number(asc[asc.length - 1].weight_kg)
    const delta = last - first
    out.push({
      memberId,
      name: asc[0].member_name || '—',
      avatar: asc[0].member_avatar || '🌿',
      count: items.length,
      latest: last.toFixed(1),
      deltaText: asc.length > 1 ? `${delta > 0 ? '+' : ''}${delta.toFixed(1)} kg` : '—',
      deltaClass: asc.length > 1 ? (delta > 0 ? 'up' : (delta < 0 ? 'down' : '')) : '',
      lastAt: (asc[asc.length - 1].measured_at || '').slice(0, 10),
    })
  }
  return out.sort((a, b) => b.count - a.count)
})

// 美食记忆：每人 张数 + 各场合次数
const mealSummary = computed(() => {
  const map = new Map()
  for (const m of mealList.value) {
    if (!map.has(m.member_id)) {
      map.set(m.member_id, {
        memberId: m.member_id,
        name: m.member_name || '—',
        avatar: m.member_avatar || '🌿',
        count: 0, feast: 0, memory: 0, travel: 0, home: 0,
      })
    }
    const s = map.get(m.member_id)
    s.count += 1
    if (s[m.meal_type] != null) s[m.meal_type] += 1
  }
  return [...map.values()].sort((a, b) => b.count - a.count)
})

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
  const byMember = new Map()
  for (const w of weightFiltered.value) {
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

// 悬浮读数：吸附到最近的测量日期，同一天多位家人的体重一起展示
const wtSvg = ref(null)
const weightCols = computed(() => {
  const lines = weightLines.value
  if (!lines.length) return []
  const allTs = lines.flatMap((l) => l._ts)
  const minT = Math.min(...allTs)
  const maxT = Math.max(...allTs)
  const innerW = CHART_W - CHART_PAD_L - CHART_PAD_R
  const span = Math.max(1, maxT - minT)
  return [...new Set(allTs)].sort((a, b) => a - b)
    .map((ts) => ({ ts, x: CHART_PAD_L + ((ts - minT) / span) * innerW }))
})

const { hoverIndex, hoverX, onMove, onLeave, onTouchStart, onTouchMove, onTouchEnd } = useChartHover({
  svgRef: wtSvg,
  columns: () => weightCols.value.map((c) => c.x),
})

const hoverCol = computed(() => weightCols.value[hoverIndex.value] || null)

const hoverDots = computed(() => {
  const col = hoverCol.value
  const r = chartRange.value
  if (!col || r.yMin == null) return []
  const innerH = CHART_H - CHART_PAD_T - CHART_PAD_B
  const spanY = Math.max(0.1, r.yMax - r.yMin)
  const yScale = (w) => CHART_PAD_T + ((r.yMax - w) / spanY) * innerH
  const out = []
  for (const l of weightLines.value) {
    const i = l._ts.indexOf(col.ts)
    if (i < 0) continue
    out.push({ memberId: l.memberId, color: l.color, x: col.x, y: yScale(l._w[i]) })
  }
  return out
})

const hoverTitle = computed(() => {
  const col = hoverCol.value
  if (!col) return ''
  const d = new Date(col.ts)
  return `${d.getMonth() + 1}/${d.getDate()}`
})

const hoverRows = computed(() => {
  const col = hoverCol.value
  if (!col) return []
  const rows = []
  for (const l of weightLines.value) {
    const i = l._ts.indexOf(col.ts)
    if (i < 0) continue
    rows.push({ label: l.name, value: `${l._w[i].toFixed(1)} kg`, color: l.color })
  }
  return rows
})

// 列表按日期分组
const weightGroups = computed(() => {
  const map = new Map()
  for (const w of weightFiltered.value) {
    const key = w.measured_at.slice(0, 10)
    if (!map.has(key)) map.set(key, [])
    map.get(key).push(w)
  }
  return [...map.entries()]
    .sort((a, b) => b[0].localeCompare(a[0]))
    .map(([date, items]) => ({ date, items }))
})

// ============================== 美食记忆 ==============================
// 场合（v2.41）：大餐 / 纪念日 / 旅行美食 / 家常好菜
const MEAL_KINDS = [
  { value: 'feast', label: '大餐', icon: '🍽' },
  { value: 'memory', label: '纪念日', icon: '🎉' },
  { value: 'travel', label: '旅行美食', icon: '✈️' },
  { value: 'home', label: '家常好菜', icon: '🏠' },
]
// v2.41 之前的三餐值，老数据仍要能正常显示
const LEGACY_MEAL_LABEL = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐', snack: '加餐' }
function mealLabel(t) {
  const hit = MEAL_KINDS.find((k) => k.value === t)
  return hit ? hit.label : (LEGACY_MEAL_LABEL[t] || t)
}
function mealKindClass(t) {
  return MEAL_KINDS.some((k) => k.value === t) ? `mt-${t}` : 'mt-legacy'
}
// 编辑老数据时，把历史值原样摆出来，避免「没选中任何场合」的困惑
const legacyKind = computed(() => {
  const t = mealForm.value.meal_type
  if (MEAL_KINDS.some((k) => k.value === t)) return ''
  return LEGACY_MEAL_LABEL[t] ? `${LEGACY_MEAL_LABEL[t]}（旧）` : ''
})
function shortDateTime(s) {
  if (!s) return ''
  const d = new Date(s)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
function longDateTime(s) {
  if (!s) return ''
  const d = new Date(s)
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
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
    await loadAll()
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
const mealEditingId = ref(null)      // 非空 = 编辑已有记录
const mealForm = ref({ member_id: null, meal_type: 'feast', taken_at: '', note: '' })
const mealFileRaw = ref(null)        // 新挑的文件（编辑时可不换图）
const mealPickedUrl = ref('')        // 新挑文件的本地预览地址
const mealExistingUrl = ref('')      // 编辑时原图地址
const mealDialogTitle = computed(() => (mealEditingId.value ? '编辑美食记忆' : '记一顿'))
// 表单里展示的照片：优先新挑的，其次原图
const mealPhotoShown = computed(() => mealPickedUrl.value || mealExistingUrl.value)

function resetMealForm() {
  mealEditingId.value = null
  mealFileRaw.value = null
  mealPickedUrl.value = ''
  mealExistingUrl.value = ''
  mealForm.value = { member_id: members.value[0]?.id || null, meal_type: 'feast', taken_at: '', note: '' }
}
function openMealDialog() {
  resetMealForm()
  showMealDialog.value = true
}
function openMealEdit(m) {
  resetMealForm()
  mealEditingId.value = m.id
  mealForm.value = {
    member_id: m.member_id,
    // 老行是 breakfast/lunch/... ：保留原值，不强行改成新场合
    meal_type: m.meal_type || 'feast',
    taken_at: (m.taken_at || '').replace(' ', 'T').slice(0, 19),
    note: m.note || '',
  }
  mealExistingUrl.value = mealPhotoUrl(m.photo_path)
  showMealDialog.value = true
}
/** 拍照 / 相册共用：capture 的 input 会直接调起手机后置相机 */
function onMealPick(e) {
  const f = e.target?.files?.[0]
  if (!f) return
  mealFileRaw.value = f
  mealPickedUrl.value = URL.createObjectURL(f)
  e.target.value = ''
}
function clearMealPhoto() {
  // 编辑态下允许清空新图回退到原图；新建态下清空即无图，提交按钮会禁用
  if (mealFileRaw.value) {
    URL.revokeObjectURL(mealPickedUrl.value)
    mealFileRaw.value = null
    mealPickedUrl.value = ''
  } else {
    mealExistingUrl.value = ''
  }
}
async function submitMeal() {
  if (!mealForm.value.member_id) { ElMessage.warning('请选家人'); return }
  if (!mealPhotoShown.value) { ElMessage.warning('请选照片'); return }
  mealSubmitting.value = true
  try {
    const payload = {
      member_id: mealForm.value.member_id,
      meal_type: mealForm.value.meal_type,
      taken_at: mealForm.value.taken_at || '',
      note: mealForm.value.note || '',
      photo: mealFileRaw.value || null,
    }
    if (mealEditingId.value) {
      await store.editMeal(mealEditingId.value, payload)
    } else {
      await store.addMeal(payload)
    }
    await loadAll()
    ElMessage.success(mealEditingId.value ? '已保存' : '已上传')
    showMealDialog.value = false
  } catch (e) {
    const msg = e?.msg || e?.detail?.msg || e?.message || '保存失败'
    ElMessage.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  } finally {
    mealSubmitting.value = false
  }
}

// ============================== 大图预览 ==============================
const previewMeal = ref(null)
const lightboxEl = ref(null)
function openPreview(m) {
  previewMeal.value = m
  nextTick(() => lightboxEl.value?.focus())
}
function closePreview() {
  previewMeal.value = null
}
function editFromPreview() {
  const m = previewMeal.value
  closePreview()
  if (m) openMealEdit(m)
}
async function deleteFromPreview() {
  const m = previewMeal.value
  closePreview()
  if (m) await onDeleteMeal(m)
}
function onLightboxKey(e) {
  if (e.key === 'Escape' && previewMeal.value) closePreview()
}
watch(previewMeal, (v) => {
  if (v) window.addEventListener('keydown', onLightboxKey)
  else window.removeEventListener('keydown', onLightboxKey)
})

// ============================== 删除 ==============================
async function onDeleteWeight(w) {
  try { await ElMessageBox.confirm(`确认删除 ${w.member_name} 的 ${w.weight_kg}kg？`, '提示', { type: 'warning' }) } catch { return }
  try { await store.removeWeight(w.id); await loadAll(); ElMessage.success('已删除') } catch { /* 拦截器提示 */ }
}
async function onDeleteMeal(m) {
  try { await ElMessageBox.confirm('确认删除这条美食记忆？照片会一并删除。', '提示', { type: 'warning' }) } catch { return }
  try { await store.removeMeal(m.id); await loadAll(); ElMessage.success('已删除') } catch { /* 拦截器提示 */ }
}

// ============================== 家人管理 ==============================
const showMembersDialog = ref(false)
function openMembersDialog() { showMembersDialog.value = true }
async function editMemberInline(m) {
  let newName = ''
  try {
    const { value } = await ElMessageBox.prompt(`把「${m.display_name}」的昵称改成`, '改昵称', {
      inputValue: m.display_name,
      inputValidator: (v) => (v && v.trim() ? true : '昵称不能为空'),
    })
    newName = value.trim()
  } catch { return }
  try {
    await store.editMember(m.id, { display_name: newName })
    // 后端把「家人名」写的就是账号昵称（唯一真源），改到自己时同步刷新顶栏
    await auth.fetchUser()
    ElMessage.success('已更新')
  } catch { /* 拦截器提示 */ }
}
async function onDeleteMember(m) {
  try { await ElMessageBox.confirm(`确认删除家人「${m.display_name}」？其体重/美食记录一并保留（仍归属于原 member_id）。`, '提示', { type: 'warning' }) } catch { return }
  try { await store.removeMember(m.id); ElMessage.success('已删除') } catch { /* 拦截器提示 */ }
}

// ============================== 初始化 ==============================
// 不带 member_id 拉全量：列表在客户端按人切片，汇总才能拿到全家口径
async function loadAll() {
  await store.fetchMembers()
  const params = {}
  if (filterRange.value !== 'all') {
    const days = Number(filterRange.value)
    const from = new Date(Date.now() - days * 86400000).toISOString().slice(0, 10)
    params.from_date = from
  }
  await Promise.all([store.fetchWeight(params), store.fetchMeals(params)])
}
onMounted(loadAll)
watch(filterRange, loadAll)
// 两个路由复用同一组件实例：切菜单时重置筛选，避免「在体重页筛了某人，切到美食页还带着」
watch(isMeals, () => {
  filterMember.value = ''
  closePreview()
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onLightboxKey)
  if (mealPickedUrl.value) URL.revokeObjectURL(mealPickedUrl.value)
})
</script>

<style scoped>
.life-tb {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
}
.life-tb-range { flex: 0 0 auto; }

/* 人员标签 + 家人汇总 */
.life-members {
  background: var(--ls-paper);
  border: 1px solid var(--ls-line);
  border-radius: var(--ls-radius, 12px);
  padding: 18px 20px;
  box-shadow: var(--ls-shadow, 0 1px 2px rgba(0,0,0,.04));
  margin-bottom: 18px;
}
.life-members-head {
  display: flex; justify-content: space-between; align-items: baseline;
  gap: 12px; flex-wrap: wrap;
  margin-bottom: 12px; padding-bottom: 8px;
  border-bottom: 1px solid var(--ls-line);
}
.life-members-head h3 { margin: 0; font-size: 15px; color: var(--lj-text); letter-spacing: .04em; }

.life-mtags { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.life-mtag {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 6px 13px; border-radius: 999px;
  border: 1px solid var(--ls-line); background: transparent;
  color: var(--lj-text-2); cursor: pointer;
  font-family: inherit; font-size: 13px;
  transition: border-color var(--motion-fast, .12s) var(--ease-standard, ease),
              background var(--motion-fast, .12s) var(--ease-standard, ease),
              color var(--motion-fast, .12s) var(--ease-standard, ease);
}
.life-mtag:hover { border-color: var(--lj-text-3); color: var(--lj-text); }
.life-mtag.on {
  border-color: var(--yq-gold, #c7a96b);
  color: var(--yq-gold, #c7a96b);
  background: rgba(199,169,107,.14);
}
.life-mtag-avatar { font-size: 15px; line-height: 1; }
.life-mtag-name { font-weight: 600; }
.life-mtag-meta { font-size: 11.5px; color: var(--lj-text-3); font-variant-numeric: tabular-nums; }
.life-mtag.on .life-mtag-meta { color: inherit; }

.life-sum-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; }
/* 窄屏改单列时不能写裸 1fr：1fr = minmax(auto, 1fr)，轨道最小宽度会被
   nowrap 表格的 min-content 顶住，卡片被撑出视口（375px 下溢出 30px）。
   必须显式 minmax(0, 1fr)，让轨道能收缩、把溢出交给 .life-sum-table-wrap 横向滚动。 */
@media (max-width: 1000px) { .life-sum-grid { grid-template-columns: minmax(0, 1fr); } }
/* 拆成单模块后汇总只有一张卡，两列会留一块空洞 */
.life-sum-grid > :only-child { grid-column: 1 / -1; }
.life-sum-card {
  border: 1px solid var(--ls-line);
  border-radius: 10px;
  padding: 12px 14px;
  background: var(--ls-paper-2, rgba(127,127,127,.03));
  min-width: 0;
}
.life-sum-title { font-size: 13px; color: var(--lj-text-2); letter-spacing: .04em; margin-bottom: 8px; }
/* 单元格是 nowrap，窄屏（375px）下 5~6 列必然超过卡片宽度，
   不给横向滚动容器就会把整个页面撑出横向滚动条 */
.life-sum-table-wrap { overflow-x: auto; }
.life-sum-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.life-sum-table th {
  text-align: right; padding: 6px 8px;
  font-size: 11.5px; font-weight: 600; color: var(--lj-text-3);
  border-bottom: 1px solid var(--ls-line); white-space: nowrap;
}
.life-sum-table th.c-name, .life-sum-table td.c-name { text-align: left; }
/* 拆成单模块后汇总表占满整行，不约束列宽的话数字会被摊到整屏；
   给数值列定宽、让「成员」列吃掉余量，数字就聚到右侧了 */
.life-sum-table th:not(.c-name), .life-sum-table td:not(.c-name) { width: 88px; }
.life-sum-table td {
  padding: 7px 8px; text-align: right;
  border-bottom: 1px dashed var(--ls-line);
  white-space: nowrap; font-variant-numeric: tabular-nums;
  color: var(--lj-text-2);
}
.life-sum-table tr:last-child td { border-bottom: none; }
.life-sum-row { cursor: pointer; transition: background var(--motion-fast, .12s) var(--ease-standard, ease); }
.life-sum-row:hover { background: rgba(127,168,163,.06); }
.life-sum-row.on { background: rgba(199,169,107,.12); }
.life-sum-avatar { margin-right: 6px; }
.life-sum-strong { font-weight: 600; color: var(--lj-text); }
.life-sum-table td.up { color: var(--lj-cinnabar, #c27053); }
.life-sum-table td.down { color: var(--lj-seal, #7fa8a3); }
.life-sum-empty { padding: 18px 4px; text-align: center; font-size: 12.5px; color: var(--lj-text-3); }

.life-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 18px;
  margin-top: 4px;
}
@media (max-width: 1000px) {
  .life-layout { grid-template-columns: minmax(0, 1fr); }
}
/* 美食记忆只有一块内容，铺满整行 */
.life-layout-single { grid-template-columns: minmax(0, 1fr); }

.life-col {
  background: var(--ls-paper);
  border: 1px solid var(--ls-line);
  border-radius: var(--ls-radius, 12px);
  padding: 18px 20px;
  box-shadow: var(--ls-shadow, 0 1px 2px rgba(0,0,0,.04));
  min-width: 0;
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
  position: relative;
}
.wt-chart {
  width: 100%; height: 220px;
  display: block;
  cursor: crosshair;
}
.wt-chart .wt-cross {
  stroke: var(--lj-text-3);
  stroke-width: 1;
  stroke-dasharray: 3 3;
  opacity: .5;
}
.wt-chart .wt-hover-dot {
  filter: drop-shadow(0 0 4px rgba(0, 0, 0, .35));
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

/* 美食记忆 */
.meal-hint {
  margin: 0 0 14px; font-size: 12px; line-height: 1.7;
  color: var(--lj-text-3);
}
.meal-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
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
/* 图区是可点击的预览入口，去掉 button 默认样式 */
.meal-img-wrap {
  position: relative; display: block; width: 100%;
  aspect-ratio: 1 / 1; overflow: hidden;
  padding: 0; border: none; background: none; cursor: zoom-in;
}
.meal-img { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform var(--motion-med) var(--ease-standard); }
.meal-card:hover .meal-img { transform: scale(1.04); }
.meal-type-tag {
  position: absolute; top: 8px; left: 8px;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 11px; font-weight: 600;
  backdrop-filter: blur(6px);
  background: rgba(0, 0, 0, .45);
  color: #fff;
}
.meal-type-tag.mt-feast  { background: rgba(199, 169, 107, .9); }
.meal-type-tag.mt-memory { background: rgba(217, 119, 6, .88); }
.meal-type-tag.mt-travel { background: rgba(91, 106, 224, .88); }
.meal-type-tag.mt-home   { background: rgba(127, 168, 163, .9); }
/* v2.41 之前的三餐老数据：中性灰，不抢戏 */
.meal-type-tag.mt-legacy { background: rgba(90, 100, 110, .8); }
.meal-zoom {
  position: absolute; right: 8px; bottom: 8px;
  width: 26px; height: 26px; border-radius: 50%;
  display: grid; place-items: center;
  font-size: 12px;
  background: rgba(0, 0, 0, .42);
  color: #fff;
  opacity: 0; transition: opacity var(--motion-fast, .12s) var(--ease-standard, ease);
}
.meal-card:hover .meal-zoom, .meal-img-wrap:focus-visible .meal-zoom { opacity: 1; }
.meal-info { padding: 8px 10px 8px; }
.meal-meta {
  display: flex; align-items: center; gap: 5px;
  font-size: 11.5px; color: var(--lj-text-2);
}
.meal-avatar { font-size: 14px; }
.meal-name { font-weight: 600; color: var(--lj-text); }
.meal-date { margin-left: auto; font-size: 10.5px; color: var(--lj-text-3); font-variant-numeric: tabular-nums; }
.meal-note { margin: 4px 0 0; font-size: 11.5px; color: var(--lj-text-3); line-height: 1.55; }
.meal-ops {
  display: flex; gap: 6px; margin-top: 8px;
  padding-top: 7px; border-top: 1px dashed var(--ls-line);
}
.meal-op {
  flex: 1; padding: 4px 0;
  border: 1px solid var(--ls-line); border-radius: 7px;
  background: transparent; color: var(--lj-text-2);
  font-family: inherit; font-size: 12px; cursor: pointer;
  transition: border-color var(--motion-fast, .12s) var(--ease-standard, ease),
              color var(--motion-fast, .12s) var(--ease-standard, ease),
              background var(--motion-fast, .12s) var(--ease-standard, ease);
}
.meal-op:hover { border-color: var(--yq-gold, #c7a96b); color: var(--yq-gold, #c7a96b); background: rgba(199,169,107,.1); }
.meal-op.danger:hover { border-color: var(--lj-cinnabar, #c27053); color: var(--lj-cinnabar, #c27053); background: rgba(194,112,83,.1); }

/* 大图预览灯箱 */
.meal-lb {
  position: fixed; inset: 0; z-index: 2600;
  display: grid; place-items: center;
  padding: 24px;
  background: rgba(12, 16, 20, .72);
  backdrop-filter: blur(10px);
  animation: mealLbIn .18s cubic-bezier(.4,.1,.2,1);
  outline: none;
}
@keyframes mealLbIn { from { opacity: 0 } to { opacity: 1 } }
.meal-lb-box {
  position: relative;
  margin: 0; max-width: min(92vw, 880px); max-height: 90vh;
  display: flex; flex-direction: column;
  border-radius: 14px; overflow: hidden;
  border: 1px solid rgba(255,255,255,.16);
  background: rgba(20, 24, 28, .9);
  box-shadow: 0 24px 60px rgba(0,0,0,.5);
}
.meal-lb-img {
  max-width: 100%; max-height: 62vh;
  object-fit: contain; display: block; background: #0d1013;
}
.meal-lb-bar { padding: 12px 16px 14px; }
.meal-lb-meta { display: flex; align-items: center; gap: 9px; flex-wrap: wrap; }
.meal-lb-meta .meal-type-tag { position: static; }
.meal-lb-name { font-size: 13px; color: #f2eee4; font-weight: 600; }
.meal-lb-date { font-size: 11.5px; color: rgba(242,238,228,.62); font-variant-numeric: tabular-nums; }
.meal-lb-note { margin: 7px 0 0; font-size: 13px; line-height: 1.6; color: rgba(242,238,228,.86); }
.meal-lb-ops { display: flex; gap: 8px; margin-top: 12px; }
.meal-lb-btn {
  padding: 6px 16px; border-radius: 8px; cursor: pointer;
  border: 1px solid rgba(255,255,255,.22);
  background: rgba(255,255,255,.07); color: #f2eee4;
  font-family: inherit; font-size: 12.5px;
  transition: border-color .16s, background .16s, color .16s;
}
.meal-lb-btn:hover { border-color: var(--yq-gold, #c7a96b); color: var(--yq-gold, #c7a96b); }
.meal-lb-btn.danger:hover { border-color: #d98564; color: #d98564; }
.meal-lb-x {
  position: absolute; top: 10px; right: 10px;
  width: 30px; height: 30px; border-radius: 50%;
  border: 1px solid rgba(255,255,255,.22);
  background: rgba(0,0,0,.45); color: #fff;
  font-size: 14px; line-height: 1; cursor: pointer;
}
.meal-lb-x:hover { border-color: var(--yq-gold, #c7a96b); color: var(--yq-gold, #c7a96b); }

/* 骨架 */
.life-skel { padding: 4px 0; }
.life-skel-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px; }

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
/* 记一顿：拍照 / 相册按钮与预览（v2.40.24） */
.meal-photo-row { display: flex; gap: 10px; align-items: flex-start; flex-wrap: wrap; }
.meal-photo-btn {
  padding: 7px 14px; border-radius: 8px; font-size: 13px; cursor: pointer;
  border: 1px solid var(--lj-line, rgba(0,0,0,.14)); background: var(--lj-surface, #fff); color: var(--lj-text-2, #45505b);
  font-family: inherit; white-space: nowrap;
}
.meal-photo-btn:hover { border-color: var(--yq-gold, #c7a96b); color: var(--yq-gold, #c7a96b); }
.meal-photo-preview { position: relative; width: 72px; height: 72px; border-radius: 10px; overflow: hidden; }
.meal-photo-preview img { width: 100%; height: 100%; object-fit: cover; }
.meal-photo-del {
  position: absolute; right: 2px; top: 2px; width: 20px; height: 20px; border-radius: 50%;
  border: none; background: rgba(0,0,0,.55); color: #fff; cursor: pointer; font-size: 13px; line-height: 1;
}
</style>