<template>
  <div class="fd-page">
    <div class="lj-bg" aria-hidden="true">
      <div class="lj-paper-texture"></div>
      <div class="lj-wash w1"></div>
      <div class="lj-wash w2"></div>
    </div>

    <div class="fd-inner">
      <!-- 页头 -->
      <header class="fd-head">
        <div class="fd-head-left">
          <BackButton class="fd-back" />
        </div>
        <div class="fd-titles">
          <h1 class="fd-title">资讯推送</h1>
          <p class="fd-sub">订阅源 · 智能摘要 · 一键收藏</p>
        </div>
        <div class="fd-head-right">
          <button class="fd-btn ghost" :disabled="refreshing" @click="refreshAll">{{ refreshing ? '刷新中…' : '⟳ 刷新全部' }}</button>
          <button class="fd-btn primary" @click="openAdd">{{ adding ? '关闭' : '＋ 添加订阅' }}</button>
        </div>
      </header>

      <!-- 添加 / 编辑订阅源（内联面板） -->
      <transition name="fd-panel">
        <section v-if="adding" class="fd-form glass">
          <div class="fd-form-head">
            <span class="fd-form-title">{{ form.id ? '编辑订阅源' : '添加订阅源' }}</span>
            <span class="fd-form-hint">填入公开的 RSS 地址，抓取后自动入库</span>
            <button class="fd-form-close" @click="closeForm">✕</button>
          </div>
          <div class="fd-form-row">
            <div class="fd-f-field grow">
              <label class="fd-f-label">RSS 地址</label>
              <input v-model="form.feed_url" class="fd-input" placeholder="https://example.com/rss.xml"
                     spellcheck="false" @keyup.enter="saveSource" />
            </div>
            <div class="fd-f-field">
              <label class="fd-f-label">分类</label>
              <input v-model="form.category" class="fd-input" placeholder="综合" maxlength="16" />
            </div>
            <div class="fd-f-field">
              <label class="fd-f-label">自定义标题（可选）</label>
              <input v-model="form.title" class="fd-input" placeholder="留空自动识别" maxlength="60" />
            </div>
          </div>
          <div class="fd-form-actions">
            <span class="fd-save-tip">保存后会自动抓取一次该源的最新文章</span>
            <button class="fd-btn primary" :disabled="saving" @click="saveSource">{{ saving ? '保存中…' : '保存并抓取' }}</button>
          </div>
        </section>
      </transition>

      <!-- 三栏主体 -->
      <div class="fd-grid">
        <!-- 左栏：订阅源 -->
        <aside class="fd-col fd-source glass">
          <div class="fd-col-head">
            <h2 class="fd-col-title">订阅源</h2>
            <span class="fd-count">{{ sources.length }}</span>
          </div>
          <div v-if="!sourceLoading" class="fd-source-list">
            <button
              v-for="s in sources"
              :key="s.id"
              class="fd-source-item"
              :class="{ active: activeSourceId !== 0 && activeSourceId === s.id }"
              @click="pickSource(s)"
            >
              <span class="fd-si-dot" :class="statusClass(s)"></span>
              <span class="fd-si-main">
                <span class="fd-si-title">{{ s.title || '未命名源' }}</span>
                <span class="fd-si-cat">{{ s.category }} · {{ s.article_count }} 篇</span>
              </span>
              <span class="fd-si-ops">
                <button class="fd-op" title="抓取" @click.stop="fetchOne(s)">⟳</button>
                <button class="fd-op" title="编辑" @click.stop="openEdit(s)">✎</button>
                <el-popconfirm
                  title="确认删除这个订阅源？"
                  confirm-button-text="删除"
                  cancel-button-text="取消"
                  width="220"
                  @confirm="delSource(s)"
                >
                  <template #reference>
                    <button class="fd-op danger" title="删除">🗑</button>
                  </template>
                </el-popconfirm>
              </span>
            </button>
            <div v-if="!sources.length" class="fd-col-empty">
              还没有订阅源<br /><span class="fd-empty-sub">点击右上角「添加订阅」开始</span>
            </div>
          </div>
          <div v-else class="fd-col-loading">加载中…</div>
        </aside>

        <!-- 中栏：文章列表 -->
        <section class="fd-col fd-list glass">
          <div class="fd-col-head">
            <h2 class="fd-col-title">{{ listTitle }}</h2>
            <div class="fd-list-filters">
              <select v-model="filter" class="fd-select" @change="reload(1)">
                <option value="all">全部</option>
                <option value="unread">未读</option>
                <option value="bookmarked">已收藏</option>
              </select>
              <input v-model="q" class="fd-search" placeholder="搜索标题…"
                     spellcheck="false" @keyup.enter="reload(1)" />
            </div>
          </div>

          <div v-if="!loading" class="fd-article-list">
            <button
              v-for="a in list"
              :key="a.id"
              class="fd-article"
              :class="{ active: activeId === a.id, unread: !a.read }"
              @click="openArticle(a)"
            >
              <span class="fd-a-dot" v-if="!a.read"></span>
              <span class="fd-a-main">
                <span class="fd-a-title">{{ a.title || '无标题' }}</span>
                <span class="fd-a-meta">
                  <span class="fd-a-source">{{ a.source_title }}</span>
                  <span class="fd-a-time">{{ fmtTime(a.published_at) }}</span>
                  <span v-if="a.ai_summary" class="fd-a-badge">AI 摘要</span>
                  <span v-if="a.bookmarked" class="fd-a-star">★</span>
                </span>
                <span v-if="a.summary" class="fd-a-excerpt">{{ a.summary }}</span>
              </span>
            </button>
            <div v-if="!list.length" class="fd-col-empty">暂无文章，点「刷新全部」拉取最新内容</div>
          </div>
          <div v-else class="fd-col-loading">加载中…</div>

          <div class="fd-pager">
            <span class="fd-pager-info">共 {{ total }} 篇</span>
            <el-pagination
              layout="prev, pager, next"
              :total="total"
              :page-size="pageSize"
              :current-page="page"
              background
              small
              @current-change="onPage"
            />
          </div>
        </section>

        <!-- 右栏：文章阅读 + AI -->
        <section class="fd-col fd-reader glass">
          <template v-if="active">
            <div class="fd-reader-head">
              <div class="fd-r-titles">
                <h2 class="fd-r-title">{{ active.title }}</h2>
                <div class="fd-r-meta">
                  <span>{{ active.source_title }}</span>
                  <span v-if="active.author"> · {{ active.author }}</span>
                  <span v-if="active.published_at"> · {{ fmtTime(active.published_at) }}</span>
                </div>
              </div>
            </div>

            <!-- AI 摘要 -->
            <div class="fd-sum glass">
              <div class="fd-sum-head">
                <span class="fd-sum-label">AI 摘要</span>
                <span v-if="aiLoading" class="fd-sum-loading">生成中…</span>
                <div class="fd-sum-actions">
                  <button v-if="!active.ai_summary && !aiLoading" class="fd-btn ghost small" @click="genSummary">生成摘要</button>
                  <button v-if="active.ai_summary && !aiLoading" class="fd-btn ghost small" @click="genSummary">重新生成</button>
                </div>
              </div>
              <div v-if="active.ai_summary" class="fd-sum-body">
                <p class="fd-sum-text">{{ active.ai_summary }}</p>
              </div>
              <div v-else-if="!aiLoading" class="fd-sum-empty">点击「生成摘要」，让 AI 为你提炼本文要点</div>
            </div>

            <!-- 原文摘要 + 正文 -->
            <div class="fd-reader-body">
              <p v-if="active.summary" class="fd-body-sum">{{ active.summary }}</p>
              <p v-if="active.content" class="fd-body">{{ active.content }}</p>
              <div class="fd-body-actions">
                <a v-if="active.link" class="fd-body-orig" :href="active.link" target="_blank" rel="noopener noreferrer">阅读原文 ↗</a>
              </div>
            </div>

            <!-- 操作栏（收藏到笔记 / 收藏 / 删除） -->
            <div class="fd-reader-ops">
              <button class="fd-btn primary" :disabled="noteSaving" @click="toNote">
                {{ noteSaving ? '保存中…' : '📌 收藏为笔记' }}
              </button>
              <button class="fd-btn ghost" :class="{ starred: active.bookmarked }" @click="toggleBook">
                {{ active.bookmarked ? '★ 已收藏' : '☆ 收藏文章' }}
              </button>
              <el-popconfirm
                title="删除这篇文章？"
                confirm-button-text="删除"
                cancel-button-text="取消"
                width="200"
                @confirm="delArticle"
              >
                <template #reference>
                  <button class="fd-btn ghost danger">🗑 删除</button>
                </template>
              </el-popconfirm>
            </div>
          </template>
          <div v-else class="fd-col-empty reader-placeholder">
            <span class="fd-rp-icon">📰</span>
            从左侧选择一篇文章开始阅读
          </div>
        </section>
      </div>

      <!-- 网安标识 -->
      <footer class="fd-foot">
        <span>心之所向，素履以往</span>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import BackButton from '@/components/BackButton.vue'
import { feedsApi } from '@/api/feeds'

const sources = ref([])
const sourceLoading = ref(true)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const filter = ref('all')
const q = ref('')
const activeId = ref(null)
const active = ref(null)
const activeSourceId = ref(0)
const refreshing = ref(false)
const saving = ref(false)
const aiLoading = ref(false)
const noteSaving = ref(false)

const form = reactive({ id: null, feed_url: '', title: '', category: '综合' })
const adding = ref(false)

const listTitle = computed(() => {
  if (activeSourceId.value) {
    const s = sources.value.find(x => x.id === activeSourceId.value)
    return s ? s.title : '文章列表'
  }
  return '最新文章'
})

function statusClass(s) {
  if (s.last_status === 1) return 'ok'
  if (s.last_status === 2) return 'err'
  return 'idle'
}

function fmtTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d)) return iso.slice(0, 10)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

async function loadSources() {
  sourceLoading.value = true
  try {
    const res = await feedsApi.sources()
    sources.value = res.data.list || []
  } finally {
    sourceLoading.value = false
  }
}

function loadListParams() {
  const params = { page: page.value, size: pageSize }
  if (activeSourceId.value) params.source_id = activeSourceId.value
  if (filter.value === 'unread') params.read = 0
  if (filter.value === 'bookmarked') params.bookmarked = 1
  if (q.value.trim()) params.q = q.value.trim()
  return params
}

async function loadList() {
  loading.value = true
  try {
    const res = await feedsApi.list(loadListParams())
    list.value = res.data.list || []
    total.value = res.data.total || 0
  } finally {
    loading.value = false
  }
}

function reload(p) {
  if (p) page.value = p
  return loadList()
}
function onPage(p) {
  page.value = p
  loadList()
}

function pickSource(s) {
  activeSourceId.value = activeSourceId.value === s.id ? 0 : s.id
  page.value = 1
  loadList()
}

async function openArticle(a) {
  activeId.value = a.id
  active.value = { ...a }
  // 补充正文（列表不含 content）
  try {
    const res = await feedsApi.get(a.id)
    const fresh = res.data
    active.value = fresh
    // 更新列表里的未读状态
    const idx = list.value.findIndex(x => x.id === a.id)
    if (idx >= 0) list.value[idx].read = fresh.read
    if (!fresh.read) list.value[idx].read = 1
  } catch (e) { /* 保留列表摘要 */ }
}

function openAdd() {
  Object.assign(form, { id: null, feed_url: '', title: '', category: '综合' })
  adding.value = true
}
function openEdit(s) {
  Object.assign(form, { id: s.id, feed_url: s.feed_url, title: s.title, category: s.category })
  adding.value = true
}
function closeForm() {
  adding.value = false
}

async function saveSource() {
  const url = (form.feed_url || '').trim()
  if (!url) {
    ElMessage.warning('请填写 RSS 地址')
    return
  }
  saving.value = true
  const payload = { feed_url: url, title: form.title.trim(), category: form.category.trim() || '综合' }
  try {
    if (form.id) {
      await feedsApi.updateSource(form.id, payload)
      ElMessage.success('已更新订阅源')
      await fetchOne({ id: form.id })
    } else {
      const res = await feedsApi.addSource(payload)
      const s = res.data
      ElMessage.success(s.last_status === 1 ? '已添加并抓取文章' : '已添加（抓取失败，可稍后重试）')
    }
    adding.value = false
    await loadSources()
    await loadList()
  } finally {
    saving.value = false
  }
}

async function fetchOne(s) {
  try {
    const res = await feedsApi.fetchSource(s.id)
    ElMessage.success(res.data.added ? `抓取到 ${res.data.added} 篇新文章` : '没有新文章')
  } catch (e) {
    ElMessage.error('抓取失败')
  } finally {
    await loadSources()
    await loadList()
  }
}

async function refreshAll() {
  refreshing.value = true
  try {
    const res = await feedsApi.fetchAll()
    const rs = res.data.results || []
    const n = rs.reduce((a, r) => a + (r.added || 0), 0)
    ElMessage.success(`刷新完成，共更新 ${n} 篇`)
  } catch (e) {
    ElMessage.error('刷新失败')
  } finally {
    refreshing.value = false
    await loadSources()
    await loadList()
  }
}

async function delSource(s) {
  await feedsApi.deleteSource(s.id)
  if (activeSourceId.value === s.id) {
    activeSourceId.value = 0
    page.value = 1
    loadList()
  }
  ElMessage.success('已删除订阅源')
  await loadSources()
}

async function genSummary() {
  if (!active.value) return
  aiLoading.value = true
  try {
    const res = await feedsApi.summary(active.value.id)
    active.value.ai_summary = res.data.ai_summary
    const idx = list.value.findIndex(x => x.id === active.value.id)
    if (idx >= 0) list.value[idx].ai_summary = res.data.ai_summary
    ElMessage.success('摘要已生成')
  } catch (e) {
    ElMessage.error('生成失败')
  } finally {
    aiLoading.value = false
  }
}

async function toggleBook() {
  if (!active.value) return
  const res = await feedsApi.toggleBookmark(active.value.id)
  active.value.bookmarked = res.data.bookmarked
  const idx = list.value.findIndex(x => x.id === active.value.id)
  if (idx >= 0) list.value[idx].bookmarked = res.data.bookmarked
}

async function toNote() {
  if (!active.value) return
  noteSaving.value = true
  try {
    const res = await feedsApi.toNote(active.value.id, { with_summary: true })
    ElMessage.success(`已收藏为笔记「${res.data.title}」`)
    active.value.bookmarked = 1
    const idx = list.value.findIndex(x => x.id === active.value.id)
    if (idx >= 0) list.value[idx].bookmarked = 1
  } catch (e) {
    ElMessage.error('收藏失败')
  } finally {
    noteSaving.value = false
  }
}

async function delArticle() {
  const id = active.value.id
  await feedsApi.delArticle(id)
  list.value = list.value.filter(x => x.id !== id)
  total.value = Math.max(0, total.value - 1)
  active.value = null
  activeId.value = null
  ElMessage.success('已删除')
}

onMounted(() => {
  loadSources()
  loadList()
})
</script>

<style scoped>
.fd-page {
  position: relative;
  min-height: 100vh;
  padding: 96px 24px 60px;
  box-sizing: border-box;
  font-family: var(--font-serif);
  color: var(--lj-text);
  overflow-x: hidden;
}
.fd-inner { position: relative; z-index: 1; max-width: 1280px; margin: 0 auto; }

.lj-bg { position: absolute; inset: 0; z-index: 0; pointer-events: none; overflow: hidden;
  background:
    radial-gradient(ellipse 55% 40% at 18% 6%, var(--glow-rain), transparent 60%),
    radial-gradient(ellipse 45% 40% at 85% 26%, var(--glow-gold), transparent 60%),
    var(--lj-bg); }
.lj-paper-texture { position: absolute; inset: 0; opacity: .5;
  background:
    repeating-linear-gradient(0deg, rgba(127,168,163,.02) 0 1px, transparent 1px 5px),
    repeating-linear-gradient(90deg, rgba(127,168,163,.014) 0 1px, transparent 1px 7px); }
.lj-wash { position: absolute; border-radius: 50%; filter: blur(80px); opacity: .4;
  background: radial-gradient(circle, rgba(127,168,163,.14), transparent 70%); animation: fd-drift 30s ease-in-out infinite; }
.lj-wash.w1 { width: 480px; height: 400px; top: 4%; left: -8%; }
.lj-wash.w2 { width: 420px; height: 360px; bottom: 4%; right: -8%; animation-delay: 9s; }
@keyframes fd-drift { 0%,100% { transform: translate(0,0); } 50% { transform: translate(32px,-18px); } }
@media (prefers-reduced-motion: reduce) { .lj-wash { animation: none; } }

.glass { background: var(--lj-glass); -webkit-backdrop-filter: var(--lj-glass-blur); backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line); box-shadow: var(--glass-highlight), var(--glass-shadow); }

/* 页头 */
.fd-head { display: flex; align-items: center; gap: 18px; margin-bottom: 18px; }
.fd-head-left { flex: none; }
.fd-titles { flex: 1; }
.fd-title { margin: 0; font-size: 28px; letter-spacing: .12em; }
.fd-sub { margin: 6px 0 0; font-size: 12px; color: var(--lj-text-2); letter-spacing: .18em; }
.fd-head-right { flex: none; display: flex; gap: 10px; flex-wrap: wrap; }

.fd-btn { border: none; cursor: pointer; border-radius: 10px; font-family: var(--font-serif);
  color: var(--lj-text); background: var(--lj-glass); border: 1px solid var(--lj-line); padding: 9px 16px; transition: all .22s; }
.fd-btn:hover:not(:disabled) { border-color: var(--lj-line-strong); }
.fd-btn:disabled { opacity: .6; cursor: not-allowed; }
.fd-btn.primary { background: linear-gradient(135deg, rgba(127,168,163,.55), rgba(199,169,107,.4)); color: #fff; }
.fd-btn.primary:hover:not(:disabled) { filter: brightness(1.05); box-shadow: 0 6px 18px rgba(0,0,0,.25); }
.fd-btn.ghost { background: transparent; }
.fd-btn.small { padding: 6px 12px; font-size: 13px; }
.fd-btn.starred { border-color: var(--lj-ochre); color: var(--lj-ochre); }
.fd-btn.danger:hover:not(:disabled) { border-color: var(--lj-vermilion); color: var(--lj-vermilion); }

/* 添加订阅面板 */
.fd-form { border-radius: 16px; padding: 16px 20px; margin-bottom: 18px; }
.fd-form-head { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.fd-form-title { font-size: 16px; letter-spacing: .08em; }
.fd-form-hint { font-size: 12px; color: var(--lj-text-3); }
.fd-form-close { margin-left: auto; border: none; background: transparent; color: var(--lj-text-2); font-size: 16px; cursor: pointer; }
.fd-form-row { display: flex; gap: 14px; flex-wrap: wrap; }
.fd-f-field { flex: 1; min-width: 200px; }
.fd-f-field.grow { flex: 2; }
.fd-f-label { display: block; font-size: 12px; color: var(--lj-text-2); margin-bottom: 6px; letter-spacing: .06em; }
.fd-input { width: 100%; padding: 9px 12px; border-radius: 10px; border: 1px solid var(--lj-line);
  background: rgba(0,0,0,.15); color: var(--lj-text); font-family: var(--font-serif); outline: none; box-sizing: border-box; }
.fd-input:focus { border-color: var(--lj-dai); }
.fd-form-actions { display: flex; align-items: center; justify-content: flex-end; gap: 12px; margin-top: 14px; }
.fd-save-tip { font-size: 12px; color: var(--lj-text-3); margin-right: auto; }
.fd-panel-enter-active,.fd-panel-leave-active { transition: all .28s ease; }
.fd-panel-enter-from,.fd-panel-leave-to { opacity: 0; transform: translateY(-10px); }

/* 三栏 */
.fd-grid { display: grid; grid-template-columns: 260px 1.4fr 1fr; gap: 16px; align-items: start; }
.fd-col { border-radius: 16px; padding: 16px; min-height: 200px; }
.fd-col-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.fd-col-title { margin: 0; font-size: 15px; letter-spacing: .08em; }
.fd-count { font-size: 12px; color: var(--lj-text-3); background: rgba(127,168,163,.1); padding: 2px 8px; border-radius: 999px; }
.fd-col-empty { padding: 40px 8px; text-align: center; color: var(--lj-text-3); font-size: 13px; line-height: 1.8; }
.fd-empty-sub { font-size: 11px; }
.fd-col-loading { padding: 40px 8px; text-align: center; color: var(--lj-text-3); font-size: 13px; }

/* 左栏 · 订阅源 */
.fd-source-list { display: flex; flex-direction: column; gap: 6px; }
.fd-source-item { display: flex; align-items: center; gap: 10px; padding: 10px 8px; border-radius: 12px;
  border: 1px solid transparent; background: transparent; color: var(--lj-text); cursor: pointer;
  text-align: left; font-family: var(--font-serif); transition: all .2s; }
.fd-source-item:hover { background: rgba(127,168,163,.06); }
.fd-source-item.active { background: rgba(127,168,163,.12); border-color: var(--lj-dai); }
.fd-si-dot { width: 8px; height: 8px; border-radius: 50%; flex: none; background: var(--lj-text-3); }
.fd-si-dot.ok { background: #6d9a6b; box-shadow: 0 0 6px rgba(109,154,107,.6); }
.fd-si-dot.err { background: var(--lj-vermilion); }
.fd-si-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.fd-si-title { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fd-si-cat { font-size: 10px; color: var(--lj-text-3); }
.fd-si-ops { display: flex; gap: 2px; flex: none; opacity: 0; transition: opacity .2s; }
.fd-source-item:hover .fd-si-ops { opacity: 1; }
.fd-op { width: 26px; height: 26px; border-radius: 7px; border: none; background: transparent; color: var(--lj-text-2); cursor: pointer; transition: all .2s; font-size: 13px; }
.fd-op:hover { color: var(--lj-dai); background: rgba(127,168,163,.1); }
.fd-op.danger:hover { color: var(--lj-vermilion); background: rgba(207,80,80,.1); }

/* 中栏 · 文章 */
.fd-list-filters { display: flex; align-items: center; gap: 8px; }
.fd-select { padding: 5px 8px; border-radius: 8px; border: 1px solid var(--lj-line); background: rgba(0,0,0,.15); color: var(--lj-text); font-family: var(--font-serif); font-size: 12px; outline: none; }
.fd-search { width: 130px; padding: 6px 10px; border-radius: 8px; border: 1px solid var(--lj-line); background: rgba(0,0,0,.15); color: var(--lj-text); font-family: var(--font-serif); font-size: 12px; outline: none; }
.fd-search:focus { border-color: var(--lj-dai); }

.fd-article-list { display: flex; flex-direction: column; gap: 4px; max-height: 640px; overflow-y: auto; }
.fd-article { display: flex; gap: 10px; padding: 12px 10px; border-radius: 12px; border: 1px solid transparent;
  background: transparent; color: var(--lj-text); cursor: pointer; text-align: left; font-family: var(--font-serif);
  transition: all .2s; align-items: flex-start; min-height: 46px; }
.fd-article:hover { background: rgba(127,168,163,.06); }
.fd-article.active { background: rgba(127,168,163,.12); border-color: var(--lj-dai); }
.fd-a-dot { width: 7px; height: 7px; border-radius: 50%; flex: none; background: var(--lj-ochre); margin-top: 7px; }
.fd-a-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.fd-a-title { font-size: 13px; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.fd-article.unread .fd-a-title { font-weight: 600; }
.fd-a-meta { display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--lj-text-3); }
.fd-a-source { color: var(--lj-dai); }
.fd-a-badge { background: rgba(199,169,107,.15); color: var(--lj-ochre); padding: 0 6px; border-radius: 999px; font-size: 10px; }
.fd-a-star { color: var(--lj-ochre); }
.fd-a-excerpt { font-size: 11px; color: var(--lj-text-3); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

.fd-pager { display: flex; align-items: center; justify-content: flex-end; gap: 12px; margin-top: 12px; }
.fd-pager-info { font-size: 12px; color: var(--lj-text-3); }

/* 右栏 · 阅读 */
.fd-reader { display: flex; flex-direction: column; gap: 14px; max-height: 760px; overflow-y: auto; }
.reader-placeholder { display: flex; flex-direction: column; align-items: center; gap: 10px; padding-top: 120px; }
.fd-rp-icon { font-size: 40px; opacity: .5; }
.fd-r-titles { min-width: 0; }
.fd-r-title { margin: 0; font-size: 17px; line-height: 1.5; letter-spacing: .02em; }
.fd-r-meta { margin-top: 6px; font-size: 11px; color: var(--lj-text-3); }

.fd-sum { border-radius: 12px; padding: 12px 14px; background: rgba(199,169,107,.10); border-color: rgba(199,169,107,.18); }
.fd-sum-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.fd-sum-label { font-size: 12px; letter-spacing: .1em; color: var(--lj-ochre); }
.fd-sum-loading { font-size: 11px; color: var(--lj-ochre); }
.fd-sum-actions { margin-left: auto; }
.fd-sum-text { margin: 0; font-size: 13px; line-height: 1.7; color: var(--lj-text); white-space: pre-wrap; word-break: break-word; }
.fd-sum-empty { font-size: 12px; color: var(--lj-text-3); }

.fd-reader-body { display: flex; flex-direction: column; gap: 12px; }
.fd-body-sum { margin: 0; font-size: 13px; line-height: 1.7; color: var(--lj-text-2); border-left: 2px solid var(--lj-dai); padding-left: 10px; }
.fd-body { margin: 0; font-size: 13px; line-height: 1.85; white-space: pre-wrap; word-break: break-word; }
.fd-body-actions { margin-top: 4px; }
.fd-body-orig { font-size: 13px; color: var(--lj-dai); text-decoration: none; }
.fd-body-orig:hover { text-decoration: underline; }

.fd-reader-ops { display: flex; gap: 8px; flex-wrap: wrap; border-top: 1px solid rgba(127,168,163,.1); padding-top: 12px; }

.fd-foot { margin-top: 30px; padding-bottom: 4px; text-align: center; font-size: 11px; color: var(--lj-text-3); letter-spacing: .15em; }

@media (max-width: 1080px) {
  .fd-grid { grid-template-columns: 220px 1fr; }
  .fd-reader { grid-column: 1 / -1; max-height: none; }
}
@media (max-width: 720px) {
  .fd-grid { grid-template-columns: 1fr; }
  .fd-source-list { max-height: 220px; overflow-y: auto; }
  .fd-page { padding: 88px 14px 50px; }
  .fd-title { font-size: 22px; }
  .fd-form-row { flex-direction: column; }
}
</style>