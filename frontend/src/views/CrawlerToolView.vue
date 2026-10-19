<template>
  <!-- v2.46.120 通用爬虫工具（夜星：后续支持爬任意平台/网址的数据）
       服务端代理抓取（免 CORS）：SSRF 拦截 / 3MB 上限 / 15s 超时；
       仅公开内容，不绕过登录、验证码与付费——目标站规则与版权提示常驻。 -->
  <IslandInnerBase type="tool" title="网页爬虫" subtitle="URL 抓取 · 正文/链接/图片/表格提取">
    <div class="cw">
      <div class="cw-row">
        <el-input
          v-model="url" placeholder="https:// 目标页面地址" clearable
          @keyup.enter="doFetch"
        />
        <el-select v-model="mode" style="width: 128px">
          <el-option label="正文文本" value="text" />
          <el-option label="链接列表" value="links" />
          <el-option label="图片列表" value="images" />
          <el-option label="表格数据" value="tables" />
          <el-option label="原始 HTML" value="html" />
        </el-select>
        <el-button type="primary" :loading="loading" @click="doFetch">抓取</el-button>
      </div>
      <p class="cw-note">仅抓公开内容（不绕过登录/验证码/付费）；请遵守目标站 robots.txt 与版权，数据仅限个人使用。</p>

      <el-alert v-if="err" :title="err" type="error" :closable="false" show-icon />

      <template v-if="result">
        <div class="cw-meta">
          <span v-if="result.title">标题：{{ result.title }}</span>
          <span v-if="result.total !== undefined">共 {{ result.total }} 条</span>
          <span class="cw-ops">
            <el-button size="small" plain @click="copyOut">复制</el-button>
            <el-button size="small" plain @click="downloadJson">下载 JSON</el-button>
            <el-button v-if="mode === 'tables'" size="small" plain @click="downloadCsv">下载 CSV</el-button>
          </span>
        </div>

        <pre v-if="mode === 'text'" class="cw-pre">{{ result.text }}</pre>
        <pre v-else-if="mode === 'html'" class="cw-pre">{{ result.html }}</pre>

        <el-table v-else-if="mode === 'links'" :data="result.links" size="small" max-height="460">
          <el-table-column prop="text" label="文字" min-width="180" show-overflow-tooltip />
          <el-table-column prop="href" label="链接" min-width="260" show-overflow-tooltip />
        </el-table>

        <div v-else-if="mode === 'images'" class="cw-imgs">
          <figure v-for="(im, i) in result.images" :key="i">
            <img :src="im.src" loading="lazy" referrerpolicy="no-referrer" :alt="im.alt" />
            <figcaption>{{ im.alt || im.src.slice(0, 60) }}</figcaption>
          </figure>
        </div>

        <div v-else-if="mode === 'tables'" class="cw-tables">
          <el-table
            v-for="(tb, ti) in result.tables" :key="ti"
            :data="tb.slice(1)" size="small" max-height="320"
            style="margin-bottom: 16px"
          >
            <el-table-column
              v-for="(h, hi) in tb[0]" :key="hi"
              :prop="String(hi)" :label="h || `列${hi + 1}`" min-width="110"
              show-overflow-tooltip
            >
              <template #default="{ row }">{{ row[hi] }}</template>
            </el-table-column>
          </el-table>
          <p v-if="!result.tables?.length" class="cw-empty">该页面未发现表格。</p>
        </div>
      </template>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { crawlerApi } from '@/api/crawler'

defineOptions({ name: 'CrawlerToolView' })

const url = ref('')
const mode = ref('text')
const loading = ref(false)
const err = ref('')
const result = ref(null)

async function doFetch() {
  if (!url.value.trim()) { ElMessage.warning('先填目标地址'); return }
  loading.value = true
  err.value = ''
  result.value = null
  try {
    const res = await crawlerApi.fetch({ url: url.value.trim(), mode: mode.value })
    if (res.data?.code === 1) { err.value = res.data.msg || '抓取失败'; return }
    result.value = res.data?.data || {}
  } catch (e) {
    err.value = e?.response?.data?.msg || e?.message || '请求失败'
  } finally { loading.value = false }
}

function serialize() {
  return mode.value === 'text' ? (result.value.text || '')
    : mode.value === 'html' ? (result.value.html || '')
    : JSON.stringify(result.value, null, 2)
}

async function copyOut() {
  try { await navigator.clipboard.writeText(serialize()); ElMessage.success('已复制') }
  catch { ElMessage.error('复制失败，请手动选择') }
}

function saveBlob(text, name, mime) {
  const blob = new Blob([text], { type: mime })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = name
  a.click()
  URL.revokeObjectURL(a.href)
}

function downloadJson() {
  saveBlob(serialize(), `crawl-${Date.now()}.json`, 'application/json')
}

function downloadCsv() {
  const rows = (result.value.tables || []).flat()
  const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
  const csv = rows.map((r) => r.map(esc).join(',')).join('\n')
  saveBlob('\ufeff' + csv, `crawl-${Date.now()}.csv`, 'text/csv;charset=utf-8')
}
</script>

<style scoped>
.cw { display: flex; flex-direction: column; gap: 14px; }
.cw-row { display: flex; gap: 10px; flex-wrap: wrap; }
.cw-row .el-input { flex: 1; min-width: 260px; }
.cw-note { margin: 0; font-size: 12px; color: var(--ls-text-3, var(--color-text-secondary)); line-height: 1.7; }
.cw-meta {
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  font-size: 12.5px; color: var(--ls-text-2, var(--color-text-secondary));
}
.cw-ops { margin-left: auto; display: flex; gap: 8px; }
.cw-pre {
  margin: 0; padding: 14px 16px; border-radius: 12px; max-height: 520px; overflow: auto;
  background: var(--dp-surface2, rgba(127, 168, 163, .08)); border: 1px solid var(--dp-line, var(--ls-line));
  font-size: 12.5px; line-height: 1.8; white-space: pre-wrap; word-break: break-word;
  color: var(--color-text);
}
.cw-imgs { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
.cw-imgs figure { margin: 0; }
.cw-imgs img {
  width: 100%; height: 110px; object-fit: cover; border-radius: 10px;
  background: rgba(127, 168, 163, .1); border: 1px solid var(--dp-line, var(--ls-line));
}
.cw-imgs figcaption { font-size: 11px; color: var(--color-text-secondary); margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cw-tables :deep(.el-table) {
  --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: transparent; --el-table-border-color: var(--dp-line, var(--ls-line));
}
.cw-empty { color: var(--color-text-secondary); font-size: 12.5px; }
</style>
