<template>
  <div class="sb-page">
    <div class="sb-inner">
      <header class="sb-head">
        <BackButton class="sb-back" />
        <div class="sb-titles">
          <h1 class="sb-title">订阅账单</h1>
          <p class="sb-sub">会员 · 云服务 · 宽带 · 保险，到期前自动提醒</p>
        </div>
        <div class="sb-head-right">
          <button class="sb-btn primary" @click="openCreate">＋ 新增订阅</button>
        </div>
      </header>

      <!-- 汇总 -->
      <section class="sb-kpi">
        <div class="sb-kpi-card glass">
          <span class="sb-kpi-k">月均支出</span>
          <span class="sb-kpi-v">¥ {{ fmt(stats.monthly_total) }}</span>
          <span class="sb-kpi-s">按各周期折算</span>
        </div>
        <div class="sb-kpi-card glass">
          <span class="sb-kpi-k">年均支出</span>
          <span class="sb-kpi-v">¥ {{ fmt(stats.yearly_total) }}</span>
          <span class="sb-kpi-s">12 个月推算</span>
        </div>
        <div class="sb-kpi-card glass">
          <span class="sb-kpi-k">活跃订阅</span>
          <span class="sb-kpi-v">{{ stats.count_active || 0 }}</span>
          <span class="sb-kpi-s">共 {{ stats.count_total || 0 }} 条记录</span>
        </div>
        <div class="sb-kpi-card glass">
          <span class="sb-kpi-k">7 天内到期</span>
          <span class="sb-kpi-v" :class="{ warn: stats.due_soon_count > 0 }">{{ stats.due_soon_count || 0 }}</span>
          <span class="sb-kpi-s">{{ stats.overdue_count ? `其中逾期 ${stats.overdue_count} 条` : '暂无逾期' }}</span>
        </div>
      </section>

      <!-- 分类分布 + 周期分布 -->
      <section class="sb-grid">
        <div class="sb-panel glass">
          <div class="sb-panel-head">
            <span class="sb-panel-title">分类分布</span>
            <span class="sb-panel-sub">按月均折算</span>
          </div>
          <div v-if="categories.length" class="sb-donut">
            <DonutChart :data="categories" unit="类" aria-label="订阅分类月均支出占比" />
            <ul class="sb-legend">
              <li v-for="c in categories" :key="c.category" class="sb-leg">
                <i class="sb-dot" :style="{ background: c.color }"></i>
                <span class="sb-leg-name">{{ c.category }}</span>
                <span class="sb-leg-val">¥{{ fmt(c.monthly_cost) }}</span>
              </li>
            </ul>
          </div>
          <p v-else class="sb-empty">还没有订阅记录，点右上角「新增订阅」开始记账</p>
        </div>

        <div class="sb-panel glass">
          <div class="sb-panel-head">
            <span class="sb-panel-title">周期分布</span>
            <span class="sb-panel-sub">活跃订阅</span>
          </div>
          <ul class="sb-cycles">
            <li v-for="c in cycles" :key="c.cycle" class="sb-cycle">
              <span class="sb-cycle-label">{{ c.label }}</span>
              <span class="sb-cycle-bar">
                <i :style="{ width: c.count ? (c.count / maxCycleCount * 100) + '%' : '0%' }"></i>
              </span>
              <span class="sb-cycle-n">{{ c.count }}</span>
            </li>
          </ul>
          <p class="sb-hint">自动续费 {{ stats.auto_renew_count || 0 }} 条 · 一次性订阅不计入月均/年均</p>
        </div>
      </section>

      <!-- 列表 -->
      <section class="sb-list glass">
        <div class="sb-list-head">
          <span class="sb-list-title">全部订阅</span>
          <label class="sb-check">
            <input type="checkbox" v-model="hideInactive" /> 隐藏已停用
          </label>
        </div>
        <div class="sb-table-wrap">
          <table class="sb-table">
            <thead>
              <tr>
                <th>名称</th><th class="r">金额</th><th class="r">周期</th>
                <th class="r">下次到期</th><th class="r">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in visible" :key="s.id" :class="{ inactive: !s.is_active }">
                <td>
                  <span class="sb-name">{{ s.name }}</span>
                  <span v-if="s.category" class="sb-cat">{{ s.category }}</span>
                  <span v-if="s.auto_renew" class="sb-tag">自动续费</span>
                  <span v-if="!s.is_active" class="sb-tag off">已停用</span>
                  <span class="sb-code">月均 ¥{{ fmt(s.monthly_cost) }}</span>
                </td>
                <td class="r sb-num">¥{{ fmt(s.amount) }}</td>
                <td class="r">{{ s.cycle_label }}</td>
                <td class="r">
                  <template v-if="s.next_due">
                    <span class="sb-due">{{ s.next_due }}</span>
                    <span v-if="s.days_to_due !== null" class="sb-days" :class="daysCls(s.days_to_due)">
                      {{ daysLabel(s.days_to_due) }}
                    </span>
                  </template>
                  <span v-else class="sb-muted">未设</span>
                </td>
                <td class="r sb-actions">
                  <button v-if="s.is_active" class="sb-btn ghost tiny" @click="pay(s)">已缴费</button>
                  <button class="sb-btn ghost tiny" @click="openEdit(s)">编辑</button>
                  <button class="sb-btn ghost tiny danger" @click="remove(s)">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="!loading && !visible.length" class="sb-empty">暂无订阅记录</p>
        <p v-else-if="loading" class="sb-empty">加载中…</p>
      </section>

      <footer class="sb-foot">到期前 3 天（可逐条调整）会自动生成待办，在「待办」里统一处理</footer>
    </div>

    <!-- 新增 / 编辑 -->
    <el-dialog v-model="dialog" :title="form.id ? '编辑订阅' : '新增订阅'" width="540px">
      <el-form :model="form" label-width="82px">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="如 腾讯视频会员 / 家庭宽带" maxlength="80" />
        </el-form-item>
        <el-form-item label="金额">
          <el-input-number v-model="form.amount" :min="0" :precision="2" :controls="false"
                           placeholder="0.00" style="width:160px" />
          <span class="sb-form-unit">元 / 每周期</span>
        </el-form-item>
        <el-form-item label="周期">
          <el-select v-model="form.cycle" style="width:160px">
            <el-option v-for="o in CYCLE_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="下次到期">
          <el-date-picker v-model="form.next_due" type="date" value-format="YYYY-MM-DD"
                          placeholder="选择到期日" style="width:200px" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" filterable allow-create default-first-option
                     placeholder="选择或输入，如 影音" style="width:200px">
            <el-option v-for="c in CATEGORY_OPTIONS" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="提前提醒">
          <el-input-number v-model="form.remind_days" :min="0" :max="60" :controls="false"
                           style="width:120px" />
          <span class="sb-form-unit">天</span>
        </el-form-item>
        <el-form-item label="自动续费">
          <el-switch v-model="form.auto_renew" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" placeholder="账号、订单号、取消入口…" />
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
import DonutChart from '@/components/finance/DonutChart.vue'
import { subscriptionsApi, CYCLE_OPTIONS } from '@/api/family'

const CATEGORY_OPTIONS = ['影音', '软件', '云服务', '会员', '宽带通讯', '保险', '教育', '其他']

/* 配色取设计 token，避免硬编码 hex */
const PALETTE = [
  'var(--lj-seal)', 'var(--lj-dai)', 'var(--lj-ochre)', 'var(--yq-rain)',
  'var(--yq-gold)', 'var(--ls-jade)', 'var(--lj-vermilion)', 'var(--lj-mist)',
]

const list = ref([])
const stats = reactive({})
const loading = ref(true)
const hideInactive = ref(false)

const dialog = ref(false)
const saving = ref(false)
const form = reactive(emptyForm())

function emptyForm() {
  return {
    id: null, name: '', amount: 0, cycle: 'monthly', next_due: '',
    category: '', remind_days: 3, auto_renew: 0, is_active: 1, notes: '',
  }
}

const categories = computed(() =>
  (stats.categories || []).map((c, i) => ({
    category: c.category,
    amount: c.monthly_cost,
    monthly_cost: c.monthly_cost,
    color: PALETTE[i % PALETTE.length],
  })))

const cycles = computed(() => stats.cycles || [])
const maxCycleCount = computed(() => Math.max(...cycles.value.map((c) => c.count), 1))

const visible = computed(() =>
  hideInactive.value ? list.value.filter((s) => s.is_active) : list.value)

function fmt(v, n = 2) { return Number(v || 0).toFixed(n) }

function daysLabel(d) {
  if (d < 0) return `逾期 ${-d} 天`
  if (d === 0) return '今天'
  return `${d} 天`
}
function daysCls(d) {
  if (d < 0) return 'is-overdue'
  if (d <= 3) return 'is-soon'
  if (d <= 7) return 'is-near'
  return ''
}

async function reload() {
  loading.value = true
  try {
    const [lr, sr] = await Promise.all([subscriptionsApi.list(), subscriptionsApi.stats()])
    list.value = lr.data?.list || []
    Object.assign(stats, sr.data || {})
  } catch { /* 拦截器已提示 */ }
  finally { loading.value = false }
}

function openCreate() {
  Object.assign(form, emptyForm())
  dialog.value = true
}

function openEdit(s) {
  Object.assign(form, {
    id: s.id, name: s.name, amount: s.amount, cycle: s.cycle,
    next_due: s.next_due || '', category: s.category || '',
    remind_days: s.remind_days, auto_renew: s.auto_renew ? 1 : 0,
    is_active: s.is_active ? 1 : 0, notes: s.notes || '',
  })
  dialog.value = true
}

async function submit() {
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      amount: Number(form.amount) || 0,
      cycle: form.cycle,
      next_due: form.next_due || '',
      category: form.category || '',
      remind_days: form.remind_days ?? 3,
      auto_renew: form.auto_renew ? 1 : 0,
      is_active: form.is_active ? 1 : 0,
      notes: form.notes || '',
    }
    if (form.id) await subscriptionsApi.update(form.id, payload)
    else await subscriptionsApi.create(payload)
    ElMessage.success(form.id ? '已保存' : '已添加')
    dialog.value = false
    await reload()
  } catch { /* 拦截器已提示 */ }
  finally { saving.value = false }
}

async function pay(s) {
  try {
    await ElMessageBox.confirm(
      `确认「${s.name}」已缴费？到期日将顺延到下一个${s.cycle_label}周期。`,
      '标记已缴费', { type: 'info' },
    )
  } catch { return }
  try {
    const res = await subscriptionsApi.pay(s.id)
    ElMessage.success(res.msg || '已顺延到下一周期')
    await reload()
  } catch { /* 拦截器已提示 */ }
}

async function remove(s) {
  try {
    await ElMessageBox.confirm(`确认删除订阅「${s.name}」？可在回收站恢复。`, '提示', { type: 'warning' })
  } catch { return }
  try {
    await subscriptionsApi.remove(s.id)
    ElMessage.success('已删除')
    await reload()
  } catch { /* 拦截器已提示 */ }
}

onMounted(reload)
</script>

<style scoped>
.sb-page { min-height: 100vh; }
.sb-inner { max-width: 1080px; margin: 0 auto; padding: 84px 20px 40px; }

.sb-head { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; flex-wrap: wrap; }
.sb-titles { flex: 1; min-width: 180px; }
.sb-title { margin: 0; font-size: 22px; letter-spacing: .1em; color: var(--lj-text); }
.sb-sub { margin: 2px 0 0; font-size: 12px; color: var(--lj-text-2); letter-spacing: .08em; }
.sb-head-right { margin-left: auto; }

.sb-btn { border-radius: 9px; padding: 8px 16px; font-size: 13px; border: 1px solid transparent;
  cursor: pointer; transition: all .2s; font-family: inherit; }
.sb-btn.primary { background: linear-gradient(135deg, rgba(199,169,107,.85), rgba(127,168,163,.85)); color: #0B0F14; }
.sb-btn.ghost { background: transparent; color: var(--lj-text); border-color: var(--lj-line); }
.sb-btn.ghost:hover { border-color: var(--lj-line-strong); color: var(--lj-seal); }
.sb-btn.tiny { padding: 3px 9px; font-size: 12px; }
.sb-btn.danger { color: var(--pnl-up); }

.sb-kpi { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 14px; }
.sb-kpi-card { display: flex; flex-direction: column; gap: 5px; padding: 16px; border-radius: 16px; }
.sb-kpi-k { font-size: 12px; color: var(--lj-text-2); letter-spacing: .08em; }
.sb-kpi-v { font-size: 23px; font-weight: 700; color: var(--lj-text); }
.sb-kpi-v.warn { color: var(--lj-seal); }
.sb-kpi-s { font-size: 11px; color: var(--lj-text-3); }

.sb-grid { display: grid; grid-template-columns: 1.15fr 1fr; gap: 14px; margin-bottom: 14px; }
.sb-panel { border-radius: 16px; padding: 16px 20px; }
.sb-panel-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 14px; }
.sb-panel-title { font-size: 15px; letter-spacing: .08em; color: var(--lj-text); }
.sb-panel-sub { font-size: 12px; color: var(--lj-text-3); }

.sb-donut { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }
.sb-legend { list-style: none; margin: 0; padding: 0; flex: 1; min-width: 150px; }
.sb-leg { display: flex; align-items: center; gap: 8px; padding: 3px 0; font-size: 12px; }
.sb-dot { width: 8px; height: 8px; border-radius: 2px; flex: none; }
.sb-leg-name { flex: 1; color: var(--lj-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sb-leg-val { color: var(--lj-text-2); font-variant-numeric: tabular-nums; }

.sb-cycles { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 9px; }
.sb-cycle { display: flex; align-items: center; gap: 10px; font-size: 12px; }
.sb-cycle-label { width: 48px; flex: none; color: var(--lj-text-2); }
.sb-cycle-bar { flex: 1; height: 7px; border-radius: 999px; background: rgba(74,95,99,.12); overflow: hidden; }
.sb-cycle-bar i { display: block; height: 100%; border-radius: 999px; background: var(--lj-dai); transition: width .4s; }
.sb-cycle-n { width: 20px; text-align: right; color: var(--lj-text-2); font-variant-numeric: tabular-nums; }
.sb-hint { margin: 14px 0 0; font-size: 11px; color: var(--lj-text-3); }

.sb-list { border-radius: 16px; padding: 18px 20px; }
.sb-list-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 14px; }
.sb-list-title { font-size: 16px; letter-spacing: .08em; color: var(--lj-text); flex: 1; }
.sb-check { font-size: 12px; color: var(--lj-text-2); display: flex; align-items: center; gap: 6px; cursor: pointer; }

.sb-table-wrap { overflow-x: auto; }
.sb-table { width: 100%; border-collapse: collapse; }
.sb-table th { text-align: left; font-size: 12px; color: var(--lj-text-3); font-weight: 500;
  padding: 8px 10px; border-bottom: 1px solid var(--lj-line); }
.sb-table th.r, .sb-table td.r { text-align: right; }
.sb-table td { padding: 11px 10px; font-size: 13px; color: var(--lj-text);
  border-bottom: 1px solid rgba(74,95,99,.12); }
.sb-table tr:hover td { background: rgba(74,95,99,.05); }
.sb-table tr.inactive td { opacity: .55; }
.sb-name { font-weight: 600; }
.sb-cat { margin-left: 8px; font-size: 11px; color: var(--lj-text-2); padding: 1px 7px;
  border-radius: 999px; border: 1px solid var(--lj-line); }
.sb-tag { margin-left: 6px; font-size: 11px; color: var(--lj-dai); padding: 1px 7px;
  border-radius: 999px; background: rgba(127,168,163,.14); }
.sb-tag.off { color: var(--lj-text-3); background: rgba(74,95,99,.1); }
.sb-code { display: block; font-size: 11px; color: var(--lj-text-3); margin-top: 3px; }
.sb-num { font-variant-numeric: tabular-nums; }
.sb-due { font-variant-numeric: tabular-nums; }
.sb-days { margin-left: 8px; font-size: 11px; padding: 1px 7px; border-radius: 999px;
  border: 1px solid var(--lj-line); color: var(--lj-text-2); }
.sb-days.is-near { color: var(--lj-ochre); border-color: var(--lj-ochre); }
.sb-days.is-soon { color: var(--lj-seal); border-color: var(--lj-seal); background: var(--lj-seal-soft); }
.sb-days.is-overdue { color: #fff; background: var(--pnl-up); border-color: var(--pnl-up); }
.sb-muted { color: var(--lj-text-3); }
.sb-actions { white-space: nowrap; }
.sb-actions .sb-btn { margin-left: 4px; }

.sb-empty { text-align: center; padding: 40px 20px; font-size: 13px; color: var(--lj-text-3); }
.sb-foot { margin-top: 20px; text-align: center; font-size: 11px; color: var(--lj-text-3); letter-spacing: .08em; }
.sb-form-unit { margin-left: 8px; font-size: 12px; color: var(--lj-text-3); }

@media (max-width: 900px) {
  .sb-kpi { grid-template-columns: repeat(2, 1fr); }
  .sb-grid { grid-template-columns: 1fr; }
}
</style>
