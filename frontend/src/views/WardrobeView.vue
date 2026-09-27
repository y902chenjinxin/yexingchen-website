<template>
  <div class="wd-page">
    <div class="wd-inner">
      <header class="wd-head">
        <BackButton class="wd-back" />
        <div class="wd-titles">
          <h1 class="wd-title">穿搭推荐</h1>
          <p class="wd-sub">衣服拍下来存好 · 按人分开推荐 · 再也不忘衣柜里有什么</p>
        </div>
        <div class="wd-head-right">
          <button class="wd-btn primary" @click="openItemCreate">＋ 加一件</button>
        </div>
      </header>

      <!-- 人：第一顺位。推荐、单品墙、搭配全部按人隔离 -->
      <div class="wd-persons">
        <button
          v-for="p in persons"
          :key="p.member_id"
          class="wd-person"
          :class="{ on: activeMemberId === p.member_id }"
          @click="switchPerson(p.member_id)"
        >
          <span class="wd-person-avatar">{{ p.avatar || '🌿' }}</span>
          <span class="wd-person-name">{{ p.name }}</span>
          <span class="wd-person-count">{{ p.item_count }}</span>
        </button>
        <button class="wd-person wd-person-manage" @click="tab = 'persons'">人档设置</button>
      </div>

      <div class="wd-tabs">
        <button v-for="t in tabs" :key="t.key" class="wd-tab" :class="{ on: tab === t.key }" @click="tab = t.key">{{ t.label }}</button>
      </div>

      <!-- ============ 今日推荐 ============ -->
      <section v-if="tab === 'today'" class="wd-pane">
        <div class="wd-today glass">
          <div class="wd-today-head">
            <div>
              <div class="wd-today-title">今天穿什么 · {{ activePerson?.name || '先选个人' }}</div>
              <div class="wd-today-weather">{{ suggest.weather_note || '—' }}</div>
            </div>
            <div class="wd-today-actions">
              <select v-model="occasion" class="wd-mini-select" @change="loadSuggest">
                <option value="">不限场合</option>
                <option v-for="o in ['通勤', '居家', '运动', '正式', '约会', '户外']" :key="o" :value="o">{{ o }}</option>
              </select>
              <button class="wd-btn tiny" :disabled="suggesting" @click="loadSuggest">换一套</button>
            </div>
          </div>

          <div v-if="suggest.empty_hint" class="wd-empty-inline">{{ suggest.empty_hint }}</div>
          <div v-else class="wd-options">
            <div v-for="(opt, i) in suggest.options" :key="i" class="wd-option">
              <div class="wd-option-imgs">
                <div v-for="it in opt.items" :key="it.id" class="wd-option-img" :title="`${it.name} · ${it.category}`">
                  <img v-if="it.photos && it.photos.length" :src="it.photos[0]" :alt="it.name">
                  <span v-else class="wd-option-ph">{{ categoryEmoji(it.category) }}</span>
                </div>
              </div>
              <div class="wd-option-names">
                {{ opt.items.map(x => x.name).join(' + ') }}
              </div>
              <div class="wd-option-actions">
                <button class="wd-btn tiny primary" @click="wearAll(opt)">就穿这套</button>
                <button class="wd-btn tiny" @click="saveOutfit(opt)">存搭配</button>
                <button class="wd-btn tiny" @click="collage(opt)">拼成图</button>
              </div>
            </div>
          </div>
          <div class="wd-today-reason">{{ suggest.reason }}</div>
        </div>
      </section>

      <!-- ============ 单品墙 ============ -->
      <section v-else-if="tab === 'items'" class="wd-pane">
        <div class="wd-toolbar">
          <input v-model="itemFilters.q" class="wd-input" placeholder="搜名称 / 品牌 / 备注" @keyup.enter="loadItems">
          <select v-model="itemFilters.category" class="wd-input wd-select" @change="loadItems">
            <option value="">全部品类</option>
            <option v-for="c in metas.categories" :key="c" :value="c">{{ c }}</option>
          </select>
          <select v-model="itemFilters.tag" class="wd-input wd-select" @change="loadItems">
            <option value="">全部标签</option>
            <option v-for="t in metas.style_tags" :key="t" :value="t">{{ t }}</option>
          </select>
          <select v-model="itemFilters.status" class="wd-input wd-select" @change="loadItems">
            <option value="">全部状态</option>
            <option v-for="s in metas.statuses" :key="s" :value="s">{{ s }}</option>
          </select>
          <label class="wd-check">
            <input v-model="staleOnly" type="checkbox" @change="toggleStale"> 90 天没穿过
          </label>
          <button class="wd-btn" @click="resetItemFilters">重置</button>
        </div>

        <div v-if="!items.length" class="wd-empty">这一位还没有入库的衣服 —— 点右上角「＋ 加一件」拍照存起来。</div>
        <div v-else class="wd-grid">
          <article v-for="it in items" :key="it.id" class="wd-card glass" @click="openItemDetail(it)">
            <div class="wd-card-img">
              <img v-if="it.photos && it.photos.length" :src="it.photos[0]" :alt="it.name" loading="lazy">
              <span v-else class="wd-card-ph">{{ categoryEmoji(it.category) }}</span>
              <span v-if="it.status !== '在穿'" class="wd-badge">{{ it.status }}</span>
            </div>
            <div class="wd-card-body">
              <div class="wd-card-name">{{ it.name }}</div>
              <div class="wd-card-meta">
                <span v-if="it.color_name" class="wd-color">
                  <i :style="{ background: it.color_hex || 'transparent' }"></i>{{ it.color_name }}
                </span>
                <span>{{ it.category }}</span>
                <span class="wd-wear">穿过 {{ it.wear_count }} 次</span>
              </div>
            </div>
          </article>
        </div>
      </section>

      <!-- ============ 搭配库 ============ -->
      <section v-else-if="tab === 'outfits'" class="wd-pane">
        <div v-if="!outfits.length" class="wd-empty">还没有存过搭配。在「今日推荐」里点「存搭配」就会收进这里。</div>
        <div v-else class="wd-outfits">
          <article v-for="o in outfits" :key="o.id" class="wd-outfit glass">
            <div class="wd-outfit-head">
              <b>{{ o.name }}</b>
              <span class="wd-outfit-owner">{{ o.owner_name }}</span>
              <span v-if="o.occasion" class="wd-cat">{{ o.occasion }}</span>
              <button class="wd-btn tiny" @click="openOutfit(o)">看搭配</button>
              <button class="wd-btn tiny danger" @click="removeOutfit(o)">删除</button>
            </div>
            <div class="wd-outfit-imgs">
              <div v-for="it in o.items" :key="it.id" class="wd-option-img">
                <img v-if="it.photos && it.photos.length" :src="it.photos[0]" :alt="it.name">
                <span v-else class="wd-option-ph">{{ categoryEmoji(it.category) }}</span>
              </div>
            </div>
          </article>
        </div>
      </section>

      <!-- ============ 人档 ============ -->
      <section v-else class="wd-pane">
        <div class="wd-persons-grid">
          <article v-for="p in persons" :key="p.member_id" class="wd-person-card glass">
            <div class="wd-person-card-head">
              <span class="wd-person-avatar lg">{{ p.avatar || '🌿' }}</span>
              <div>
                <div class="wd-person-card-name">{{ p.name }}</div>
                <div class="wd-person-card-sub">已入库 {{ p.item_count }} 件</div>
              </div>
            </div>
            <div class="wd-person-photo">
              <img v-if="p.full_body_photo" :src="p.full_body_photo" :alt="`${p.name} 的全身照`">
              <div v-else class="wd-person-photo-empty">还没有全身照</div>
            </div>
            <div class="wd-person-fields">
              <el-input v-model="p.size_note" size="small" placeholder="尺码：上衣 L / 鞋 42" @change="savePerson(p)" />
              <label class="wd-btn tiny">
                <input type="file" accept="image/*" hidden @change="(e) => uploadPersonPhoto(p, e)">
                上传全身照
              </label>
            </div>
            <p class="wd-person-tip">全身照用于「拼成图」与将来的 AI 试穿（正对镜头、光线好效果最好）。</p>
          </article>
        </div>
      </section>
    </div>

    <!-- 单品详情 -->
    <el-dialog v-model="detailVisible" :title="detail?.name || '单品'" width="620px">
      <div v-if="detail" class="wd-detail">
        <div class="wd-detail-imgs">
          <img v-for="(p, i) in (detail.photos || [])" :key="i" :src="p" :alt="detail.name" @click="preview(p)">
          <div v-if="!(detail.photos || []).length" class="wd-detail-noimg">{{ categoryEmoji(detail.category) }} 没传图片</div>
        </div>
        <div class="wd-detail-rows">
          <div><span class="k">归属人</span>{{ detail.owner_name || '未指定' }}</div>
          <div><span class="k">品类</span>{{ detail.category }}</div>
          <div v-if="detail.color_name"><span class="k">颜色</span>{{ detail.color_name }}</div>
          <div><span class="k">季节</span>{{ (detail.seasons || []).join(' / ') || '未填' }}</div>
          <div><span class="k">保暖度</span>{{ detail.warmth }}/5</div>
          <div><span class="k">正式度</span>{{ detail.formality }}/5</div>
          <div v-if="detail.size"><span class="k">尺码</span>{{ detail.size }}</div>
          <div v-if="detail.brand"><span class="k">品牌</span>{{ detail.brand }}</div>
          <div v-if="detail.price"><span class="k">价格</span>¥{{ detail.price }}</div>
          <div><span class="k">穿着</span>{{ detail.wear_count }} 次{{ detail.last_worn_at ? ` · 最近 ${detail.last_worn_at}` : '' }}</div>
          <div><span class="k">上传人</span>{{ detail.uploader_name }}</div>
        </div>
        <div v-if="(detail.style_tags || []).length" class="wd-tags">
          <span v-for="t in detail.style_tags" :key="t" class="wd-tag">{{ t }}</span>
        </div>
        <p v-if="detail.note" class="wd-detail-note">{{ detail.note }}</p>
      </div>
      <template #footer>
        <button class="wd-btn" @click="detailVisible = false">关闭</button>
        <button class="wd-btn primary" @click="wearOne(detail)">今天穿了</button>
        <button class="wd-btn" @click="openItemEdit(detail)">编辑</button>
        <button class="wd-btn danger" @click="removeItem(detail)">删除</button>
      </template>
    </el-dialog>

    <!-- 新增 / 编辑单品 -->
    <el-dialog v-model="formVisible" :title="form.id ? '编辑单品' : '加一件衣服'" width="640px">
      <el-form label-width="76px" label-position="left">
        <el-form-item label="归属人">
          <el-select v-model="form.owner_member_id" placeholder="这是谁的衣服" style="width: 100%">
            <el-option v-for="p in persons" :key="p.member_id" :value="p.member_id" :label="`${p.avatar} ${p.name}`" />
          </el-select>
        </el-form-item>
        <el-form-item label="名称"><el-input v-model="form.name" placeholder="藏青西装外套 / 白色帆布鞋" maxlength="120" /></el-form-item>
        <el-form-item label="品类">
          <el-select v-model="form.category" style="width: 100%">
            <el-option v-for="c in metas.categories" :key="c" :value="c" :label="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="主色">
          <div class="wd-color-row">
            <select v-model="form.color_name" class="wd-input">
              <option value="">未填</option>
              <option v-for="c in metas.color_presets" :key="c" :value="c">{{ c }}</option>
            </select>
            <input v-model="form.color_hex" type="color" class="wd-color-picker" title="取色（选填）">
          </div>
        </el-form-item>
        <el-form-item label="季节">
          <el-checkbox-group v-model="form.seasons">
            <el-checkbox v-for="s in ['春', '夏', '秋', '冬']" :key="s" :value="s" :label="s" />
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="保暖度">
          <el-slider v-model="form.warmth" :min="1" :max="5" :step="1" show-stops style="max-width: 260px" />
        </el-form-item>
        <el-form-item label="正式度">
          <el-slider v-model="form.formality" :min="1" :max="5" :step="1" show-stops style="max-width: 260px" />
        </el-form-item>
        <el-form-item label="标签">
          <el-checkbox-group v-model="form.style_tags">
            <el-checkbox v-for="t in metas.style_tags" :key="t" :value="t" :label="t" />
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio v-for="s in metas.statuses" :key="s" :value="s" :label="s" />
          </el-radio-group>
        </el-form-item>
        <el-form-item label="尺码/品牌">
          <div class="wd-two">
            <el-input v-model="form.size" placeholder="L / 42" maxlength="30" />
            <el-input v-model="form.brand" placeholder="品牌（可留空）" maxlength="60" />
          </div>
        </el-form-item>
        <el-form-item label="价格"><el-input-number v-model="form.price" :min="0" :max="999999" :step="10" controls-position="right" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.note" type="textarea" :rows="2" maxlength="300" /></el-form-item>
        <el-form-item label="图片">
          <div class="wd-uploader">
            <div v-for="(p, i) in form.photos" :key="i" class="wd-upload-item">
              <img :src="p" alt="已上传">
              <button class="wd-upload-del" @click.prevent="form.photos.splice(i, 1)">×</button>
            </div>
            <label class="wd-upload-add" :class="{ busy: uploading }">
              <input type="file" accept="image/*" multiple hidden @change="onPickItem">
              {{ uploading ? '上传中…' : '＋' }}
            </label>
          </div>
          <div class="wd-form-tip">建议拍平铺图（干净背景），推荐与拼图都用第一张当封面。</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <button class="wd-btn" @click="formVisible = false">取消</button>
        <button class="wd-btn primary" :disabled="saving" @click="saveItem">{{ saving ? '保存中…' : '保存' }}</button>
      </template>
    </el-dialog>

    <!-- 搭配详情 -->
    <el-dialog v-model="outfitVisible" :title="outfit?.name || '搭配'" width="560px">
      <div v-if="outfit" class="wd-option-imgs lg">
        <div v-for="it in outfit.items" :key="it.id" class="wd-option-img" :title="it.name">
          <img v-if="it.photos && it.photos.length" :src="it.photos[0]" :alt="it.name">
          <span v-else class="wd-option-ph">{{ categoryEmoji(it.category) }}</span>
        </div>
      </div>
      <p v-if="outfit" class="wd-detail-note">{{ outfit.items.map((x) => `${x.name}（${x.category}）`).join(' · ') }}</p>
      <template #footer>
        <button class="wd-btn" @click="outfitVisible = false">关闭</button>
        <button class="wd-btn primary" @click="wearOutfit(outfit)">今天穿了</button>
        <button class="wd-btn" @click="collage({ items: outfit.items })">拼成图</button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import BackButton from '@/components/BackButton.vue'
import { wardrobeApi, uploadLifeImage } from '@/api/lifeExtra'

const tabs = [
  { key: 'today', label: '今日推荐' },
  { key: 'items', label: '单品墙' },
  { key: 'outfits', label: '搭配库' },
  { key: 'persons', label: '人档' },
]
const tab = ref('today')

const persons = ref([])
const activeMemberId = ref(null)
const activePerson = computed(() => persons.value.find((p) => p.member_id === activeMemberId.value) || null)

const metas = reactive({ categories: ['上装', '下装', '外套', '连衣裙', '鞋', '配饰'], style_tags: [], statuses: ['在穿', '闲置', '已淘汰'], color_presets: [] })
const items = ref([])
const outfits = ref([])
const occasion = ref('')
const suggest = reactive({ options: [], reason: '', weather_note: '', empty_hint: '' })
const suggesting = ref(false)
const staleOnly = ref(false)
const itemFilters = reactive({ q: '', category: '', tag: '', status: '' })

const saving = ref(false)
const uploading = ref(false)
const detail = ref(null)
const detailVisible = ref(false)
const formVisible = ref(false)
const form = reactive({
  id: null, owner_member_id: null, name: '', category: '上装', color_name: '', color_hex: '',
  seasons: [], warmth: 3, formality: 3, style_tags: [], status: '在穿',
  size: '', brand: '', price: 0, note: '', photos: [],
})
const outfit = ref(null)
const outfitVisible = ref(false)

function categoryEmoji(c) {
  return { 上装: '👕', 下装: '👖', 外套: '🧥', 连衣裙: '👗', 鞋: '👟', 配饰: '🧣' }[c] || '👕'
}
function preview(u) { window.open(u, '_blank', 'noopener') }

/* ---------------- 人 ---------------- */
async function loadPersons() {
  const res = await wardrobeApi.persons()
  persons.value = res?.data?.list || []
  if (!activeMemberId.value && persons.value.length) activeMemberId.value = persons.value[0].member_id
}

function switchPerson(id) {
  activeMemberId.value = id
  tab.value = 'today'
  loadItems()
  loadSuggest()
  loadOutfits()
}

async function savePerson(p) {
  try {
    await wardrobeApi.savePerson(p.member_id, { size_note: p.size_note || '' })
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '保存失败')
  }
}

async function uploadPersonPhoto(p, e) {
  const f = e.target.files?.[0]
  if (!f) return
  try {
    const res = await uploadLifeImage(f, 'wardrobe')
    const url = res?.data?.url
    if (url) {
      await wardrobeApi.savePerson(p.member_id, { full_body_photo: url })
      p.full_body_photo = url
      ElMessage.success('全身照已保存')
    }
  } catch (err) {
    ElMessage.warning(err?.response?.data?.detail || '上传失败')
  } finally { e.target.value = '' }
}

/* ---------------- 单品 ---------------- */
async function loadItems() {
  const params = { size: 300 }
  if (activeMemberId.value) params.owner_member_id = activeMemberId.value
  if (itemFilters.q) params.q = itemFilters.q
  if (itemFilters.category) params.category = itemFilters.category
  if (itemFilters.tag) params.tag = itemFilters.tag
  if (itemFilters.status) params.status = itemFilters.status
  if (staleOnly.value) params.stale_days = 90
  try {
    const res = await wardrobeApi.items(params)
    items.value = res?.data?.list || []
    const d = res?.data || {}
    if (d.categories) metas.categories = d.categories
    if (d.style_tags) metas.style_tags = d.style_tags
    if (d.statuses) metas.statuses = d.statuses
    if (d.color_presets) metas.color_presets = d.color_presets
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '加载失败')
  }
}

function toggleStale() { loadItems() }
function resetItemFilters() {
  Object.assign(itemFilters, { q: '', category: '', tag: '', status: '' })
  staleOnly.value = false
  loadItems()
}

function openItemCreate() {
  Object.assign(form, {
    id: null, owner_member_id: activeMemberId.value, name: '', category: '上装', color_name: '', color_hex: '',
    seasons: [], warmth: 3, formality: 3, style_tags: [], status: '在穿',
    size: '', brand: '', price: 0, note: '', photos: [],
  })
  formVisible.value = true
}
function openItemEdit(it) {
  if (!it) return
  Object.assign(form, {
    id: it.id, owner_member_id: it.owner_member_id, name: it.name, category: it.category,
    color_name: it.color_name, color_hex: it.color_hex, seasons: [...(it.seasons || [])],
    warmth: it.warmth, formality: it.formality, style_tags: [...(it.style_tags || [])],
    status: it.status, size: it.size, brand: it.brand, price: it.price || 0,
    note: it.note, photos: [...(it.photos || [])],
  })
  detailVisible.value = false
  formVisible.value = true
}

async function onPickItem(e) {
  const files = Array.from(e.target.files || [])
  if (!files.length) return
  uploading.value = true
  try {
    for (const f of files) {
      if (f.size > 8 * 1024 * 1024) { ElMessage.warning(`${f.name} 超过 8MB，跳过`); continue }
      const res = await uploadLifeImage(f, 'wardrobe')
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

async function saveItem() {
  if (!form.name.trim()) { ElMessage.warning('给这件衣服起个名字吧'); return }
  if (!form.owner_member_id) { ElMessage.warning('先选归属人 —— 推荐要按人分开算'); return }
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(), owner_member_id: form.owner_member_id, category: form.category,
      color_name: form.color_name, color_hex: form.color_hex, seasons: form.seasons,
      warmth: form.warmth, formality: form.formality, style_tags: form.style_tags,
      status: form.status, size: form.size, brand: form.brand, price: Number(form.price) || null,
      note: form.note, photos: form.photos,
    }
    if (form.id) await wardrobeApi.updateItem(form.id, payload)
    else await wardrobeApi.createItem(payload)
    ElMessage.success(form.id ? '已更新' : '已入库')
    formVisible.value = false
    await loadItems()
    await loadPersons()
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function openItemDetail(it) { detail.value = it; detailVisible.value = true }

async function wearOne(it) {
  if (!it) return
  try {
    await wardrobeApi.wear(it.id)
    ElMessage.success(`记下了：今天穿了「${it.name}」`)
    detailVisible.value = false
    await loadItems()
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '记录失败')
  }
}

async function wearAll(opt) {
  if (!opt?.items?.length) return
  try {
    for (const it of opt.items) await wardrobeApi.wear(it.id)
    ElMessage.success('这一套记下了')
    await loadItems()
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '记录失败')
  }
}

async function removeItem(it) {
  try {
    await ElMessageBox.confirm(`移除「${it.name}」？（可以在「显示已下架」里…… 这件会从单品墙消失）`, '确认移除', {
      type: 'warning', confirmButtonText: '移除', cancelButtonText: '算了',
    })
  } catch { return }
  try {
    await wardrobeApi.removeItem(it.id)
    detailVisible.value = false
    ElMessage.success('已移除')
    await loadItems()
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '移除失败')
  }
}

/* ---------------- 推荐 ---------------- */
async function loadSuggest() {
  if (!activeMemberId.value) { suggest.empty_hint = '先在上面选一个人'; return }
  suggesting.value = true
  try {
    const res = await wardrobeApi.suggest({ owner_member_id: activeMemberId.value, occasion: occasion.value })
    const d = res?.data || {}
    suggest.options = d.options || []
    suggest.reason = d.reason || ''
    suggest.weather_note = d.weather_note || ''
    suggest.empty_hint = d.empty_hint || ''
  } catch (e) {
    suggest.empty_hint = e?.response?.data?.detail || '推荐失败，稍后再试'
  } finally {
    suggesting.value = false
  }
}

async function saveOutfit(opt) {
  if (!opt?.item_ids?.length) return
  try {
    const { value } = await ElMessageBox.prompt('给这套搭配起个名字', '存搭配', {
      inputValue: `${activePerson.value?.name || ''} ${occasion.value || '日常'}搭配`,
      confirmButtonText: '保存', cancelButtonText: '算了',
    })
    await wardrobeApi.createOutfit({
      name: value, owner_member_id: activeMemberId.value,
      item_ids: opt.item_ids, occasion: occasion.value,
    })
    ElMessage.success('已存入搭配库')
    await loadOutfits()
  } catch (e) {
    if (e !== 'cancel') ElMessage.warning(e?.response?.data?.detail || '保存失败')
  }
}

/* ---------------- 搭配库 ---------------- */
async function loadOutfits() {
  try {
    const res = await wardrobeApi.outfits(activeMemberId.value ? { owner_member_id: activeMemberId.value } : {})
    outfits.value = res?.data?.list || []
  } catch { outfits.value = [] }
}
function openOutfit(o) { outfit.value = o; outfitVisible.value = true }
async function wearOutfit(o) {
  if (!o?.items?.length) return
  try {
    for (const it of o.items) await wardrobeApi.wear(it.id)
    ElMessage.success('这一套记下了')
    outfitVisible.value = false
    await loadItems()
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '记录失败')
  }
}
async function removeOutfit(o) {
  try {
    await ElMessageBox.confirm(`删除搭配「${o.name}」？`, '确认删除', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '算了',
    })
  } catch { return }
  try {
    await wardrobeApi.removeOutfit(o.id)
    ElMessage.success('已删除')
    await loadOutfits()
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '删除失败')
  }
}

/* ---------------- 拼成图（T0：人像 + 单品排成一张卡片，零成本）---------------- */
function collage(opt) {
  const list = (opt?.items || []).slice(0, 6)
  if (!list.length) { ElMessage.warning('这套还没有单品'); return }
  const W = 1080, H = 1350
  const cv = document.createElement('canvas')
  cv.width = W; cv.height = H
  const ctx = cv.getContext('2d')
  ctx.fillStyle = '#FAF7F0'
  ctx.fillRect(0, 0, W, H)

  ctx.textAlign = 'left'
  ctx.fillStyle = '#18202A'
  ctx.font = '700 44px "PingFang SC", "Microsoft YaHei", sans-serif'
  ctx.fillText(`${activePerson.value?.name || ''} 今天穿这套`, 60, 96)
  ctx.fillStyle = '#C7A96B'
  ctx.font = '400 24px "PingFang SC", "Microsoft YaHei", sans-serif'
  ctx.fillText(new Date().toLocaleDateString('zh-CN'), 60, 138)

  const cols = 2, gap = 20
  const cellW = (W - 120 - gap) / cols
  const cellH = 330
  let done = 0
  list.forEach((it, i) => {
    const x = 60 + (i % cols) * (cellW + gap)
    const y = 190 + Math.floor(i / cols) * (cellH + gap)
    ctx.fillStyle = 'rgba(0,0,0,.05)'
    ctx.fillRect(x, y, cellW, cellH)
    const url = (it.photos || [])[0]
    const finish = () => {
      done++
      if (done === list.length) {
        ctx.fillStyle = '#8A8F98'
        ctx.font = '400 22px "PingFang SC", "Microsoft YaHei", sans-serif'
        ctx.fillText((suggest.weather_note || '').slice(0, 48), 60, H - 60)
        cv.toBlob((blob) => {
          if (!blob) { ElMessage.warning('导出失败'); return }
          const a = document.createElement('a')
          a.href = URL.createObjectURL(blob)
          a.download = `穿搭-${new Date().toISOString().slice(0, 10)}.png`
          a.click()
          setTimeout(() => URL.revokeObjectURL(a.href), 5000)
        }, 'image/png')
      }
    }
    ctx.fillStyle = '#18202A'
    ctx.font = '600 22px "PingFang SC", "Microsoft YaHei", sans-serif'
    ctx.fillText(`${it.name} · ${it.category}`, x + 12, y + cellH - 16)
    if (!url) { finish(); return }
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      const scale = Math.min(cellW / img.width, (cellH - 56) / img.height)
      const w = img.width * scale, h = img.height * scale
      ctx.drawImage(img, x + (cellW - w) / 2, y + (cellH - 56 - h) / 2, w, h)
      finish()
    }
    img.onerror = finish
    img.src = url
  })
}

onMounted(async () => {
  try {
    await loadPersons()
    await Promise.all([loadItems(), loadSuggest(), loadOutfits()])
  } catch (e) {
    ElMessage.warning(e?.response?.data?.detail || '加载失败')
  }
})
</script>

<style scoped>
.wd-page { min-height: 100vh; }
.wd-inner { max-width: 1080px; margin: 0 auto; padding: 84px 20px 40px; }

.wd-head { display: flex; align-items: center; gap: 14px; margin-bottom: 14px; flex-wrap: wrap; }
.wd-titles { flex: 1; min-width: 180px; }
.wd-title { margin: 0; font-size: 22px; letter-spacing: .1em; color: var(--lj-text); }
.wd-sub { margin: 2px 0 0; font-size: 12px; color: var(--lj-text-2); letter-spacing: .06em; }
.wd-head-right { display: flex; gap: 8px; margin-left: auto; }

.wd-btn {
  border-radius: 9px; padding: 8px 16px; font-size: 13px; cursor: pointer;
  border: 1px solid var(--lj-line); background: transparent; color: var(--lj-text);
  font-family: inherit; transition: all .2s;
}
.wd-btn:hover { border-color: var(--lj-line-strong); color: var(--lj-seal); }
.wd-btn.primary { background: linear-gradient(135deg, rgba(199,169,107,.85), rgba(127,168,163,.85)); color: #0B0F14; border-color: transparent; }
.wd-btn.tiny { padding: 4px 10px; font-size: 12px; }
.wd-btn.danger { color: var(--pnl-up, #c2432f); }
.wd-btn:disabled { opacity: .6; cursor: default; }

.wd-persons { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.wd-person { display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px; border-radius: 999px;
  border: 1px solid var(--lj-line); background: transparent; color: var(--lj-text-2); cursor: pointer; font-family: inherit; font-size: 13px; }
.wd-person.on { border-color: var(--lj-seal); color: var(--lj-seal); background: rgba(199,169,107,.12); font-weight: 600; }
.wd-person-avatar { font-size: 15px; }
.wd-person-avatar.lg { font-size: 26px; }
.wd-person-count { font-size: 11px; opacity: .75; }
.wd-person-manage { border-style: dashed; }

.wd-tabs { display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
.wd-tab { padding: 7px 18px; border-radius: 999px; border: 1px solid var(--lj-line); background: transparent;
  color: var(--lj-text-2); cursor: pointer; font-family: inherit; font-size: 13px; }
.wd-tab.on { background: var(--lj-seal); border-color: var(--lj-seal); color: #0B0F14; font-weight: 600; }

.wd-today { padding: 18px; border-radius: 16px; }
.wd-today-head { display: flex; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.wd-today-title { font-size: 16px; font-weight: 700; color: var(--lj-text); }
.wd-today-weather { font-size: 12.5px; color: var(--lj-text-2); margin-top: 4px; }
.wd-today-actions { margin-left: auto; display: flex; gap: 8px; align-items: center; }
.wd-mini-select { border: 1px solid var(--lj-line); border-radius: 8px; padding: 5px 8px; font-size: 12.5px;
  background: transparent; color: var(--lj-text); font-family: inherit; }
.wd-options { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-top: 14px; }
.wd-option { border: 1px solid var(--lj-line); border-radius: 12px; padding: 12px; }
.wd-option-imgs { display: flex; gap: 8px; flex-wrap: wrap; }
.wd-option-imgs.lg { margin-bottom: 12px; }
.wd-option-img { width: 72px; height: 72px; border-radius: 10px; overflow: hidden; background: rgba(74,95,99,.08);
  display: flex; align-items: center; justify-content: center; }
.wd-option-img img { width: 100%; height: 100%; object-fit: cover; }
.wd-option-ph { font-size: 24px; }
.wd-option-names { margin-top: 9px; font-size: 12.5px; color: var(--lj-text); line-height: 1.7; }
.wd-option-actions { display: flex; gap: 6px; margin-top: 9px; flex-wrap: wrap; }
.wd-today-reason { margin-top: 14px; font-size: 12.5px; color: var(--lj-text-3); }
.wd-empty-inline { margin-top: 14px; font-size: 13px; color: var(--lj-text-3); }

.wd-toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 14px; flex-wrap: wrap; }
.wd-input { background: rgba(74,95,99,.08); border: 1px solid var(--lj-line); color: var(--lj-text);
  border-radius: 8px; padding: 8px 11px; font-size: 13px; font-family: inherit; min-width: 180px; flex: 1 1 180px; }
.wd-input:focus { outline: none; border-color: var(--lj-seal); }
.wd-select { flex: 0 0 132px; min-width: 120px; }
.wd-check { font-size: 12.5px; color: var(--lj-text-2); display: inline-flex; align-items: center; gap: 5px; white-space: nowrap; }
.wd-empty { padding: 44px 20px; text-align: center; color: var(--lj-text-3); font-size: 13.5px; line-height: 1.9; }

.wd-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.wd-card { border-radius: 14px; overflow: hidden; cursor: pointer; transition: border-color .2s; }
.wd-card:hover { border-color: var(--lj-line-strong); }
.wd-card-img { position: relative; aspect-ratio: 1 / 1; background: rgba(74,95,99,.08);
  display: flex; align-items: center; justify-content: center; }
.wd-card-img img { width: 100%; height: 100%; object-fit: cover; }
.wd-card-ph { font-size: 34px; }
.wd-badge { position: absolute; left: 8px; top: 8px; font-size: 10.5px; padding: 1px 7px; border-radius: 999px;
  background: rgba(0,0,0,.55); color: #fff; }
.wd-card-body { padding: 9px 11px 12px; }
.wd-card-name { font-size: 13.5px; font-weight: 600; color: var(--lj-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.wd-card-meta { display: flex; gap: 9px; flex-wrap: wrap; font-size: 11px; color: var(--lj-text-3); margin-top: 5px; }
.wd-color { display: inline-flex; align-items: center; gap: 4px; }
.wd-color i { width: 9px; height: 9px; border-radius: 50%; border: 1px solid var(--lj-line); }
.wd-wear { margin-left: auto; }

.wd-outfits { display: flex; flex-direction: column; gap: 10px; }
.wd-outfit { border-radius: 14px; padding: 12px 14px; }
.wd-outfit-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 14px; color: var(--lj-text); }
.wd-outfit-owner { font-size: 11px; color: var(--lj-text-3); }
.wd-cat { font-size: 11px; padding: 1px 7px; border-radius: 999px; background: rgba(127,168,163,.14); color: var(--lj-text-2); }
.wd-outfit-imgs { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }

.wd-persons-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.wd-person-card { border-radius: 14px; padding: 16px; }
.wd-person-card-head { display: flex; align-items: center; gap: 10px; }
.wd-person-card-name { font-size: 15px; font-weight: 600; color: var(--lj-text); }
.wd-person-card-sub { font-size: 11.5px; color: var(--lj-text-3); }
.wd-person-photo { margin: 12px 0; height: 180px; border-radius: 12px; overflow: hidden;
  background: rgba(74,95,99,.08); display: flex; align-items: center; justify-content: center; }
.wd-person-photo img { width: 100%; height: 100%; object-fit: cover; }
.wd-person-photo-empty { font-size: 12px; color: var(--lj-text-3); }
.wd-person-fields { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.wd-person-tip { margin: 9px 0 0; font-size: 11px; color: var(--lj-text-3); line-height: 1.7; }

.wd-detail-imgs { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 8px; margin-bottom: 14px; }
.wd-detail-imgs img { width: 100%; height: 120px; object-fit: cover; border-radius: 10px; cursor: zoom-in; }
.wd-detail-noimg { grid-column: 1 / -1; height: 90px; display: flex; align-items: center; justify-content: center;
  border-radius: 10px; background: rgba(74,95,99,.08); color: var(--lj-text-3); font-size: 13px; }
.wd-detail-rows { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; font-size: 13px; color: var(--lj-text); }
.wd-detail-rows .k { color: var(--lj-text-3); margin-right: 8px; font-size: 12px; }
.wd-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 12px; }
.wd-tag { font-size: 11px; padding: 1px 8px; border-radius: 999px; background: rgba(199,169,107,.16); color: var(--lj-text-2); }
.wd-detail-note { margin: 12px 0 0; font-size: 13px; color: var(--lj-text-2); line-height: 1.8; }

.wd-color-row { display: flex; gap: 10px; align-items: center; width: 100%; }
.wd-color-row .wd-input { flex: 1; }
.wd-color-picker { width: 42px; height: 32px; border: 1px solid var(--lj-line); border-radius: 8px; background: transparent; cursor: pointer; }
.wd-two { display: flex; gap: 10px; width: 100%; }
.wd-uploader { display: flex; gap: 8px; flex-wrap: wrap; }
.wd-upload-item { width: 72px; height: 72px; border-radius: 10px; overflow: hidden; position: relative; }
.wd-upload-item img { width: 100%; height: 100%; object-fit: cover; }
.wd-upload-del { position: absolute; right: 2px; top: 2px; width: 18px; height: 18px; border-radius: 50%;
  border: none; background: rgba(0,0,0,.55); color: #fff; cursor: pointer; font-size: 12px; line-height: 1; }
.wd-upload-add { width: 72px; height: 72px; border-radius: 10px; border: 1px dashed var(--lj-line-strong);
  display: flex; align-items: center; justify-content: center; cursor: pointer; color: var(--lj-text-3); font-size: 20px; }
.wd-upload-add.busy { opacity: .6; cursor: default; font-size: 12px; }
.wd-form-tip { font-size: 11px; color: var(--lj-text-3); margin-top: 4px; }

@media (max-width: 760px) {
  .wd-inner { padding: 74px 14px 32px; }
  .wd-head-right { width: 100%; }
  .wd-head-right .wd-btn { flex: 1; }
  .wd-today-actions { margin-left: 0; width: 100%; }
  .wd-select { flex: 1 1 44%; min-width: 0; }
  .wd-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
  .wd-option-img { width: 60px; height: 60px; }
}
</style>
