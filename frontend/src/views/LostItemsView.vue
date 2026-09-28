<template>
  <div class="li-page">
    <div class="li-inner">
      <header class="li-head">
        <BackButton class="li-back" />
        <div class="li-titles">
          <h1 class="li-title">遗失物件</h1>
          <p class="li-sub">丢过什么、在哪丢的、当时什么情形 —— 记下来，以后翻着回忆</p>
        </div>
        <div class="li-head-right">
          <button class="li-btn primary" @click="openCreate">＋ 记一笔</button>
        </div>
      </header>

      <!-- 一行小统计，不做成 KPI 面板 -->
      <div class="li-stats glass">
        <span>记过 <b>{{ stats.count }}</b> 件</span>
        <span v-if="stats.total_value">涉及 <b>¥{{ stats.total_value }}</b></span>
        <span v-if="latestDate">最近一次 <b>{{ latestDate }}</b></span>
        <span v-if="!stats.count" class="li-stats-hint">丢东西不丢人，忘了才可惜</span>
      </div>

      <div class="li-toolbar">
        <select v-model="filters.uploader_id" class="li-input li-select" @change="reload">
          <option value="">谁记的（全部）</option>
          <option v-for="u in uploaders" :key="u.user_id" :value="u.user_id">{{ u.avatar }} {{ u.name }}</option>
        </select>
        <select v-model="filters.category" class="li-input li-select" @change="reload">
          <option value="">全部分类</option>
          <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
        </select>
        <select v-model="filters.year" class="li-input li-select" @change="reload">
          <option value="">全部年份</option>
          <option v-for="y in years" :key="y" :value="y">{{ y }} 年</option>
        </select>
        <input v-model="filters.q" class="li-input" placeholder="搜物品 / 地点 / 经过" @keyup.enter="reload">
        <button class="li-btn" @click="resetFilters">重置</button>
      </div>

      <div v-if="loading" class="li-empty">加载中…</div>
      <div v-else-if="!list.length" class="li-empty">
        还没有记录。第一次想记的时候，点右上角「记一笔」—— 图片可以不传，写几个字也算。
      </div>

      <template v-else>
        <section v-for="grp in grouped" :key="grp.year" class="li-year">
          <div class="li-year-label">{{ grp.year }}<span class="li-year-count">{{ grp.items.length }} 件</span></div>
          <div class="li-list">
            <article v-for="it in grp.items" :key="it.id" class="li-card glass" @click="openDetail(it)">
              <div v-if="it.photos && it.photos.length" class="li-thumb">
                <img :src="it.photos[0]" :alt="it.name" loading="lazy">
                <span v-if="it.photos.length > 1" class="li-thumb-more">+{{ it.photos.length - 1 }}</span>
              </div>
              <div v-else class="li-thumb li-thumb-plain">{{ categoryEmoji(it.category) }}</div>
              <div class="li-card-main">
                <div class="li-name-row">
                  <span class="li-name">{{ it.name }}</span>
                  <span class="li-cat">{{ it.category }}</span>
                  <span v-if="it.value" class="li-value">¥{{ it.value }}</span>
                </div>
                <div class="li-meta">
                  <span v-if="it.lost_at">📅 {{ it.lost_at }}</span>
                  <span v-if="it.place">📍 {{ it.place }}</span>
                  <span class="li-owner">{{ it.uploader_name }} 记的</span>
                </div>
                <p v-if="it.scene" class="li-scene">{{ it.scene }}</p>
                <div v-if="it.mood || (it.tags && it.tags.length)" class="li-tags">
                  <span v-if="it.mood" class="li-mood">{{ it.mood }}</span>
                  <span v-for="t in it.tags" :key="t" class="li-tag">{{ t }}</span>
                </div>
              </div>
              <!-- 卡片上直接给操作入口（桌面悬停显现 / 触屏常显）：
                   只靠「点卡片看详情」太隐蔽，夜星找不到编辑与删除（V2438-001） -->
              <div class="li-acts">
                <button class="li-act" title="编辑这条" @click.stop="openEdit(it)">编辑</button>
                <button class="li-act danger" title="删除这条" @click.stop="remove(it)">删除</button>
              </div>
            </article>
          </div>
        </section>
      </template>
    </div>

    <!-- 详情 -->
    <el-dialog v-model="detailVisible" :title="detail?.name || '记录'" width="620px">
      <div v-if="detail" class="li-detail">
        <div v-if="detail.photos && detail.photos.length" class="li-detail-imgs">
          <img v-for="(p, i) in detail.photos" :key="i" :src="p" :alt="detail.name" @click="preview(p)">
        </div>
        <div class="li-detail-rows">
          <div><span class="k">分类</span>{{ detail.category }}</div>
          <div><span class="k">时间</span>{{ detail.lost_at || '未填' }}</div>
          <div><span class="k">地点</span>{{ detail.place || '未填' }}</div>
          <div v-if="detail.value"><span class="k">估值</span>¥{{ detail.value }}</div>
          <div><span class="k">记录人</span>{{ detail.uploader_name }}</div>
        </div>
        <p v-if="detail.scene" class="li-detail-scene">{{ detail.scene }}</p>
        <div v-if="detail.mood" class="li-detail-mood">{{ detail.mood }}</div>
        <div v-if="detail.tags && detail.tags.length" class="li-tags">
          <span v-for="t in detail.tags" :key="t" class="li-tag">{{ t }}</span>
        </div>
      </div>
      <template #footer>
        <button class="li-btn" @click="detailVisible = false">关闭</button>
        <button class="li-btn" @click="openEdit(detail)">编辑</button>
        <button class="li-btn danger" @click="remove(detail)">删除</button>
      </template>
    </el-dialog>

    <!-- 新增 / 编辑 -->
    <el-dialog v-model="formVisible" :title="form.id ? '编辑记录' : '记一笔遗失'" width="620px">
      <el-form label-width="76px" label-position="left">
        <el-form-item label="物品"><el-input v-model="form.name" placeholder="机票 / 手表 / 耳机" maxlength="120" /></el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="c in categories" :key="c" :value="c" :label="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="丢失日期"><el-date-picker v-model="form.lost_at" type="date" value-format="YYYY-MM-DD" placeholder="不填就是今天" style="width: 100%" /></el-form-item>
        <el-form-item label="地点"><el-input v-model="form.place" placeholder="成都天府机场 T2 / 大理古城" maxlength="160" /></el-form-item>
        <el-form-item label="经过">
          <el-input v-model="form.scene" type="textarea" :rows="4" placeholder="当时在做什么、怎么丢的、后来想起什么……" maxlength="2000" show-word-limit />
        </el-form-item>
        <el-form-item label="心情"><el-input v-model="form.mood" placeholder="一句话，可留空" maxlength="60" /></el-form-item>
        <el-form-item label="估值"><el-input-number v-model="form.value" :min="0" :max="9999999" :step="100" controls-position="right" /></el-form-item>
        <el-form-item label="标签">
          <el-input v-model="form.tagText" placeholder="逗号分隔：出差,机场" />
        </el-form-item>
        <el-form-item label="图片">
          <div class="li-uploader">
            <div v-for="(p, i) in form.photos" :key="i" class="li-upload-item">
              <img :src="p" alt="已上传图片">
              <button class="li-upload-del" @click.prevent="form.photos.splice(i, 1)">×</button>
            </div>
            <label class="li-upload-add" :class="{ busy: uploading }">
              <input type="file" accept="image/*" multiple hidden @change="onPick">
              {{ uploading ? '上传中…' : '＋' }}
            </label>
          </div>
          <div class="li-form-tip">图片可以不传 —— 事后想起来只写几个字同样有用。</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <button class="li-btn" @click="formVisible = false">取消</button>
        <button class="li-btn primary" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import BackButton from '@/components/BackButton.vue'
import { lostApi, uploadLifeImage } from '@/api/lifeExtra'

const list = ref([])
const uploaders = ref([])
const stats = reactive({ count: 0, total_value: 0, by_year: [], by_category: [], categories: [] })
const categories = ref(['证件', '电子', '穿戴', '随身', '其他'])
const filters = reactive({ uploader_id: '', category: '', year: '', q: '' })
const loading = ref(true)
const saving = ref(false)
const uploading = ref(false)

const detail = ref(null)
const detailVisible = ref(false)
const formVisible = ref(false)
const form = reactive({
  id: null, name: '', category: '其他', lost_at: '', place: '', scene: '',
  mood: '', value: 0, photos: [], tagText: '',
})

const years = computed(() => (stats.by_year || []).map((x) => x.year).filter((y) => y !== '未填日期'))
const latestDate = computed(() => (list.value[0]?.lost_at || ''))

/** 按年倒序分组（后端已按日期倒序返回，这里只做分组） */
const grouped = computed(() => {
  const out = []
  const map = new Map()
  for (const it of list.value) {
    const y = (it.lost_at || '').slice(0, 4) || '未填日期'
    if (!map.has(y)) { map.set(y, []); out.push({ year: y, items: map.get(y) }) }
    map.get(y).push(it)
  }
  return out
})

function categoryEmoji(c) {
  return { 证件: '🪪', 电子: '📱', 穿戴: '⌚', 随身: '🎒', 其他: '📦' }[c] || '📦'
}

async function reload() {
  loading.value = true
  try {
    const params = { size: 200 }
    if (filters.uploader_id) params.uploader_id = filters.uploader_id
    if (filters.category) params.category = filters.category
    if (filters.year) params.year = filters.year
    if (filters.q) params.q = filters.q
    const [res, st] = await Promise.all([lostApi.list(params), lostApi.stats()])
    list.value = res?.data?.list || []
    const d = st?.data || {}
    Object.assign(stats, d)
    if (d.categories?.length) categories.value = d.categories
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  Object.assign(filters, { uploader_id: '', category: '', year: '', q: '' })
  reload()
}

function openCreate() {
  Object.assign(form, {
    id: null, name: '', category: '其他', lost_at: '', place: '', scene: '',
    mood: '', value: 0, photos: [], tagText: '',
  })
  formVisible.value = true
}

/** 打开详情（点卡片）。此前模板引用了它但**函数从未定义** ——
 *  点卡片直接抛 TypeError，详情打不开、编辑与删除按钮永远露不出来（V2438-001）。 */
function openDetail(it) {
  if (!it) return
  detail.value = it
  detailVisible.value = true
}

function openEdit(it) {
  if (!it) return
  Object.assign(form, {
    id: it.id, name: it.name, category: it.category, lost_at: it.lost_at || '',
    place: it.place || '', scene: it.scene || '', mood: it.mood || '',
    value: it.value || 0, photos: [...(it.photos || [])], tagText: (it.tags || []).join(','),
  })
  detailVisible.value = false
  formVisible.value = true
}

async function onPick(e) {
  const files = Array.from(e.target.files || [])
  if (!files.length) return
  uploading.value = true
  try {
    for (const f of files) {
      if (f.size > 8 * 1024 * 1024) { ElMessage.warning(`${f.name} 超过 8MB，跳过`); continue }
      const res = await uploadLifeImage(f, 'lost')
      const url = res?.data?.url
      if (url) form.photos.push(url)
    }
  } catch (err) {
    ElMessage.warning(err?.response?.data?.detail || '图片上传失败')
  } finally {
    uploading.value = false
    e.target.value = ''
  }
}

async function save() {
  if (!form.name.trim()) { ElMessage.warning('至少写个物品名'); return }
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      category: form.category,
      lost_at: form.lost_at || '',
      place: form.place,
      scene: form.scene,
      mood: form.mood,
      value: Number(form.value) || null,
      photos: form.photos,
      tags: form.tagText ? form.tagText.split(/[,，]/).map((s) => s.trim()).filter(Boolean) : [],
    }
    if (form.id) await lostApi.update(form.id, payload)
    else await lostApi.create(payload)
    ElMessage.success(form.id ? '已更新' : '记下了')
    formVisible.value = false
    await reload()
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(it) {
  try {
    await ElMessageBox.confirm(`删除「${it.name}」这条记录？`, '确认删除', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '算了',
    })
  } catch { return }
  try {
    await lostApi.remove(it.id)
    detailVisible.value = false
    ElMessage.success('已删除')
    await reload()
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '删除失败')
  }
}

function preview(url) { window.open(url, '_blank', 'noopener') }

onMounted(async () => {
  await reload()
  try {
    const res = await lostApi.uploaders()
    uploaders.value = res?.data?.list || []
  } catch { /* 家人列表拿不到不影响主流程 */ }
})
</script>

<style scoped>
.li-page { min-height: 100vh; }
.li-inner { max-width: 1080px; margin: 0 auto; padding: 84px 20px 40px; }

.li-head { display: flex; align-items: center; gap: 14px; margin-bottom: 14px; flex-wrap: wrap; }
.li-titles { flex: 1; min-width: 180px; }
.li-title { margin: 0; font-size: 22px; letter-spacing: .1em; color: var(--lj-text); }
.li-sub { margin: 2px 0 0; font-size: 12px; color: var(--lj-text-2); letter-spacing: .06em; }
.li-head-right { display: flex; gap: 8px; margin-left: auto; }

.li-btn {
  border-radius: 9px; padding: 8px 16px; font-size: 13px; cursor: pointer;
  border: 1px solid var(--lj-line); background: transparent; color: var(--lj-text);
  font-family: inherit; transition: all .2s;
}
.li-btn:hover { border-color: var(--lj-line-strong); color: var(--lj-seal); }
.li-btn.primary { background: linear-gradient(135deg, rgba(199,169,107,.85), rgba(127,168,163,.85)); color: #0B0F14; border-color: transparent; }
.li-btn.danger { color: var(--pnl-up, #c2432f); }
.li-btn:disabled { opacity: .6; cursor: default; }

.li-stats { display: flex; gap: 18px; flex-wrap: wrap; padding: 12px 18px; border-radius: 14px; font-size: 13px; color: var(--lj-text-2); margin-bottom: 14px; }
.li-stats b { color: var(--lj-seal); font-size: 15px; }
.li-stats-hint { color: var(--lj-text-3); }

.li-toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.li-input { background: rgba(74,95,99,.08); border: 1px solid var(--lj-line); color: var(--lj-text);
  border-radius: 8px; padding: 8px 11px; font-size: 13px; font-family: inherit; min-width: 200px; flex: 1 1 200px; }
.li-input:focus { outline: none; border-color: var(--lj-seal); }
.li-select { flex: 0 0 150px; min-width: 140px; }

.li-empty { padding: 48px 20px; text-align: center; color: var(--lj-text-3); font-size: 13.5px; line-height: 1.9; }

.li-year { margin-bottom: 18px; }
.li-year-label { font-size: 12px; letter-spacing: .16em; color: var(--lj-text-3); margin: 0 0 8px 4px; display: flex; align-items: center; gap: 8px; }
.li-year-count { font-size: 11px; opacity: .8; }
.li-list { display: flex; flex-direction: column; gap: 10px; }

.li-card { position: relative; display: flex; gap: 14px; padding: 12px 14px; border-radius: 14px; cursor: pointer; transition: border-color .2s; }
.li-card:hover { border-color: var(--lj-line-strong); }

/* 卡片操作按钮：桌面悬停显现（不抢视觉），触屏与窄屏常显 */
.li-acts { flex: none; display: flex; align-items: center; gap: 6px; opacity: 0; transition: opacity .18s; }
.li-card:hover .li-acts, .li-card:focus-within .li-acts { opacity: 1; }
.li-act {
  border: 1px solid var(--lj-line); background: transparent; color: var(--lj-text-2);
  font-family: inherit; font-size: 12px; padding: 5px 10px; border-radius: 8px; cursor: pointer;
  transition: all .18s; white-space: nowrap;
}
.li-act:hover { border-color: var(--lj-line-strong); color: var(--lj-seal); }
.li-act.danger:hover { border-color: var(--pnl-up, #c2432f); color: var(--pnl-up, #c2432f); }
@media (hover: none) { .li-acts { opacity: 1; } }
.li-thumb { width: 78px; height: 78px; flex: none; border-radius: 10px; overflow: hidden; position: relative; background: rgba(74,95,99,.08); }
.li-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.li-thumb-plain { display: flex; align-items: center; justify-content: center; font-size: 28px; }
.li-thumb-more { position: absolute; right: 4px; bottom: 4px; font-size: 10px; padding: 1px 5px; border-radius: 999px; background: rgba(0,0,0,.55); color: #fff; }

.li-card-main { flex: 1; min-width: 0; }
.li-name-row { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.li-name { font-size: 15px; font-weight: 600; color: var(--lj-text); }
.li-cat { font-size: 11px; padding: 1px 7px; border-radius: 999px; background: rgba(127,168,163,.14); color: var(--lj-text-2); }
.li-value { font-size: 12px; color: var(--lj-text-3); }
.li-meta { display: flex; gap: 12px; flex-wrap: wrap; font-size: 11.5px; color: var(--lj-text-3); margin-top: 4px; }
.li-owner { margin-left: auto; }
.li-scene { margin: 7px 0 0; font-size: 12.5px; color: var(--lj-text-2); line-height: 1.75;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.li-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 7px; }
.li-tag { font-size: 11px; padding: 1px 8px; border-radius: 999px; background: rgba(199,169,107,.16); color: var(--lj-text-2); }
.li-mood { font-size: 11.5px; color: var(--lj-text-2); font-style: italic; }

.li-detail-imgs { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 8px; margin-bottom: 14px; }
.li-detail-imgs img { width: 100%; height: 120px; object-fit: cover; border-radius: 10px; cursor: zoom-in; }
.li-detail-rows { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; font-size: 13px; color: var(--lj-text); }
.li-detail-rows .k { color: var(--lj-text-3); margin-right: 8px; font-size: 12px; }
.li-detail-scene { margin: 14px 0 0; font-size: 13.5px; line-height: 1.9; color: var(--lj-text); white-space: pre-wrap; }
.li-detail-mood { margin-top: 10px; font-size: 13px; color: var(--lj-text-2); font-style: italic; }

.li-uploader { display: flex; gap: 8px; flex-wrap: wrap; }
.li-upload-item { width: 72px; height: 72px; border-radius: 10px; overflow: hidden; position: relative; }
.li-upload-item img { width: 100%; height: 100%; object-fit: cover; }
.li-upload-del { position: absolute; right: 2px; top: 2px; width: 18px; height: 18px; border-radius: 50%;
  border: none; background: rgba(0,0,0,.55); color: #fff; cursor: pointer; font-size: 12px; line-height: 1; }
.li-upload-add { width: 72px; height: 72px; border-radius: 10px; border: 1px dashed var(--lj-line-strong);
  display: flex; align-items: center; justify-content: center; cursor: pointer; color: var(--lj-text-3); font-size: 20px; }
.li-upload-add.busy { opacity: .6; cursor: default; font-size: 12px; }
.li-form-tip { font-size: 11px; color: var(--lj-text-3); margin-top: 4px; }

@media (max-width: 760px) {
  .li-inner { padding: 74px 14px 32px; }
  .li-head-right { width: 100%; }
  .li-head-right .li-btn { flex: 1; }
  .li-select { flex: 1 1 44%; min-width: 0; }
  .li-stats { gap: 12px; font-size: 12.5px; }
  .li-thumb { width: 62px; height: 62px; }
  .li-owner { margin-left: 0; }
  /* 窄屏按钮竖排，省横向空间 */
  .li-acts { opacity: 1; flex-direction: column; gap: 6px; }
  .li-act { padding: 4px 9px; font-size: 11.5px; }
}
</style>
