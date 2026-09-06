<template>
  <div class="tv-page">
    <div class="lj-bg" aria-hidden="true">
      <div class="lj-paper-texture"></div>
      <div class="lj-wash w1"></div>
      <div class="lj-wash w2"></div>
    </div>

    <div class="tv-inner">
      <!-- 页头 -->
      <header class="tv-head">
        <div class="tv-head-left"><BackButton class="tv-back" /></div>
        <div class="tv-titles">
          <h1 class="tv-title">旅行足迹</h1>
          <p class="tv-sub">走遍山河，把到过的地方都点亮</p>
        </div>
        <div class="tv-head-right">
          <button v-if="canEdit" class="tv-btn ghost" :disabled="loading" @click="reload">{{ loading ? '加载中…' : '⟳ 刷新' }}</button>
          <button v-if="canEdit" class="tv-btn primary" @click="openCreate">{{ editorOpen ? '关闭' : '＋ 记下旅程' }}</button>
        </div>
      </header>

      <!-- KPI 汇总 -->
      <section class="tv-kpi">
        <div class="tv-kpi-card glass">
          <span class="tv-kpi-k">旅程</span>
          <span class="tv-kpi-v">{{ stats.travel_count }}</span>
          <span class="tv-kpi-s">段行程足迹</span>
        </div>
        <div class="tv-kpi-card glass">
          <span class="tv-kpi-k">省份</span>
          <span class="tv-kpi-v">{{ stats.province_count }}</span>
          <span class="tv-kpi-s">点亮的地图区域</span>
        </div>
        <div class="tv-kpi-card glass">
          <span class="tv-kpi-k">城市</span>
          <span class="tv-kpi-v">{{ stats.city_count }}</span>
          <span class="tv-kpi-s">到访的城市</span>
        </div>
      </section>

      <!-- 地图 + 时间线联动 -->
      <section class="tv-layout">
        <div class="tv-map glass">
          <TravelMap
            :points="mapPoints"
            :active-trip-id="activeTripId"
            :active-province="activeProvince"
          />
        </div>
        <div class="tv-slide glass">
          <TravelTimeline
            :travels="travels"
            :active-id="activeTripId"
            :can-edit="canEdit"
            @select="onSelectTrip"
          />
        </div>
      </section>

      <!-- 内联编辑器（无弹窗） -->
      <transition name="tv-panel">
        <section v-if="editorOpen" class="tv-edit-wrap">
          <TravelEditor :initial="editing" :busy="saving" @save="onSave" @cancel="closeEditor" />
        </section>
      </transition>

      <!-- 内联详情（无弹窗） -->
      <transition name="tv-panel">
        <section v-if="detail && !editorOpen" class="tv-detail-wrap">
          <TravelDetail :t="detail" :can-edit="canEdit && detail.user_id === meId" @close="detail=null" @edit="openEdit" @remove="onRemove" />
        </section>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import BackButton from '@/components/BackButton.vue'
import { useAuthStore } from '@/stores/auth'
import TravelMap from '@/components/travel/TravelMap.vue'
import TravelTimeline from '@/components/travel/TravelTimeline.vue'
import TravelEditor from '@/components/travel/TravelEditor.vue'
import TravelDetail from '@/components/travel/TravelDetail.vue'
import { listTravels, getStats, getTravel, createTravel, updateTravel, removeTravel } from '@/api/travels'

const auth = useAuthStore()
const canEdit = computed(() => !!auth.isLoggedIn)

const travels = ref([])
const loading = ref(true)
const stats = reactive({ travel_count: 0, province_count: 0, city_count: 0 })

const activeTripId = ref(null)
const activeProvince = ref(null)
const detail = ref(null)
const editorOpen = ref(false)
const editing = ref(null)
const saving = ref(false)

const meId = computed(() => auth.user?.id)

const mapPoints = computed(() => {
  const pts = []
  for (const t of travels.value) {
    ;(t.cities || []).forEach((c) => {
      pts.push({ tripId: t.id, tripTitle: t.title, seq: c.seq, city: c.city, province: c.province, lon: c.lon, lat: c.lat })
    })
  }
  return pts
})

async function reload() {
  loading.value = true
  try {
    const [lr, sr] = await Promise.all([listTravels(), getStats()])
    travels.value = lr?.data?.list || []
    Object.assign(stats, sr?.data || {})
    // 保持当前选中有效
    if (activeTripId.value && !travels.value.some((t) => t.id === activeTripId.value)) {
      activeTripId.value = null
      activeProvince.value = null
    }
  } catch (e) { /* 拦截器已提示 */ }
  finally { loading.value = false }
}

function onSelectTrip(id) {
  activeTripId.value = id
  const t = travels.value.find((x) => x.id === id)
  activeProvince.value = t?.cities?.[0]?.province || null
  if (id) loadDetail(id)
  else detail.value = null
}

async function loadDetail(id) {
  try {
    const r = await getTravel(id)
    detail.value = r?.data || null
  } catch (e) { detail.value = null }
}

function openCreate() {
  if (editorOpen.value && !editing.value) { closeEditor(); return }
  editing.value = null
  detail.value = null
  editorOpen.value = true
  activeTripId.value = null
  activeProvince.value = null
}
function openEdit(id) {
  editing.value = detail.value
  editorOpen.value = true
}
function closeEditor() { editorOpen.value = false; editing.value = null }

async function onSave(payload) {
  saving.value = true
  try {
    if (editing.value) {
      await updateTravel(editing.value.id, payload)
      ElMessage.success('已更新这趟旅程')
    } else {
      const r = await createTravel(payload)
      ElMessage.success('已记下这段旅程')
      editing.value = { id: r?.data?.id }
    }
    closeEditor()
    const keep = activeTripId.value
    await reload()
    if (keep) { activeTripId.value = keep; loadDetail(keep) }
  } catch (e) { /* handled */ }
  finally { saving.value = false }
}

async function onRemove(id) {
  try {
    await removeTravel(id)
    ElMessage.success('已删除')
    detail.value = null
    activeTripId.value = null
    activeProvince.value = null
    await reload()
  } catch (e) { /* handled */ }
}

onMounted(reload)
</script>

<style scoped>
.tv-page { min-height: 100vh; position: relative; }
.tv-inner { max-width: 1180px; margin: 0 auto; padding: 86px 20px 60px; position: relative; z-index: 1; }

.tv-head { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
.tv-head-left { flex: none; }
.tv-back { flex: none; }
.tv-titles { flex: 1; min-width: 0; }
.tv-title { margin: 0; font-size: 26px; letter-spacing: .12em; color: var(--lj-text); }
.tv-sub { margin: 4px 0 0; font-size: 13px; color: var(--lj-text-3); }
.tv-head-right { display: flex; gap: 10px; flex: none; }
.tv-btn { padding: 8px 18px; border-radius: 999px; border: 1px solid var(--lj-line-strong); font-size: 13.5px; cursor: pointer; transition: all .25s; }
.tv-btn.ghost { background: none; color: var(--lj-text-2); }
.tv-btn.ghost:hover { border-color: var(--lj-dai); color: var(--lj-dai); }
.tv-btn.primary { color: var(--lj-text); background: linear-gradient(135deg, rgba(127,168,163,.3), rgba(199,169,107,.18)); }
.tv-btn.primary:hover { filter: brightness(1.12); }

.tv-kpi { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 18px; }
.tv-kpi-card.glass, .tv-map.glass, .tv-slide.glass {
  background: var(--lj-glass); -webkit-backdrop-filter: var(--lj-glass-blur); backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line); box-shadow: var(--glass-highlight), var(--glass-shadow);
}
.tv-kpi-card { display: flex; flex-direction: column; gap: 4px; padding: 16px 18px; border-radius: 16px; }
.tv-kpi-k { font-size: 12px; letter-spacing: .1em; color: var(--lj-text-3); }
.tv-kpi-v { font-size: 30px; font-weight: 700; color: var(--lj-dai, #7FA8A3); letter-spacing: .02em; }
.tv-kpi-s { font-size: 12px; color: var(--lj-text-3); }

.tv-layout { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(280px, 1fr); gap: 16px; align-items: stretch; }
.tv-map { border-radius: 18px; padding: 16px; overflow: hidden; }
.tv-slide { border-radius: 18px; padding: 14px; height: 560px; overflow: hidden; }

.tv-edit-wrap, .tv-detail-wrap { margin-top: 18px; }
.tv-panel-enter-active, .tv-panel-leave-active { transition: all .3s ease; }
.tv-panel-enter-from, .tv-panel-leave-to { opacity: 0; transform: translateY(12px); }

@media (max-width: 820px) {
  .tv-layout { grid-template-columns: 1fr; }
  .tv-slide { height: 400px; }
  .tv-kpi { grid-template-columns: repeat(3, 1fr); }
}
</style>