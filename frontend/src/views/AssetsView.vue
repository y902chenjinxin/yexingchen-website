<template>
  <div class="assets-page">
    <header class="assets-header">
      <h1>内容资产</h1>
      <div>
        <el-button @click="showLink = true">添加网页</el-button>
        <label class="upload-btn">
          上传文件
          <input type="file" accept="image/*,application/pdf" hidden @change="onUpload" />
        </label>
      </div>
    </header>

    <div class="assets-toolbar">
      <el-select v-model="typeFilter" placeholder="类型" clearable @change="reload" style="width:140px">
        <el-option label="网页" value="link" />
        <el-option label="图片" value="image" />
        <el-option label="PDF" value="pdf" />
      </el-select>
      <el-input v-model="keyword" placeholder="搜索标题/描述/URL" clearable @keyup.enter="reload" style="max-width:280px" />
    </div>

    <ul v-if="items.length" class="assets-grid">
      <li v-for="a in items" :key="a.id" class="asset-card">
        <div class="asset-preview">
          <img
            v-if="a.type === 'image' && a.objectUrl"
            :src="a.objectUrl"
            :alt="a.title"
          />
          <span v-else-if="a.type === 'image' && !a.objectUrl" class="asset-loading">图片加载失败</span>
          <iframe
            v-else-if="a.type === 'pdf' && a.objectUrl"
            :src="a.objectUrl"
            class="asset-pdf"
          />
          <span v-else-if="a.type === 'pdf' && !a.objectUrl" class="asset-loading">PDF 加载失败</span>
          <a v-else-if="a.type === 'link'" :href="a.url" target="_blank" rel="noopener noreferrer" class="asset-link-card">
            🔗 {{ a.url }}
          </a>
        </div>
        <div class="asset-info">
          <h4>{{ a.title || '（无标题）' }}</h4>
          <p v-if="a.description">{{ a.description }}</p>
          <div class="asset-meta">
            <span v-for="t in a.tags" :key="t" class="asset-tag">#{{ t }}</span>
            <span class="asset-size">{{ humanSize(a.file_size) }}</span>
          </div>
          <div class="asset-actions">
            <!-- 使用 button 而非 <a>：避免点击瞬间 href="#" 触发导航；
                 点击后 preventDefault + 异步 fetchBlob，成功后创建临时下载链接 -->
            <button
              v-if="a.type === 'image' || a.type === 'pdf'"
              type="button"
              class="link-btn"
              :data-asset-id="a.id"
              :data-asset-title="a.title || ''"
              @click.prevent="onDownload(a)"
            >下载</button>
            <el-button size="small" type="danger" plain @click="remove(a)">删除</el-button>
          </div>
        </div>
      </li>
    </ul>
    <p v-else class="assets-empty">还没有内容资产。点击右上角添加。</p>

    <el-pagination
      v-model:current-page="page"
      :page-size="size"
      :total="total"
      layout="prev, pager, next, total"
      class="assets-pager"
      @current-change="reload"
    />

    <el-dialog v-model="showLink" title="添加网页" width="480px">
      <el-form :model="linkForm" label-width="64px">
        <el-form-item label="URL">
          <el-input v-model="linkForm.url" placeholder="https://…" />
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="linkForm.title" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="linkForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="linkForm.tagInput" placeholder="逗号分隔" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showLink = false">取消</el-button>
        <el-button type="primary" :disabled="!linkForm.url" @click="submitLink">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { workbenchApi } from '@/api/workbench'

const route = useRoute()
const items = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(12)
const typeFilter = ref(route.query.type || '')
const keyword = ref(route.query.q || '')

const showLink = ref(false)
const linkForm = ref({ url: '', title: '', description: '', tagInput: '' })

// object URL 缓存
const objectUrls = new Map()
// 当前正在下载的 assetId（防止并发点击同一资产造成重复下载）
const downloadingIds = new Set()
// 临时下载用 object URL（点击 → 创建 → 触发 → 5s 后 revoke）
const tempDownloadUrls = new Set()

function humanSize(n) {
  if (!n) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let s = n
  for (const u of units) {
    if (s < 1024) return `${s.toFixed(1)} ${u}`
    s /= 1024
  }
  return `${s.toFixed(1)} TB`
}

function revokeAllUrls() {
  for (const url of objectUrls.values()) URL.revokeObjectURL(url)
  objectUrls.clear()
}

/**
 * 触发浏览器下载：用临时 <a download> 触发，不依赖 href 初始值，避免竞态。
 * - 必须在 user gesture 中创建（fetchBlob 已完成，再创建 a 即可）
 * - 5s 后自动 revoke 临时 object URL
 */
function triggerBrowserDownload(blob, filename) {
  const url = URL.createObjectURL(blob)
  tempDownloadUrls.add(url)
  const a = document.createElement('a')
  a.href = url
  a.download = filename || 'download'
  a.style.display = 'none'
  a.rel = 'noopener'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => {
    if (tempDownloadUrls.has(url)) {
      tempDownloadUrls.delete(url)
      URL.revokeObjectURL(url)
    }
  }, 5000)
}

watch(() => route.query, (q) => {
  typeFilter.value = q.type || ''
  keyword.value = q.q || ''
  page.value = 1
  reload()
})

async function loadBlobFor(a) {
  if (a.type !== 'image' && a.type !== 'pdf') return
  if (objectUrls.has(a.id)) return
  try {
    const { objectUrl } = await workbenchApi.assets.fetchBlob(a.id, 'preview')
    a.objectUrl = objectUrl
    objectUrls.set(a.id, objectUrl)
  } catch (e) {
    ElMessage.warning('资源加载失败：' + (a.title || a.id))
  }
}

async function reload() {
  const params = { page: page.value, size: size.value }
  if (typeFilter.value) params.type = typeFilter.value
  if (keyword.value) params.q = keyword.value
  const res = await workbenchApi.assets.list(params)
  // 释放旧的 object URL（列表项变了）
  revokeAllUrls()
  const list = (res.data.list || []).map(a => ({ ...a, objectUrl: null }))
  items.value = list
  total.value = res.data.total || 0
  // 为每个图片/PDF 加载鉴权 blob URL
  for (const a of list) {
    loadBlobFor(a)
  }
}

async function onUpload(e) {
  const f = e.target.files?.[0]
  e.target.value = ''
  if (!f) return
  const form = new FormData()
  form.append('file', f)
  form.append('title', f.name)
  try {
    await workbenchApi.assets.upload(form)
    ElMessage.success('已上传')
    reload()
  } catch (err) {
    if (err?.response?.status === 413) ElMessage.error('文件超过大小限制')
    else ElMessage.error('上传失败：' + (err?.response?.data?.msg || err.message))
  }
}

async function submitLink() {
  const tag_names = (linkForm.value.tagInput || '').split(',').map(s => s.trim()).filter(Boolean)
  try {
    await workbenchApi.assets.createLink({
      url: linkForm.value.url,
      title: linkForm.value.title,
      description: linkForm.value.description,
      tag_names,
    })
    showLink.value = false
    linkForm.value = { url: '', title: '', description: '', tagInput: '' }
    reload()
  } catch (e) {
    ElMessage.error('保存失败：' + (e?.response?.data?.msg || e.message))
  }
}

async function remove(a) {
  try {
    await ElMessageBox.confirm(`确认删除「${a.title || '该资产'}」？将进入回收站。`, '提示', { type: 'warning' })
  } catch { return }
  await workbenchApi.assets.delete(a.id)
  reload()
}

/**
 * 点击"下载"按钮的真正下载逻辑：
 * - 通过 fetchBlob('download') 拿到带 Bearer 的 blob；
 * - 创建临时 <a download> 触发浏览器下载；
 * - 不修改卡片本身的 objectUrl，避免影响预览。
 */
async function onDownload(a) {
  if (!a || (a.type !== 'image' && a.type !== 'pdf')) return
  if (downloadingIds.has(a.id)) return // 防止并发重复下载
  downloadingIds.add(a.id)
  try {
    const { blob } = await workbenchApi.assets.fetchBlob(a.id, 'download')
    // blob 是从 Auth 后的对象 URL 切片出来的；不要把 blob 转 blob:URL 后长期持有。
    // 直接用 fetch 出来的 Response.blob(...) — 这里实际是 workbenchApi 已 createObjectURL。
    // 为避免依赖泄露，沿用 fetchBlob 返回的 blob，并通过临时 URL 触发下载。
    triggerBrowserDownload(blob, a.title || `asset-${a.id}`)
  } catch (e) {
    ElMessage.error('下载失败：' + (e?.response?.data?.msg || e.message || '未知错误'))
  } finally {
    downloadingIds.delete(a.id)
  }
}

onBeforeUnmount(() => {
  revokeAllUrls()
  // 清理临时下载 URL
  for (const u of tempDownloadUrls) URL.revokeObjectURL(u)
  tempDownloadUrls.clear()
})

onMounted(reload)
</script>

<style scoped>
.assets-page { max-width: 1100px; margin: 0 auto; padding: 24px 16px 80px; }
.assets-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.assets-header h1 { font-size: 22px; margin: 0; }
.upload-btn { display: inline-block; padding: 8px 14px; background: var(--paper-white); border: 1px solid var(--rattan-yellow); border-radius: var(--radius-sm); cursor: pointer; margin-left: 8px; }
.upload-btn:hover { background: var(--paper-white)8e6; }
.assets-toolbar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
.assets-grid { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
.asset-card { background: var(--paper-white); border: 1px solid var(--paper-aged); border-radius: var(--radius-sm); overflow: hidden; display: flex; flex-direction: column; }
.asset-preview { background: var(--paper-white); height: 160px; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.asset-preview img { max-width: 100%; max-height: 100%; object-fit: contain; }
.asset-pdf { width: 100%; height: 100%; border: 0; }
.asset-link-card { color: var(--ochre); padding: 16px; text-align: center; word-break: break-all; font-size: 13px; }
.asset-loading { color: var(--color-text-muted); font-size: 12px; }
.asset-info { padding: 10px 12px; flex: 1; display: flex; flex-direction: column; gap: 6px; }
.asset-info h4 { font-size: 14px; margin: 0; }
.asset-info p { font-size: 12px; color: var(--color-text-muted); margin: 0; }
.asset-meta { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.asset-tag { color: var(--ochre); font-size: 11px; }
.asset-size { color: var(--color-text-muted); font-size: 11px; }
.asset-actions { display: flex; justify-content: space-between; align-items: center; margin-top: auto; }
.link-btn {
  background: transparent;
  border: 0;
  color: var(--ochre);
  font-size: 12px;
  cursor: pointer;
  padding: 0;
}
.link-btn:hover { text-decoration: underline; }
.assets-empty { color: var(--color-text-muted); text-align: center; padding: 40px 0; }
.assets-pager { margin-top: 16px; text-align: right; }
</style>