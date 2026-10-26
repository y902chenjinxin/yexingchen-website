<template>
  <section v-if="hasAny" class="rel glass-card" @click="goRelations">
    <header class="rel-head">
      <span class="rel-tag">关系</span>
      <span class="rel-title">{{ summary }}</span>
      <span class="rel-more">全部 {{ total }} 人 ›</span>
    </header>

    <div class="rel-row">
      <button
        v-for="c in chips"
        :key="c.key"
        class="rel-chip"
        :class="'rel-chip--' + c.kind"
        @click.stop="goRelations"
      >
        <span class="rel-ico">{{ c.icon }}</span>
        <b>{{ c.name }}</b>
        <em>{{ c.text }}</em>
      </button>
      <span v-if="!chips.length" class="rel-none">都挺好的，没有谁被落下。</span>
    </div>
  </section>
</template>

<script setup>
/**
 * 工作台「关系」提醒卡（v2.46.250）
 *
 * 刻意做得很矮：一行一个人名，不占工作台的视线。
 * 内向的人需要的不是「关系仪表盘」，而是「现在该给谁发条消息」。
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import relationsApi from '@/api/relations'

const router = useRouter()
const dash = ref({ birthdays: [], overdue: [], overdue_total: 0, blind: null, total: 0 })

const total = computed(() => dash.value.total || 0)

const chips = computed(() => {
  const out = []
  for (const c of (dash.value.birthdays || []).slice(0, 2)) {
    out.push({
      key: 'b' + c.id, kind: 'bday', icon: '🎂', name: c.name,
      text: c.birthday?.label || '',
    })
  }
  for (const c of (dash.value.overdue || []).slice(0, 3)) {
    out.push({
      key: 'o' + c.id, kind: 'late', icon: '🕊', name: c.name,
      text: `${c.days_since} 天`,
    })
  }
  if (!out.length && dash.value.blind) {
    const b = dash.value.blind
    out.push({
      key: 'n' + b.id, kind: 'blind', icon: '🎲', name: b.name,
      text: b.topics || '想起一个人',
    })
  }
  return out
})

const hasAny = computed(() => total.value > 0)

const summary = computed(() => {
  const n = chips.value.length
  if (!n) return '今天没有非联系不可的人'
  const b = (dash.value.birthdays || []).length
  const o = dash.value.overdue_total || 0
  const bits = []
  if (b) bits.push(`${b} 位生日将近`)
  if (o) bits.push(`${o} 位有点久了`)
  return bits.join(' · ') || '想起一个人'
})

function goRelations() {
  router.push('/relations')
}

onMounted(async () => {
  try {
    const res = await relationsApi.dashboard()
    dash.value = res?.data || dash.value
  } catch { /* 没数据就不显示这张卡 */ }
})
</script>

<style scoped>
.rel { padding: 13px 18px 14px; cursor: pointer; transition: border-color .15s; }
.rel:hover { border-color: var(--tc-line-strong, rgba(15, 60, 110, .26)); }

.rel-head { display: flex; align-items: center; gap: 8px; margin-bottom: 9px; }
.rel-tag {
  font-size: 10.5px; font-weight: 600; letter-spacing: .08em; padding: 2px 7px; border-radius: 6px;
  background: rgba(14, 147, 184, .12); color: var(--tc-cyan-deep, #0a708c);
}
.rel-title { flex: 1; min-width: 0; font-size: 13px; font-weight: 600; color: var(--tc-text, #0b1622); }
.rel-more { font-size: 11px; color: var(--tc-text-3, #5b6f8a); }

.rel-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.rel-chip {
  display: inline-flex; align-items: center; gap: 6px; padding: 5px 11px; border-radius: 999px;
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .12)); background: transparent;
  font: inherit; cursor: pointer; max-width: 100%;
}
.rel-chip:hover { border-color: var(--tc-cyan, #0e93b8); background: rgba(14, 147, 184, .05); }
.rel-chip b { font-size: 12.5px; font-weight: 600; color: var(--tc-text, #0b1622); }
.rel-chip em { font-style: normal; font-size: 11px; color: var(--tc-text-3, #5b6f8a); }
.rel-chip--bday { border-color: rgba(169, 129, 47, .3); }
.rel-chip--bday em { color: var(--lj-seal, #a9812f); }
.rel-chip--late em { color: #b4552f; }
.rel-ico { font-size: 12px; line-height: 1; }

.rel-none { font-size: 12px; color: var(--tc-text-3, #5b6f8a); }
</style>
