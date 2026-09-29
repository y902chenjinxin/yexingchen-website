<!--
  ServerMonitorCard.vue —— 服务器资源监测（PC 工作台首页，v2.40.39）

  口径说明（先说清楚，免得被标题误导）：
  - **内存**只有系统级：玄黄后端是一个 Python 进程，音乐/视频等模块跑在同一进程里，
    操作系统层面分不出「音乐占多少内存」，任何这种数字都是编的。
  - **模块维度是「存储占用」**：该模块的上传文件 + 它名下的数据库表 —— 音乐/视频真正吃资源的地方。
  - 进程内存按「服务」聚合（后端 / 解析服务 / Nginx），这个是真的。
  组件只在桌面分支挂载（WorkbenchView 的 v-else 里），手机端不出现。
-->
<template>
  <div v-mouse-light class="sv-card bento-card">
    <div class="sv-head">
      <div class="sv-title">
        服务器监测
        <span class="sv-sub">内存 · 磁盘 · 模块占用</span>
      </div>
      <div class="sv-head-right">
        <span v-if="data" class="sv-time">{{ data.collected_at }} 采集</span>
        <button class="sv-refresh" :disabled="loading" title="重新采集" @click="load(true)">↻</button>
      </div>
    </div>

    <p v-if="loading && !data" class="sv-tip">正在读取服务器状态…</p>
    <p v-else-if="data && data.supported === false" class="sv-tip">{{ data.reason }}</p>
    <p v-else-if="error" class="sv-tip sv-tip--err">{{ error }}</p>

    <template v-else-if="data">
      <!-- ===== 内存 / 磁盘 ===== -->
      <div class="sv-gauges">
        <div class="sv-gauge">
          <div class="sv-gauge-head">
            <span>内存</span><b :class="lv(mem.percent)">{{ mem.percent }}%</b>
          </div>
          <div class="sv-bar"><i :class="lv(mem.percent)" :style="{ width: pct(mem.percent) }"></i></div>
          <div class="sv-gauge-foot">
            <b>{{ fmtMb(mem.used_mb) }}</b> / {{ fmtMb(mem.total_mb) }}
            <span class="sv-dim">· 可用 {{ fmtMb(mem.available_mb) }}</span>
          </div>
          <div v-if="mem.swap_total_mb" class="sv-gauge-sub">
            Swap {{ fmtMb(mem.swap_used_mb) }} / {{ fmtMb(mem.swap_total_mb) }}
          </div>
        </div>

        <div class="sv-gauge">
          <div class="sv-gauge-head">
            <span>磁盘</span><b :class="lv(disk.percent)">{{ disk.percent }}%</b>
          </div>
          <div class="sv-bar"><i :class="lv(disk.percent)" :style="{ width: pct(disk.percent) }"></i></div>
          <div class="sv-gauge-foot">
            <b>{{ disk.used_gb }}G</b> / {{ disk.total_gb }}G
            <span class="sv-dim">· 剩余 {{ disk.avail_gb }}G</span>
          </div>
        </div>
      </div>

      <!-- ===== 模块占用（一级 → 可展开二级） ===== -->
      <div class="sv-sec">
        <div class="sv-sec-head">
          <span>模块占用</span>
          <span class="sv-sec-total">{{ fmtBytes(data.modules_total_bytes) }}</span>
        </div>
        <ul class="sv-modules">
          <li v-for="g in data.modules" :key="g.key">
            <button class="sv-row" :class="{ open: expanded[g.key] }" @click="toggle(g.key)">
              <span class="sv-caret">{{ expanded[g.key] ? '▾' : '▸' }}</span>
              <span class="sv-name">{{ g.name }}</span>
              <span class="sv-mini"><i :style="{ width: pct(g.percent) }"></i></span>
              <span class="sv-pct">{{ g.percent }}%</span>
              <span class="sv-size">{{ fmtBytes(g.bytes) }}</span>
            </button>
            <ul v-if="expanded[g.key]" class="sv-children">
              <li v-for="c in g.children.filter(x => x.kb > 0)" :key="c.key">
                <span class="sv-name">{{ c.name }}</span>
                <span class="sv-mini"><i :style="{ width: pct(c.percent) }"></i></span>
                <span class="sv-pct">{{ c.percent }}%</span>
                <span class="sv-size">{{ fmtBytes(c.bytes) }}</span>
              </li>
            </ul>
          </li>
        </ul>
        <div class="sv-note">
          口径：上传文件 + 数据库表；不含程序与依赖（{{ fmtBytes((data.extra?.program_kb || 0) * 1024) }}）
          与前端站点（{{ fmtBytes((data.extra?.dist_kb || 0) * 1024) }}）
        </div>
      </div>

      <!-- ===== 进程内存（按服务聚合） ===== -->
      <div class="sv-sec">
        <div class="sv-sec-head"><span>进程内存</span><span class="sv-sec-total">常驻</span></div>
        <div class="sv-procs">
          <span v-for="p in data.processes" :key="p.name" class="sv-chip">
            {{ p.name }}<b>{{ p.rss_mb }}M</b><em v-if="p.count > 1">×{{ p.count }}</em>
          </span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { workbenchApi } from '@/api/workbench'

const data = ref(null)
const loading = ref(false)
const error = ref('')
const expanded = ref({})

const mem = computed(() => data.value?.memory || {})
const disk = computed(() => data.value?.disk || {})

const pct = (n) => `${Math.max(0, Math.min(100, Number(n) || 0))}%`
/** 使用率配色：<60 正常 / <85 偏紧 / ≥85 告急 */
const lv = (n) => (n >= 85 ? 'lv-danger' : n >= 60 ? 'lv-warn' : 'lv-ok')

function fmtMb(mb) {
  const v = Number(mb) || 0
  return v >= 1024 ? `${(v / 1024).toFixed(1)}G` : `${v}M`
}
function fmtBytes(bytes) {
  const b = Number(bytes) || 0
  if (b >= 1024 ** 3) return `${(b / 1024 ** 3).toFixed(2)} GB`
  if (b >= 1024 ** 2) return `${(b / 1024 ** 2).toFixed(1)} MB`
  if (b >= 1024) return `${(b / 1024).toFixed(0)} KB`
  return `${b} B`
}

function toggle(key) {
  expanded.value = { ...expanded.value, [key]: !expanded.value[key] }
}

async function load(force = false) {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const res = await workbenchApi.serverMonitor()
    data.value = res?.data || res || null
    // 首次加载自动展开占比最大的模块，省得还要手点一下才看得到音乐/视频
    if (force === false && data.value?.modules?.length && !Object.keys(expanded.value).length) {
      expanded.value = { [data.value.modules[0].key]: true }
    }
  } catch (e) {
    error.value = e?.response?.data?.detail || '读取失败（仅超管可见）'
  } finally {
    loading.value = false
  }
}

onMounted(() => load(false))
</script>

<style scoped>
.sv-card { grid-column: 1 / -1; }
.sv-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.sv-title { font-size: 14px; font-weight: 700; color: var(--dp-text); display: flex; align-items: baseline; gap: 8px; }
.sv-sub { font-size: 11.5px; font-weight: 400; color: var(--dp-text3); }
.sv-head-right { display: flex; align-items: center; gap: 8px; }
.sv-time { font-size: 11px; color: var(--dp-text3); }
.sv-refresh {
  border: 1px solid var(--dp-line); background: transparent; color: var(--dp-text2); cursor: pointer;
  width: 26px; height: 26px; border-radius: 8px; font-size: 13px; line-height: 1;
}
.sv-refresh:hover:not(:disabled) { border-color: var(--yq-gold, var(--dp-accent)); color: var(--yq-gold, var(--dp-accent)); }
.sv-refresh:disabled { opacity: .5; cursor: default; }
.sv-tip { font-size: 12.5px; color: var(--dp-text3); margin: 24px 0; text-align: center; }
.sv-tip--err { color: #e5484d; }

/* ---------- 内存 / 磁盘 ---------- */
.sv-gauges { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.sv-gauge-head { display: flex; align-items: baseline; justify-content: space-between; font-size: 12.5px; color: var(--dp-text2); }
.sv-gauge-head b { font-size: 15px; font-variant-numeric: tabular-nums; }
.sv-bar { margin: 7px 0 6px; height: 7px; border-radius: 999px; background: var(--dp-bg2, rgba(0, 0, 0, .06)); overflow: hidden; }
.sv-bar i { display: block; height: 100%; border-radius: 999px; transition: width .4s ease; }
.lv-ok { color: #1aa86a; }
.sv-bar i.lv-ok { background: linear-gradient(90deg, #1aa86a, #38c98a); }
.lv-warn { color: #d08700; }
.sv-bar i.lv-warn { background: linear-gradient(90deg, #d08700, #f0b429); }
.lv-danger { color: #e5484d; }
.sv-bar i.lv-danger { background: linear-gradient(90deg, #e5484d, #f4736f); }
.sv-gauge-foot { font-size: 12px; color: var(--dp-text2); font-variant-numeric: tabular-nums; }
.sv-gauge-foot b { color: var(--dp-text); }
.sv-dim { color: var(--dp-text3); }
.sv-gauge-sub { margin-top: 3px; font-size: 11px; color: var(--dp-text3); }

/* ---------- 模块 ---------- */
.sv-sec { margin-top: 16px; padding-top: 13px; border-top: 1px solid var(--dp-line); }
.sv-sec-head {
  display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 8px;
  font-size: 12.5px; color: var(--dp-text2);
}
.sv-sec-total { font-size: 12px; color: var(--dp-text3); font-variant-numeric: tabular-nums; }
.sv-modules { list-style: none; margin: 0; padding: 0; }
.sv-row {
  width: 100%; display: grid; grid-template-columns: 14px 96px 1fr 46px 72px; align-items: center;
  gap: 8px; padding: 5px 6px; border: 0; border-radius: 8px; background: transparent;
  cursor: pointer; font-family: inherit; text-align: left; transition: background .16s;
}
.sv-row:hover { background: var(--dp-accent-faint, rgba(167, 139, 250, .08)); }
.sv-row.open { background: var(--dp-accent-faint, rgba(167, 139, 250, .06)); }
.sv-caret { font-size: 10px; color: var(--dp-text3); }
.sv-name { font-size: 12.5px; color: var(--dp-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sv-mini { height: 5px; border-radius: 999px; background: var(--dp-bg2, rgba(0, 0, 0, .06)); overflow: hidden; }
.sv-mini i { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, rgba(199, 169, 107, .85), rgba(127, 168, 163, .85)); }
.sv-pct { font-size: 11.5px; color: var(--dp-text2); text-align: right; font-variant-numeric: tabular-nums; }
.sv-size { font-size: 11.5px; color: var(--dp-text3); text-align: right; font-variant-numeric: tabular-nums; }
.sv-children { list-style: none; margin: 2px 0 4px; padding: 0; }
.sv-children li {
  display: grid; grid-template-columns: 96px 1fr 46px 72px; align-items: center; gap: 8px;
  padding: 3px 6px 3px 20px;
}
.sv-children .sv-name { font-size: 12px; color: var(--dp-text2); }
.sv-children .sv-mini { height: 4px; }
.sv-children .sv-mini i { background: linear-gradient(90deg, rgba(127, 168, 163, .6), rgba(127, 168, 163, .35)); }
.sv-note { margin-top: 8px; font-size: 11px; color: var(--dp-text3); line-height: 1.6; }

/* ---------- 进程 ---------- */
.sv-procs { display: flex; flex-wrap: wrap; gap: 8px; }
.sv-chip {
  display: inline-flex; align-items: center; gap: 5px; padding: 4px 10px; border-radius: 999px;
  font-size: 11.5px; color: var(--dp-text2);
  background: var(--dp-accent-faint, rgba(167, 139, 250, .1));
}
.sv-chip b { color: var(--dp-text); font-variant-numeric: tabular-nums; }
.sv-chip em { font-style: normal; font-size: 10.5px; color: var(--dp-text3); }

/* 窄屏（桌面窗口被压窄时也不会挤坏；真正的手机端不渲染本卡片） */
@media (max-width: 760px) {
  .sv-gauges { grid-template-columns: 1fr; gap: 12px; }
  .sv-row { grid-template-columns: 14px 70px 1fr 40px 62px; }
  .sv-children li { grid-template-columns: 70px 1fr 40px 62px; }
}
</style>
