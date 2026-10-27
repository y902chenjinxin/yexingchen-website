<template>
  <div class="va-page">
    <div class="va-inner">
      <header class="va-head">
        <BackButton class="va-back" />
        <div class="va-titles">
          <h1 class="va-title">密码保险箱</h1>
          <p class="va-sub">全家共享的密码便签本 —— 记下来就不会忘</p>
        </div>
        <div class="va-head-right">
          <IconButton icon="plus" label="存一条" variant="primary" @click="openCreate" />
        </div>
      </header>

      <!-- 用途边界写清楚，避免把重要密码放这里 -->
      <div class="va-notice">
        <span class="va-notice-ic" aria-hidden="true"><AppIcon icon="🔒" :size="15" /></span>
        <span>这里只放<b>不重要、丢了也不致命</b>的密码（网站会员 / WiFi / 门禁 / 旧设备）。
          银行、支付、邮箱、主账号请用专业工具（Vaultwarden / KeePassXC / 系统钥匙串）。</span>
      </div>

      <!-- v2.46.159：页面工具栏统一用 PageToolbar（间距/换行一处定义） -->
      <PageToolbar>
        <SearchField v-model="filters.q" placeholder="搜名称 / 账号 / 网址 / 备注" width="210px" @search="reload" />
        <FilterSelect v-model="filters.uploader_id" placeholder="谁存的（全部）" width="150px" @change="reload">
          <el-option v-for="u in uploaders" :key="u.user_id" :value="u.user_id" :label="u.name" />
        </FilterSelect>
        <FilterSelect v-model="filters.category" placeholder="全部分类" width="140px" @change="reload">
          <el-option v-for="c in categories" :key="c" :value="c" :label="c" />
        </FilterSelect>
        <IconButton icon="refresh" label="重置" @click="resetFilters" />
      </PageToolbar>

      <div v-if="loading" class="va-empty">加载中…</div>
      <EmptyState
        v-else-if="!list.length"
        title="保险箱还是空的"
        description="先存一条试试 —— 比如家里的 WiFi 密码、快递柜取件码。"
        action-label="存一条"
        @action="openCreate"
      />

      <div v-else class="va-list">
        <article v-for="e in list" :key="e.id" class="va-card glass">
          <div class="va-card-ic"><AppIcon :icon="categoryEmoji(e.category)" :size="19" /></div>
          <div class="va-card-main">
            <div class="va-name-row">
              <span class="va-name">{{ e.title }}</span>
              <span class="va-cat">{{ e.category }}</span>
              <span class="va-owner">{{ e.uploader_name }} 存</span>
            </div>
            <div class="va-fields">
              <span v-if="e.username" class="va-field">
                <i>账号</i>{{ e.username }}
                <IconButton icon="copy" size="sm" label="复制账号" @click="copy(e.username, '账号')" />
              </span>
              <span v-if="e.password" class="va-field">
                <i>密码</i>
                <code class="va-pwd">{{ shown.has(e.id) ? e.password : '••••••' }}</code>
                <IconButton :icon="shown.has(e.id) ? 'hide' : 'eye'" size="sm" :label="shown.has(e.id) ? '隐藏' : '显示'" @click="toggle(e.id)" />
                <IconButton icon="copy" size="sm" label="复制密码" @click="copy(e.password, '密码')" />
              </span>
              <span v-if="e.url" class="va-field">
                <i>网址</i>
                <a :href="e.url" target="_blank" rel="noopener noreferrer" class="va-link">{{ shortUrl(e.url) }}</a>
              </span>
            </div>
            <p v-if="e.note" class="va-note">{{ e.note }}</p>
          </div>
          <div class="va-card-actions">
            <IconButton icon="edit" size="sm" label="编辑" @click="openEdit(e)" />
            <IconButton icon="trash" size="sm" label="删除" variant="danger" @click="remove(e)" />
          </div>
        </article>
      </div>
    </div>

    <el-dialog v-model="formVisible" :title="form.id ? '编辑' : '存一条密码'" width="560px">
      <el-form label-width="64px" label-position="left">
        <el-form-item label="名称"><el-input v-model="form.title" placeholder="公司 WiFi / 咖啡机 App" maxlength="120" /></el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="c in categories" :key="c" :value="c" :label="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="账号"><el-input v-model="form.username" placeholder="可留空" maxlength="160" /></el-form-item>
        <el-form-item label="密码">
          <div class="va-pwd-row">
            <el-input v-model="form.password" placeholder="可留空" maxlength="300" />
            <button class="va-btn tiny" :disabled="generating" @click.prevent="generate">{{ generating ? '生成中…' : '生成' }}</button>
          </div>
        </el-form-item>
        <el-form-item label="网址"><el-input v-model="form.url" placeholder="https://… 可留空" maxlength="300" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.note" type="textarea" :rows="3" placeholder="备注（可留空）" maxlength="500" /></el-form-item>
      </el-form>
      <template #footer>
        <button class="va-btn" @click="formVisible = false">取消</button>
        <button class="va-btn primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import EmptyState from '@/components/EmptyState.vue'
import PageToolbar from '@/components/common/PageToolbar.vue'
import SearchField from '@/components/common/SearchField.vue'
import FilterSelect from '@/components/common/FilterSelect.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import BackButton from '@/components/BackButton.vue'
import { vaultApi } from '@/api/lifeExtra'
import { copyText } from '@/utils/clipboard'
import AppIcon from '@/components/common/AppIcon.vue'
import IconButton from '@/components/common/IconButton.vue'

const list = ref([])
const uploaders = ref([])
const categories = ref(['网站', 'WiFi', '设备', '门禁', '其他'])
const filters = reactive({ q: '', uploader_id: '', category: '' })
const loading = ref(true)
const saving = ref(false)
const generating = ref(false)
const shown = ref(new Set())          // 当前显示明文的条目 id（默认全部打码）

const formVisible = ref(false)
const form = reactive({ id: null, title: '', url: '', username: '', password: '', note: '', category: '网站' })

function categoryEmoji(c) {
  return { 网站: '🌐', WiFi: '📶', 设备: '📟', 门禁: '🔑', 其他: '🗂' }[c] || '🗂'
}
function shortUrl(u) {
  try { return new URL(u).hostname } catch { return u }
}
function toggle(id) {
  const s = new Set(shown.value)
  if (s.has(id)) s.delete(id); else s.add(id)
  shown.value = s
}
async function copy(text, label) {
  if (!text) { ElMessage.warning(`没有${label}可复制`); return }
  await copyText(text, `${label}已复制`)
}

async function reload() {
  loading.value = true
  try {
    const params = {}
    if (filters.q) params.q = filters.q
    if (filters.uploader_id) params.uploader_id = filters.uploader_id
    if (filters.category) params.category = filters.category
    const res = await vaultApi.list(params)
    list.value = res?.data?.list || []
    if (res?.data?.categories?.length) categories.value = res.data.categories
    shown.value = new Set()          // 重新加载后回到打码状态
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  Object.assign(filters, { q: '', uploader_id: '', category: '' })
  reload()
}

function openCreate() {
  Object.assign(form, { id: null, title: '', url: '', username: '', password: '', note: '', category: '网站' })
  formVisible.value = true
}
function openEdit(e) {
  Object.assign(form, {
    id: e.id, title: e.title, url: e.url, username: e.username,
    password: e.password, note: e.note, category: e.category,
  })
  formVisible.value = true
}

async function generate() {
  generating.value = true
  try {
    const res = await vaultApi.generate({ length: 16, charset: 'all' })
    form.password = res?.data?.password || ''
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '生成失败')
  } finally {
    generating.value = false
  }
}

async function save() {
  if (!form.title.trim()) { ElMessage.warning('至少写个名称'); return }
  saving.value = true
  try {
    const payload = {
      title: form.title.trim(), url: form.url, username: form.username,
      password: form.password, note: form.note, category: form.category,
    }
    if (form.id) await vaultApi.update(form.id, payload)
    else await vaultApi.create(payload)
    ElMessage.success(form.id ? '已更新' : '已存进保险箱')
    formVisible.value = false
    await reload()
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(e) {
  try {
    await ElMessageBox.confirm(`删除「${e.title}」？`, '确认删除', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '算了',
    })
  } catch { return }
  try {
    await vaultApi.remove(e.id)
    ElMessage.success('已删除')
    await reload()
  } catch (err) {
    ElMessage.warning(err?.response?.data?.detail || '删除失败')
  }
}

onMounted(async () => {
  await reload()
  try {
    const res = await vaultApi.uploaders()
    uploaders.value = res?.data?.list || []
  } catch { /* 家人列表拿不到不影响主流程 */ }
})
</script>

<style scoped>
.va-page { min-height: 100vh; }
.va-inner { max-width: 1080px; margin: 0 auto; padding: 84px 20px 40px; }

.va-head { display: flex; align-items: center; gap: 14px; margin-bottom: 14px; flex-wrap: wrap; }
.va-titles { flex: 1; min-width: 180px; }
.va-title { margin: 0; font-size: 22px; letter-spacing: .1em; color: var(--lj-text); }
.va-sub { margin: 2px 0 0; font-size: 12px; color: var(--lj-text-2); letter-spacing: .06em; }
.va-head-right { display: flex; gap: 8px; margin-left: auto; }

.va-btn {
  border-radius: 9px; padding: 8px 16px; font-size: 13px; cursor: pointer;
  border: 1px solid var(--lj-line); background: transparent; color: var(--lj-text);
  font-family: inherit; transition: all .2s;
}
.va-btn:hover { border-color: var(--lj-line-strong); color: var(--lj-seal); }
.va-btn.primary { background: var(--lj-ink, #18181b); color: var(--lj-paper, #fff); border-color: transparent; }
.va-btn.tiny { padding: 4px 10px; font-size: 12px; }
.va-btn.danger { color: var(--pnl-up, #c2432f); }
.va-btn:disabled { opacity: .6; cursor: default; }

.va-notice { display: flex; gap: 10px; align-items: flex-start; padding: 11px 16px; border-radius: 12px;
  background: rgba(199,169,107,.1); font-size: 12px; line-height: 1.75; color: var(--lj-text-2); margin-bottom: 14px; }
.va-notice b { color: var(--lj-seal); }
.va-notice-ic { font-size: 15px; line-height: 1.4; }

.va-input { background: rgba(74,95,99,.08); border: 1px solid var(--lj-line); color: var(--lj-text);
  border-radius: 8px; padding: 8px 11px; font-size: 13px; font-family: inherit; min-width: 200px; flex: 1 1 200px; }
.va-input:focus { outline: none; border-color: var(--lj-seal); }
.va-select { flex: 0 0 150px; min-width: 140px; }

.va-empty { padding: 48px 20px; text-align: center; color: var(--lj-text-3); font-size: 13.5px; line-height: 1.9; }
.va-list { display: flex; flex-direction: column; gap: 10px; }

.va-card { display: flex; gap: 12px; padding: 12px 14px; border-radius: 14px; align-items: flex-start; }
.va-card-ic { width: 40px; height: 40px; flex: none; border-radius: 11px; background: rgba(74,95,99,.08);
  display: flex; align-items: center; justify-content: center; font-size: 19px; }
.va-card-main { flex: 1; min-width: 0; }
.va-name-row { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.va-name { font-size: 15px; font-weight: 600; color: var(--lj-text); }
.va-cat { font-size: 11px; padding: 1px 7px; border-radius: 999px; background: rgba(127,168,163,.14); color: var(--lj-text-2); }
.va-owner { font-size: 11px; color: var(--lj-text-3); margin-left: auto; }
.va-fields { display: flex; gap: 18px; flex-wrap: wrap; margin-top: 6px; }
.va-field { font-size: 12.5px; color: var(--lj-text); display: inline-flex; align-items: center; gap: 6px; }
.va-field i { font-style: normal; font-size: 11px; color: var(--lj-text-3); }
.va-pwd { font-family: ui-monospace, Menlo, Consolas, monospace; letter-spacing: .08em; }
.va-mini { border: 1px solid var(--lj-line); background: transparent; color: var(--lj-text-2);
  border-radius: 6px; font-size: 11px; padding: 1px 7px; cursor: pointer; font-family: inherit; }
.va-mini:hover { border-color: var(--lj-line-strong); color: var(--lj-seal); }
.va-link { color: var(--lj-seal); text-decoration: none; }
.va-note { margin: 7px 0 0; font-size: 12px; color: var(--lj-text-2); line-height: 1.7; }
.va-card-actions { display: flex; gap: 6px; flex: none; }
.va-pwd-row { display: flex; gap: 8px; width: 100%; align-items: center; }
.va-pwd-row .el-input { flex: 1; }

@media (max-width: 760px) {
  .va-inner { padding: 74px 14px 32px; }
  .va-head-right { width: 100%; }
  .va-head-right .va-btn { flex: 1; }
  .va-select { flex: 1 1 44%; min-width: 0; }
  .va-owner { margin-left: 0; width: 100%; }
  .va-card { flex-wrap: wrap; }
  .va-card-actions { margin-left: 52px; }
  .va-fields { gap: 10px; }
}
</style>
