<template>
  <IslandInnerBase type="tool" title="时间胶囊" subtitle="写给未来的信 · 到期才可读 · 服务端强制锁死">
    <div class="cp-tool">
      <!-- 写信 -->
      <div class="cp-compose glass-card">
        <input v-model="title" class="cp-title" maxlength="80" placeholder="标题（选填，如：给 30 岁的我）">
        <textarea v-model="content" class="cp-content" rows="6" placeholder="写给未来的自己……（到期前服务端锁死，谁也看不到）"></textarea>
        <div class="cp-row">
          <label class="cp-unlock-label">解锁时间
            <input v-model="unlockAt" type="datetime-local" class="cp-datetime">
          </label>
          <div class="cp-quick">
            <button v-for="q in quicks" :key="q.label" class="cp-quick-btn" @click="setQuick(q.days)">{{ q.label }}</button>
          </div>
        </div>
        <button class="cp-submit" :disabled="submitting" @click="submit">{{ submitting ? '封存中…' : '🔒 封存' }}</button>
        <div v-if="error" class="cp-err">{{ error }}</div>
      </div>

      <!-- 列表 -->
      <div class="cp-list">
        <div v-for="c in list" :key="c.id" class="cp-item" :class="{ locked: c.locked }">
          <div class="cp-item-head">
            <span class="cp-item-title">{{ c.title }}</span>
            <span class="cp-chip" :class="c.locked ? 'chip-locked' : 'chip-open'">
              {{ c.locked ? `🔒 ${fmtLeft(c.seconds_left)}` : '✉️ 已解锁' }}
            </span>
          </div>
          <div class="cp-item-meta">封存于 {{ (c.created_at || '').slice(0, 16) }} · 解锁于 {{ (c.unlock_at || '').slice(0, 16) }}</div>
          <div v-if="!c.locked && c.content" class="cp-body">{{ c.content }}</div>
          <div v-else-if="c.locked" class="cp-body cp-locked-hint">内容已封存，到期后自动解锁——急也没用，服务端说了算。</div>
          <div class="cp-item-foot">
            <button v-if="!c.locked && !c.opened_at" class="cp-mini" @click="openIt(c)">拆信</button>
            <button class="cp-mini danger" @click="delIt(c)">删除</button>
          </div>
        </div>
        <div v-if="!list.length && !loading" class="cp-empty">还没有胶囊。写一封给未来的自己吧。</div>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { capsuleCreate, capsuleList, capsuleOpen, capsuleDelete } from '@/api/toolkit'

const title = ref('')
const content = ref('')
const unlockAt = ref('')
const submitting = ref(false)
const error = ref('')
const list = ref([])
const loading = ref(true)

const quicks = [
  { label: '1 个月', days: 30 },
  { label: '半年', days: 182 },
  { label: '1 年', days: 365 },
  { label: '3 年', days: 1095 },
  { label: '10 年', days: 3650 },
]

function setQuick(days) {
  const d = new Date(Date.now() + days * 86400000)
  // datetime-local 需要 YYYY-MM-DDTHH:mm
  unlockAt.value = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}

function fmtLeft(s) {
  if (s >= 86400 * 365) return `还剩 ${(s / 86400 / 365).toFixed(1)} 年`
  if (s >= 86400) return `还剩 ${Math.floor(s / 86400)} 天`
  if (s >= 3600) return `还剩 ${Math.floor(s / 3600)} 小时`
  return `还剩 ${Math.floor(s / 60)} 分钟`
}

async function load() {
  loading.value = true
  try {
    const body = await capsuleList()
    list.value = body?.data?.list || []
  } finally {
    loading.value = false
  }
}

async function submit() {
  error.value = ''
  if (!content.value.trim()) { error.value = '写点什么吧，空白的信没有意义'; return }
  if (!unlockAt.value) { error.value = '选一个解锁时间'; return }
  submitting.value = true
  try {
    await capsuleCreate({
      title: title.value,
      content: content.value,
      unlock_at: new Date(unlockAt.value).toISOString().slice(0, 19).replace('T', ' '),
    })
    ElMessage.success('已封存 🔒')
    title.value = ''; content.value = ''; unlockAt.value = ''
    await load()
  } catch (e) {
    error.value = e?.response?.data?.detail || '封存失败'
  } finally {
    submitting.value = false
  }
}

async function openIt(c) {
  try {
    const body = await capsuleOpen(c.id)
    const idx = list.value.findIndex(x => x.id === c.id)
    if (idx >= 0) list.value[idx] = body.data
    ElMessage.success('信已拆开')
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '还没到解锁时间')
  }
}

async function delIt(c) {
  try {
    await ElMessageBox.confirm(c.locked ? '这封胶囊还没到期，删除后无法恢复，确定？' : '删除这封胶囊？', '确认', { type: 'warning' })
  } catch { return }
  await capsuleDelete(c.id)
  list.value = list.value.filter(x => x.id !== c.id)
  ElMessage.success('已删除')
}

onMounted(load)
</script>

<style scoped>
.cp-compose { padding: 18px; display: flex; flex-direction: column; gap: 12px; }
.cp-title, .cp-content, .cp-datetime {
  width: 100%; padding: 10px 12px; border-radius: 10px; font-size: 14px;
  border: 1px solid var(--dp-line, rgba(0,0,0,.12)); background: var(--dp-surface, #fff);
  color: var(--dp-text, #18202a);
}
.cp-content { resize: vertical; line-height: 1.7; }
.cp-row { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.cp-unlock-label { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--dp-text2, #45505b); }
.cp-unlock-label input { width: auto; }
.cp-quick { display: flex; gap: 6px; flex-wrap: wrap; }
.cp-quick-btn {
  padding: 5px 12px; border-radius: 999px; font-size: 12px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: transparent; color: var(--dp-text2, #45505b);
}
.cp-quick-btn:hover { border-color: var(--yq-gold, #c7a96b); color: var(--yq-gold, #c7a96b); }
.cp-submit {
  align-self: flex-start; padding: 10px 28px; border-radius: 10px; border: none; cursor: pointer;
  background: var(--yq-gold, #c7a96b); color: #fff; font-size: 14px; font-weight: 600;
}
.cp-submit:disabled { opacity: .55; }
.cp-err { color: #e5484d; font-size: 13px; }
.cp-list { margin-top: 18px; display: flex; flex-direction: column; gap: 12px; }
.cp-item { padding: 14px 16px; border-radius: 12px; border: 1px solid var(--dp-line, rgba(0,0,0,.08)); }
.cp-item.locked { background: var(--dp-bg2, rgba(0,0,0,.03)); }
.cp-item-head { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.cp-item-title { font-weight: 600; font-size: 14.5px; color: var(--dp-text, #18202a); }
.cp-chip { font-size: 12px; padding: 3px 10px; border-radius: 999px; flex: none; }
.chip-locked { background: rgba(199,169,107,.16); color: #8a6d1a; }
.chip-open { background: rgba(26,168,106,.14); color: #157a4c; }
.cp-item-meta { margin-top: 6px; font-size: 12px; color: var(--dp-text3, #8a8f98); }
.cp-body {
  margin-top: 10px; padding: 12px 14px; border-radius: 10px; font-size: 14px; line-height: 1.8;
  background: var(--dp-surface, #fff); border: 1px solid var(--dp-line, rgba(0,0,0,.08));
  white-space: pre-wrap; color: var(--dp-text, #18202a);
}
.cp-locked-hint { color: var(--dp-text3, #8a8f98); font-style: italic; }
.cp-item-foot { margin-top: 10px; display: flex; gap: 8px; }
.cp-mini {
  padding: 4px 14px; border-radius: 8px; font-size: 12px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text2, #45505b);
}
.cp-mini.danger:hover { color: #e5484d; border-color: #e5484d; }
.cp-empty { text-align: center; padding: 30px; color: var(--dp-text3, #8a8f98); font-size: 13px; }
</style>
