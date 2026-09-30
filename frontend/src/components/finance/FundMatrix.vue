<template>
  <div class="fin-mtable-wrap">
    <table class="fin-mtable">
      <thead>
        <tr>
          <th class="c-name">月份</th>
          <th v-for="m in members" :key="m.user_id" class="c-num">{{ m.name }}</th>
          <th class="c-num">合计</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.month">
          <td class="c-name">{{ r.month }}</td>
          <td v-for="m in members" :key="m.user_id" class="c-num">¥ {{ money(cell(r, m.user_id)) }}</td>
          <td class="c-num strong">¥ {{ money(r.total) }}</td>
        </tr>
        <tr class="fin-mtr total">
          <td class="c-name">合计</td>
          <td v-for="m in members" :key="m.user_id" class="c-num">¥ {{ money(colTotal(m.user_id)) }}</td>
          <td class="c-num">¥ {{ money(grandTotal) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
/**
 * 「各人各月转入」矩阵：行=月份，列=家庭成员，末行合计。
 * 存款 / 公款 / 个人零花三块看板共用，数据来自 /finance/funds 的 monthly_by_member。
 */
import { computed } from 'vue'

const props = defineProps({
  // [{ month, members: [{ user_id, name, avatar, amount }], total }]
  rows: { type: Array, default: () => [] },
  // 列定义：家庭成员的并集（跨行去重后的顺序）
  members: { type: Array, default: () => [] },
})

const money = (v) => Number(v || 0).toFixed(2)

function cell(row, uid) {
  const hit = (row.members || []).find((m) => m.user_id === uid)
  return hit ? hit.amount : 0
}
function colTotal(uid) {
  return props.rows.reduce((s, r) => s + cell(r, uid), 0)
}
// 合计 = 各行 total 之和；与池子「累计转入」同源同口径，必然对得上
const grandTotal = computed(() => props.rows.reduce((s, r) => s + (r.total || 0), 0))
</script>

<!-- 父组件（FinanceView）的 scoped 样式只覆盖到本组件根节点，表体在根节点内部拿不到
     那份 scope id，所以表格样式必须在这里自带一份，否则整张表是无边框裸表。 -->
<style scoped>
.fin-mtable-wrap { overflow-x: auto; }
.fin-mtable { width: 100%; border-collapse: collapse; font-size: 13px; }
.fin-mtable th { text-align: right; padding: 8px 10px; font-size: 12px; font-weight: 600;
  color: var(--lj-text-2); border-bottom: 1px solid var(--lj-line); white-space: nowrap; }
.fin-mtable th.c-name, .fin-mtable td.c-name { text-align: left; }
.fin-mtable td { padding: 9px 10px; border-bottom: 1px dashed var(--lj-line); text-align: right;
  white-space: nowrap; font-variant-numeric: tabular-nums; }
.fin-mtable td.strong { font-weight: 600; color: var(--lj-ochre); }
.fin-mtr.total { font-weight: 600; background: rgba(199,169,107,.08); }
.fin-mtr.total td { border-bottom: none; }
@media (max-width: 560px) {
  .fin-mtable { font-size: 12px; }
  .fin-mtable th, .fin-mtable td { padding: 7px 8px; }
}
</style>
