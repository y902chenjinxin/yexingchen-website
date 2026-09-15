<template>
  <div class="ct-page">
    <div class="ct-inner">
      <header class="ct-head">
        <BackButton class="ct-back" />
        <div class="ct-titles">
          <h1 class="ct-title">家人通讯录</h1>
          <p class="ct-sub">生日 · 住址 · 电话，一处记全，到期自动提醒</p>
        </div>
        <div class="ct-head-right">
          <div class="ct-seg">
            <button class="ct-seg-btn" :class="{ on: view === 'list' }" @click="view = 'list'">列表</button>
            <button class="ct-seg-btn" :class="{ on: view === 'calendar' }" @click="view = 'calendar'">日历</button>
          </div>
          <button class="ct-btn primary" @click="openCreate">＋ 新增</button>
        </div>
      </header>

      <div class="ct-toolbar">
        <input v-model="keyword" class="ct-input" placeholder="搜索姓名 / 关系 / 电话 / 住址" spellcheck="false" />
        <select v-model="relationFilter" class="ct-input ct-select">
          <option value="">全部关系</option>
          <option v-for="r in usedRelations" :key="r" :value="r">{{ r }}</option>
        </select>
        <span class="ct-count">共 {{ filtered.length }} 位{{ upcomingCount ? ` · 近 30 天生日 ${upcomingCount} 位` : '' }}</span>
      </div>

      <!-- ============ 列表视图 ============ -->
      <section v-if="view === 'list'" class="ct-list">
        <article v-for="c in filtered" :key="c.id" class="ct-card glass">
          <div class="ct-card-main">
            <div class="ct-avatar" :class="{ pin: c.is_pinned }">{{ (c.name || '?').slice(0, 1) }}</div>
            <div class="ct-card-text">
              <div class="ct-name-row">
                <span class="ct-name">{{ c.name }}</span>
                <span v-if="c.relation" class="ct-rel">{{ c.relation }}</span>
                <span v-if="c.is_pinned" class="ct-pin">置顶</span>
                <span v-if="c.days_to_birthday !== null" class="ct-bday" :class="bdayCls(c.days_to_birthday)">
                  {{ bdayLabel(c.days_to_birthday) }}
                </span>
              </div>
              <div class="ct-meta">
                <span v-if="c.birthday">{{ bdayText(c) }}{{ c.age ? ` · ${c.age} 岁` : '' }}</span>
                <span v-if="c.phone">
                  电话 <a class="ct-tel" :href="`tel:${c.phone}`">{{ c.phone }}</a>
                </span>
                <span v-if="c.address">住址 {{ c.address }}</span>
              </div>
              <p v-if="c.notes" class="ct-notes">{{ c.notes }}</p>
            </div>
          </div>
          <div class="ct-card-actions">
            <button class="ct-btn ghost tiny" @click="togglePin(c)">{{ c.is_pinned ? '取消置顶' : '置顶' }}</button>
            <button class="ct-btn ghost tiny" @click="openEdit(c)">编辑</button>
            <button class="ct-btn ghost tiny danger" @click="remove(c)">删除</button>
          </div>
        </article>
        <p v-if="!loading && !filtered.length" class="ct-empty">
          还没有联系人。点右上角「新增」，把家里人的生日和电话记进来，临近生日会自动生成待办。
        </p>
        <p v-else-if="loading" class="ct-empty">加载中…</p>
      </section>

      <!-- ============ 日历视图 ============ -->
      <section v-else class="ct-card glass ct-cal-card">
        <div class="ct-cal-head">
          <button class="ct-btn ghost tiny" @click="shiftMonth(-1)">‹ 上月</button>
          <span class="ct-cal-title">{{ calYear }} 年 {{ calMonth + 1 }} 月</span>
          <button class="ct-btn ghost tiny" @click="shiftMonth(1)">下月 ›</button>
          <button class="ct-btn ghost tiny" @click="resetMonth">回到本月</button>
        </div>
        <div class="ct-cal-week">
          <span v-for="w in WEEK" :key="w">{{ w }}</span>
        </div>
        <div class="ct-cal">
          <div v-for="cell in calCells" :key="cell.key" class="ct-day" :class="{ blank: cell.blank, today: cell.isToday }">
            <template v-if="!cell.blank">
              <span class="ct-day-n">{{ cell.day }}</span>
              <ul v-if="cell.people.length" class="ct-day-list">
                <li v-for="p in cell.people.slice(0, 3)" :key="p.id" class="ct-day-item" :title="`${p.name} ${bdayText(p)}`"
                    @click="openEdit(p)">
                  {{ p.name }}<span v-if="p.birthday_type === 'lunar'" class="ct-day-lunar">农</span><span v-if="p.age" class="ct-day-age">{{ p.age }}</span>
                </li>
                <li v-if="cell.people.length > 3" class="ct-day-more">+{{ cell.people.length - 3 }}</li>
              </ul>
            </template>
          </div>
        </div>
        <p class="ct-cal-tip">点日历上的名字可直接编辑。农历生日已换算成对应公历日期后落入日历（标「农」角标），换算以上面列表里的下次生日为准。</p>
      </section>
    </div>

    <!-- ============ 新增 / 编辑弹窗 ============ -->
    <el-dialog v-model="dialog" :title="form.id ? '编辑联系人' : '新增联系人'" width="560px">
      <el-form :model="form" label-width="76px">
        <el-form-item label="姓名">
          <el-input v-model="form.name" placeholder="如 奶奶" maxlength="60" />
        </el-form-item>
        <el-form-item label="关系">
          <el-select v-model="form.relation" filterable allow-create default-first-option style="width:100%"
                     placeholder="选择或直接输入，如 姑姑">
            <el-option v-for="r in RELATION_OPTIONS" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
        <el-form-item label="生日">
          <div class="ct-bday-row">
            <el-select v-model="birthMonth" placeholder="月" clearable style="width:100px">
              <el-option v-for="m in 12" :key="m" :label="`${m} 月`" :value="m" />
            </el-select>
            <el-select v-model="birthDay" placeholder="日" clearable style="width:100px">
              <el-option v-for="d in maxBirthDay" :key="d" :label="`${d} 日`" :value="d" />
            </el-select>
            <el-select v-model="form.birthday_type" style="width:110px" @change="onBdayTypeChange">
              <el-option label="公历" value="solar" />
              <el-option label="农历" value="lunar" />
            </el-select>
            <el-checkbox
              v-if="form.birthday_type === 'lunar'"
              v-model="form.lunar_leap"
              :true-value="1"
              :false-value="0"
              class="ct-leap"
            >闰月</el-checkbox>
          </div>
          <div class="ct-form-tip">
            <template v-if="form.birthday_type === 'lunar'">
              按农历填报（家里长辈的生日多是农历）。系统会自动换算成公历并生成提醒；
              只有闰四月、闰二月这类年份才勾「闰月」，没有对应闰月的年份自动按普通月过。
            </template>
            <template v-else>只记得月日也可以，年份留空即可（年份仅用于显示年龄）</template>
          </div>
        </el-form-item>
        <el-form-item label="出生年">
          <el-input-number v-model="form.birth_year" :min="1900" :max="2100" :controls="false"
                           :placeholder="form.birthday_type === 'lunar' ? '可选，填农历年' : '可选，如 1950'" style="width:180px" />
          <span v-if="form.birthday_type === 'lunar'" class="ct-inline-tip">农历生日请填农历年，年龄才准（腊月生日会差一岁）</span>
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.phone" placeholder="手机号或座机" maxlength="40" />
        </el-form-item>
        <el-form-item label="住址">
          <el-input v-model="form.address" placeholder="省市区 + 详细地址" maxlength="255" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="form.tags" placeholder="逗号分隔，如 老家,常联系" maxlength="255" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" placeholder="忌口、喜好、要带的东西…" />
        </el-form-item>
        <el-form-item label="置顶">
          <el-switch v-model="form.is_pinned" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :disabled="!form.name.trim() || saving" @click="submit">
          {{ saving ? '保存中…' : '保存' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import BackButton from '@/components/BackButton.vue'
import { contactsApi, RELATION_OPTIONS } from '@/api/family'

const WEEK = ['日', '一', '二', '三', '四', '五', '六']

const list = ref([])
const loading = ref(true)
const keyword = ref('')
const relationFilter = ref('')
const view = ref('list')

const dialog = ref(false)
const saving = ref(false)
const birthMonth = ref(null)
const birthDay = ref(null)
const form = reactive(emptyForm())

// 农历没有 31 日，日下拉要跟着历法收窄，否则会填出永远存不进的日期
const maxBirthDay = computed(() => (form.birthday_type === 'lunar' ? 30 : 31))

function emptyForm() {
  return {
    id: null, name: '', relation: '', phone: '', address: '',
    birthday_type: 'solar', lunar_leap: 0, birth_year: null, tags: '', notes: '', is_pinned: 0,
  }
}

function onBdayTypeChange() {
  // 从公历切到农历时，原本选的 31 日不存在了 → 清掉，避免提交被后端拒
  if (form.birthday_type === 'lunar' && birthDay.value > 30) birthDay.value = null
  if (form.birthday_type === 'solar') form.lunar_leap = 0
}

/** 生日展示文案：农历显示中文月日 + 换算后的公历日期 */
function bdayText(c) {
  if (c.birthday_type === 'lunar' && c.lunar_text) {
    return c.next_birthday ? `农历${c.lunar_text} → ${c.next_birthday}` : `农历${c.lunar_text}`
  }
  return `生日 ${c.birthday}`
}

const filtered = computed(() => {
  const q = keyword.value.trim().toLowerCase()
  return list.value.filter((c) => {
    if (relationFilter.value && c.relation !== relationFilter.value) return false
    if (!q) return true
    return [c.name, c.relation, c.phone, c.address, c.tags]
      .some((v) => (v || '').toLowerCase().includes(q))
  })
})

const usedRelations = computed(() =>
  [...new Set(list.value.map((c) => c.relation).filter(Boolean))].sort())

const upcomingCount = computed(() =>
  list.value.filter((c) => c.days_to_birthday !== null && c.days_to_birthday <= 30).length)

function bdayLabel(d) {
  if (d === 0) return '今天生日'
  if (d <= 30) return `${d} 天后生日`
  return `还有 ${d} 天`
}
function bdayCls(d) {
  if (d === 0) return 'is-today'
  if (d <= 7) return 'is-soon'
  if (d <= 30) return 'is-near'
  return ''
}

/* ---------------- 日历 ---------------- */
const now = new Date()
const calYear = ref(now.getFullYear())
const calMonth = ref(now.getMonth())

const byMonthDay = computed(() => {
  const map = {}
  for (const c of list.value) {
    if (!c.birthday) continue
    // 农历生日要落在**换算后的公历**那一格：直接拿农历月日去排公历日历会错位近一个月
    const key = c.next_birthday ? c.next_birthday.slice(5) : c.birthday
    ;(map[key] ||= []).push(c)
  }
  return map
})

const calCells = computed(() => {
  const y = calYear.value
  const m = calMonth.value
  const pad = new Date(y, m, 1).getDay()
  const days = new Date(y, m + 1, 0).getDate()
  const todayStr = localDate(new Date())
  const cells = []
  for (let i = 0; i < pad; i++) cells.push({ blank: true, key: `p${i}` })
  for (let d = 1; d <= days; d++) {
    const mm = String(m + 1).padStart(2, '0')
    const dd = String(d).padStart(2, '0')
    const iso = `${y}-${mm}-${dd}`
    cells.push({
      blank: false,
      key: iso,
      day: d,
      isToday: iso === todayStr,
      people: byMonthDay.value[`${mm}-${dd}`] || [],
    })
  }
  return cells
})

function localDate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function shiftMonth(delta) {
  let m = calMonth.value + delta
  let y = calYear.value
  if (m < 0) { m = 11; y -= 1 }
  if (m > 11) { m = 0; y += 1 }
  calMonth.value = m
  calYear.value = y
}
function resetMonth() {
  const t = new Date()
  calYear.value = t.getFullYear()
  calMonth.value = t.getMonth()
}

/* ---------------- CRUD ---------------- */
async function reload() {
  loading.value = true
  try {
    const res = await contactsApi.list()
    list.value = res.data?.list || []
  } catch { /* 拦截器已提示 */ }
  finally { loading.value = false }
}

function openCreate() {
  Object.assign(form, emptyForm())
  birthMonth.value = null
  birthDay.value = null
  dialog.value = true
}

function openEdit(c) {
  Object.assign(form, {
    id: c.id, name: c.name, relation: c.relation, phone: c.phone, address: c.address,
    birthday_type: c.birthday_type || 'solar', lunar_leap: c.lunar_leap || 0,
    birth_year: c.birth_year,
    tags: c.tags, notes: c.notes, is_pinned: c.is_pinned || 0,
  })
  if (c.birthday) {
    const [mm, dd] = c.birthday.split('-')
    birthMonth.value = Number(mm)
    birthDay.value = Number(dd)
  } else {
    birthMonth.value = null
    birthDay.value = null
  }
  dialog.value = true
}

function birthdayValue() {
  if (!birthMonth.value && !birthDay.value) return ''
  if (!birthMonth.value || !birthDay.value) return null // 只填一半：提示后不提交
  return `${String(birthMonth.value).padStart(2, '0')}-${String(birthDay.value).padStart(2, '0')}`
}

async function submit() {
  const bday = birthdayValue()
  if (bday === null) {
    ElMessage.warning('生日请把月和日都选上，或全部留空')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      relation: form.relation || '',
      phone: form.phone || '',
      address: form.address || '',
      birthday: bday,
      birth_year: form.birth_year || null,
      birthday_type: form.birthday_type,
      lunar_leap: form.birthday_type === 'lunar' ? (form.lunar_leap ? 1 : 0) : 0,
      tags: form.tags || '',
      notes: form.notes || '',
      is_pinned: form.is_pinned ? 1 : 0,
    }
    if (form.id) await contactsApi.update(form.id, payload)
    else await contactsApi.create(payload)
    ElMessage.success(form.id ? '已保存' : '已添加')
    dialog.value = false
    await reload()
  } catch { /* 拦截器已提示 */ }
  finally { saving.value = false }
}

async function togglePin(c) {
  try {
    await contactsApi.update(c.id, { is_pinned: c.is_pinned ? 0 : 1 })
    await reload()
  } catch { /* 拦截器已提示 */ }
}

async function remove(c) {
  try {
    await ElMessageBox.confirm(`确认删除联系人「${c.name}」？可在回收站恢复。`, '提示', { type: 'warning' })
  } catch { return }
  try {
    await contactsApi.remove(c.id)
    ElMessage.success('已删除')
    await reload()
  } catch { /* 拦截器已提示 */ }
}

onMounted(reload)
</script>

<style scoped>
.ct-page { min-height: 100vh; }
.ct-inner { max-width: 1080px; margin: 0 auto; padding: 84px 20px 40px; }

.ct-head { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; flex-wrap: wrap; }
.ct-back { margin-right: 2px; }
.ct-titles { flex: 1; min-width: 180px; }
.ct-title { margin: 0; font-size: 22px; letter-spacing: .1em; color: var(--lj-text); }
.ct-sub { margin: 2px 0 0; font-size: 12px; color: var(--lj-text-2); letter-spacing: .08em; }
.ct-head-right { display: flex; gap: 8px; align-items: center; margin-left: auto; }

.ct-seg { display: flex; border: 1px solid var(--lj-line); border-radius: 10px; overflow: hidden; }
.ct-seg-btn { padding: 7px 14px; font-size: 13px; cursor: pointer; background: transparent;
  color: var(--lj-text-2); border: none; transition: all .2s; }
.ct-seg-btn.on { background: var(--lj-seal-soft); color: var(--lj-seal); }

.ct-btn { border-radius: 9px; padding: 8px 16px; font-size: 13px; border: 1px solid transparent;
  cursor: pointer; transition: all .2s; font-family: inherit; }
.ct-btn.primary { background: linear-gradient(135deg, rgba(199,169,107,.85), rgba(127,168,163,.85)); color: #0B0F14; }
.ct-btn.ghost { background: transparent; color: var(--lj-text); border-color: var(--lj-line); }
.ct-btn.ghost:hover { border-color: var(--lj-line-strong); color: var(--lj-seal); }
.ct-btn.tiny { padding: 4px 10px; font-size: 12px; }
.ct-btn.danger { color: var(--pnl-up); }

.ct-toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 14px; flex-wrap: wrap; }
.ct-input { background: rgba(74,95,99,.08); border: 1px solid var(--lj-line); color: var(--lj-text);
  border-radius: 8px; padding: 8px 11px; font-size: 13px; font-family: inherit; min-width: 220px; flex: 1 1 220px; }
.ct-input:focus { outline: none; border-color: var(--lj-seal); }
.ct-select { flex: 0 0 150px; min-width: 150px; }
.ct-count { font-size: 12px; color: var(--lj-text-3); }

.ct-list { display: flex; flex-direction: column; gap: 10px; }
.ct-card { border-radius: 16px; padding: 14px 18px; display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.ct-card-main { display: flex; gap: 14px; flex: 1; min-width: 260px; align-items: flex-start; }
.ct-avatar { width: 42px; height: 42px; flex: none; border-radius: 12px; display: flex;
  align-items: center; justify-content: center; font-family: var(--font-serif); font-size: 18px;
  background: rgba(127,168,163,.16); color: var(--lj-dai); border: 1px solid var(--lj-line); }
.ct-avatar.pin { background: var(--lj-seal-soft); color: var(--lj-seal); border-color: var(--lj-seal); }
.ct-card-text { flex: 1; min-width: 0; }
.ct-name-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ct-name { font-size: 16px; font-weight: 600; color: var(--lj-text); }
.ct-rel { font-size: 12px; color: var(--lj-text-2); padding: 1px 8px; border-radius: 999px;
  border: 1px solid var(--lj-line); }
.ct-pin { font-size: 11px; color: var(--lj-seal); padding: 1px 7px; border-radius: 999px;
  background: var(--lj-seal-soft); }
.ct-bday { font-size: 11px; padding: 1px 8px; border-radius: 999px; border: 1px solid var(--lj-line);
  color: var(--lj-text-2); }
.ct-bday.is-near { color: var(--lj-ochre); border-color: var(--lj-ochre); }
.ct-bday.is-soon { color: var(--lj-seal); border-color: var(--lj-seal); background: var(--lj-seal-soft); }
.ct-bday.is-today { color: #0B0F14; background: var(--lj-seal); border-color: var(--lj-seal); font-weight: 600; }
.ct-meta { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 6px; font-size: 12px; color: var(--lj-text-2); }
.ct-tel { color: var(--lj-dai); text-decoration: none; }
.ct-tel:hover { text-decoration: underline; }
.ct-notes { margin: 6px 0 0; font-size: 12px; color: var(--lj-text-3); line-height: 1.6; }
.ct-card-actions { display: flex; gap: 6px; margin-left: auto; }

.ct-empty { text-align: center; padding: 46px 20px; font-size: 13px; line-height: 1.9; color: var(--lj-text-3); }

/* 日历 */
.ct-cal-card { border-radius: 16px; padding: 16px 20px; }
.ct-cal-head { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.ct-cal-title { font-size: 15px; letter-spacing: .08em; color: var(--lj-text); flex: 1; text-align: center; }
.ct-cal-week { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; margin-bottom: 6px; }
.ct-cal-week span { text-align: center; font-size: 11px; color: var(--lj-text-3); }
.ct-cal { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; }
.ct-day { min-height: 74px; border-radius: 10px; padding: 5px 6px; box-sizing: border-box;
  border: 1px solid transparent; background: rgba(74,95,99,.05); overflow: hidden; }
.ct-day.blank { background: transparent; }
.ct-day.today { box-shadow: 0 0 0 1px var(--lj-seal) inset; }
.ct-day-n { font-size: 11px; color: var(--lj-text-3); font-variant-numeric: tabular-nums; }
.ct-day-list { list-style: none; margin: 3px 0 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
.ct-day-item { font-size: 11px; color: var(--lj-text); background: var(--lj-seal-soft); border-radius: 4px;
  padding: 1px 4px; cursor: pointer; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ct-day-item:hover { background: var(--lj-seal); color: #fff; }
.ct-day-age { font-size: 10px; opacity: .75; margin-left: 3px; }
.ct-day-more { font-size: 10px; color: var(--lj-text-3); }
.ct-cal-tip { margin: 12px 0 0; font-size: 11px; line-height: 1.7; color: var(--lj-text-3); }

.ct-bday-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.ct-form-tip { font-size: 11px; color: var(--lj-text-3); line-height: 1.6; margin-top: 4px; }
.ct-leap { margin-left: 2px; }
.ct-inline-tip { margin-left: 10px; font-size: 11px; color: var(--lj-text-3); }
.ct-day-lunar { font-size: 9px; margin-left: 3px; padding: 0 3px; border-radius: 3px;
  background: var(--lj-ochre); color: #0B0F14; }

@media (max-width: 760px) {
  .ct-head-right { width: 100%; }
  .ct-btn.primary { margin-left: auto; }
  .ct-day { min-height: 58px; }
  .ct-card-actions { margin-left: 0; }
}
</style>
