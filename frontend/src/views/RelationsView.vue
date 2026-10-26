<template>
  <div class="rl-page">
    <div class="rl-inner">
      <header class="rl-head">
        <BackButton class="rl-back" />
        <div class="rl-titles">
          <h1 class="rl-title">关系</h1>
          <p class="rl-sub">谁能记住，谁就还在你的生活里</p>
        </div>
        <IconButton icon="plus" label="加人" variant="primary" @click="openCreate" />
      </header>

      <!-- 三个触发点（v2.46.250）：生日 / 该联系 / 想起一个人。
           内向的人不需要「关系健康分」，只需要一个具体的人名 + 一个理由。 -->
      <section v-if="hasCue" class="rl-cues">
        <div v-if="dash.birthdays.length" class="rl-cue rl-cue--bday">
          <div class="rl-cue-h"><span>🎂</span>近期生日</div>
          <button
            v-for="c in dash.birthdays"
            :key="'b' + c.id"
            class="rl-cue-row"
            @click="openById(c.id)"
          >
            <b>{{ c.name }}</b>
            <em>{{ c.birthday.label }}<template v-if="c.birthday.is_lunar"> · 农历</template></em>
          </button>
        </div>

        <div v-if="dash.overdue.length" class="rl-cue rl-cue--late">
          <div class="rl-cue-h"><span>🕊</span>有点久了</div>
          <button
            v-for="c in dash.overdue"
            :key="'o' + c.id"
            class="rl-cue-row"
            @click="openById(c.id)"
          >
            <b>{{ c.name }}</b>
            <em>{{ c.days_since }} 天</em>
          </button>
          <p v-if="dash.overdue_total > dash.overdue.length" class="rl-cue-more">
            还有 {{ dash.overdue_total - dash.overdue.length }} 位
          </p>
        </div>

        <div v-if="dash.blind" class="rl-cue rl-cue--blind">
          <div class="rl-cue-h"><span>🎲</span>想起一个人</div>
          <button class="rl-cue-row" @click="openById(dash.blind.id)">
            <b>{{ dash.blind.name }}</b>
            <em>{{ dash.blind.topics || '还没记共同话题' }}</em>
          </button>
        </div>
      </section>

      <div class="rl-toolbar">
        <input v-model="keyword" class="rl-input" placeholder="搜名字 / 关系 / 话题" spellcheck="false" />
        <div class="rl-seg">
          <button
            v-for="s in STAR_FILTERS"
            :key="s.v"
            class="rl-seg-btn"
            :class="{ on: star === s.v }"
            @click="star = s.v"
          >{{ s.label }}</button>
        </div>
        <span class="rl-count">共 {{ items.length }} 人</span>
      </div>

      <p v-if="!loading && !items.length" class="rl-empty">
        还没有人。点右上角「加人」，先记一个最近想起来的人 —— 只要有名字就能开始。
      </p>

      <ul class="rl-list">
        <li v-for="c in items" :key="c.id" class="rl-item" @click="open(c)">
          <span class="rl-ava">{{ c.name.slice(0, 1) }}</span>
          <div class="rl-main">
            <div class="rl-line1">
              <b>{{ c.name }}</b>
              <span v-if="c.relation" class="rl-rel">{{ c.relation }}</span>
              <span v-if="c.birthday && c.birthday.days <= 7" class="rl-bd">🎂 {{ c.birthday.label }}</span>
            </div>
            <p class="rl-line2" :class="{ late: c.overdue }">{{ statusText(c) }}</p>
          </div>
          <span class="rl-stars" :title="`亲密度 ${c.intimacy || 3}/5`">{{ stars(c.intimacy) }}</span>
        </li>
      </ul>
    </div>

    <!-- 详情 -->
    <el-drawer v-model="drawer" :size="drawerSize" :with-header="false" class="rl-drawer">
      <div v-if="cur" class="rl-detail">
        <header class="rl-dhead">
          <span class="rl-dava">{{ cur.name.slice(0, 1) }}</span>
          <div class="rl-dinfo">
            <h2>{{ cur.name }}</h2>
            <p>
              <span v-if="cur.relation">{{ cur.relation }}</span>
              <span class="rl-dot">·</span>
              <span>{{ stars(cur.intimacy) }} 亲密度 {{ cur.intimacy || 3 }}/5</span>
            </p>
            <p class="rl-dstate" :class="{ late: cur.overdue }">{{ statusText(cur) }}</p>
          </div>
          <button class="rl-close" @click="drawer = false">×</button>
        </header>

        <div v-if="cur.topics || cur.notes || cur.birthday" class="rl-facts">
          <p v-if="cur.birthday">
            <i>生日</i>{{ cur.birthday.mmdd }}<template v-if="cur.birthday.is_lunar">（农历）</template>
            · {{ cur.birthday.label }}
          </p>
          <p v-if="cur.topics"><i>话题</i>{{ cur.topics }}</p>
          <p v-if="cur.notes"><i>备注</i>{{ cur.notes }}</p>
        </div>

        <div class="rl-actions">
          <button class="rl-act rl-act--main" @click="openLogForm">记一次</button>
          <button class="rl-act" :disabled="icing" @click="doIcebreak">
            {{ icing ? '生成中…' : '生成开场白' }}
          </button>
          <button class="rl-act" @click="openEdit">编辑</button>
        </div>

        <div v-if="iceLines.length" class="rl-ice">
          <div class="rl-ice-h">挑一句发过去</div>
          <div v-for="(l, i) in iceLines" :key="i" class="rl-ice-row">
            <p>{{ l }}</p>
            <button @click="copyLine(l)">{{ copiedIdx === i ? '已复制' : '复制' }}</button>
          </div>
        </div>

        <!-- 记一次（内联小表单，不做弹窗：这是最容易被打断的操作，越轻越好） -->
        <div v-if="logForm" class="rl-logform">
          <div class="rl-lf-row">
            <button
              v-for="ch in CHANNELS"
              :key="ch"
              class="rl-chip"
              :class="{ on: logDraft.channel === ch }"
              @click="logDraft.channel = ch"
            >{{ ch }}</button>
          </div>
          <div class="rl-lf-row">
            <button
              v-for="t in TAGS"
              :key="t"
              class="rl-chip"
              :class="{ on: logTags.includes(t) }"
              @click="toggleTag(t)"
            >{{ t }}</button>
          </div>
          <el-input
            v-model="logDraft.note"
            type="textarea"
            :rows="2"
            maxlength="500"
            placeholder="一句话就够了：他最近在忙什么 / 说了什么"
          />
          <el-input
            v-model="logDraft.follow_up"
            maxlength="200"
            placeholder="下次可以接着问（比如：他女儿今年高考）"
            class="rl-lf-follow"
          />
          <div class="rl-lf-actions">
            <button class="rl-act" @click="logForm = false">取消</button>
            <button class="rl-act rl-act--main" :disabled="saving" @click="submitLog">
              {{ saving ? '保存中…' : '记下' }}
            </button>
          </div>
        </div>

        <div class="rl-timeline">
          <div class="rl-tl-h">聊过的事</div>
          <p v-if="!cur.logs || !cur.logs.length" class="rl-tl-empty">
            还没有记录。记第一条之后，「多久没联系」才算得准。
          </p>
          <div v-for="l in cur.logs" :key="l.id" class="rl-tl-item">
            <div class="rl-tl-dot"></div>
            <div class="rl-tl-body">
              <div class="rl-tl-top">
                <b>{{ l.happened_on }}</b>
                <span v-if="l.channel" class="rl-tl-ch">{{ l.channel }}</span>
                <button class="rl-tl-del" title="删除这条" @click="removeLog(l.id)">×</button>
              </div>
              <p v-if="l.note" class="rl-tl-note">{{ l.note }}</p>
              <div v-if="l.tags" class="rl-tl-tags">
                <span v-for="t in l.tags.split(',')" :key="t">{{ t }}</span>
              </div>
              <p v-if="l.follow_up" class="rl-tl-follow">下次问：{{ l.follow_up }}</p>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 新建 / 编辑 -->
    <el-dialog v-model="dialog" :title="form.id ? '编辑' : '加一个人'" width="420px" append-to-body>
      <div class="rl-form">
        <label class="rl-field">
          <span>名字</span>
          <el-input v-model="form.name" maxlength="60" placeholder="只要名字就能开始" />
        </label>
        <label class="rl-field">
          <span>关系</span>
          <el-input v-model="form.relation" maxlength="40" placeholder="发小 / 同事 / 客户 / 表姐…" />
        </label>
        <div class="rl-field">
          <span>亲密度（决定多久提醒你一次）</span>
          <div class="rl-seg">
            <button
              v-for="n in 5"
              :key="n"
              class="rl-seg-btn"
              :class="{ on: form.intimacy === n }"
              @click="form.intimacy = n"
            >{{ n }}</button>
          </div>
          <p class="rl-tip">{{ intimacyTip }}</p>
        </div>
        <label class="rl-field">
          <span>共同话题（逗号分隔）</span>
          <el-input v-model="form.topics" maxlength="255" placeholder="露营 / 摄影 / 他女儿 / 跳槽" />
        </label>
        <div class="rl-field">
          <span>生日</span>
          <div class="rl-bd-row">
            <el-input v-model="form.birthday" maxlength="5" placeholder="MM-DD，可不填" style="width: 130px" />
            <button
              class="rl-chip"
              :class="{ on: form.birthday_type === 'solar' }"
              @click="form.birthday_type = 'solar'"
            >公历</button>
            <button
              class="rl-chip"
              :class="{ on: form.birthday_type === 'lunar' }"
              @click="form.birthday_type = 'lunar'"
            >农历</button>
          </div>
        </div>
        <label class="rl-field">
          <span>备注</span>
          <el-input v-model="form.notes" type="textarea" :rows="2" placeholder="他胃不好 / 刚搬家 / 别问他前公司" />
        </label>
        <p v-if="form.id" class="rl-tip rl-del" @click="removeContact">删除这个人</p>
      </div>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="!form.name.trim()" @click="submitForm">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 关系维护（v2.46.250）
 *
 * 设计三原则（夜星原话 + 我的取舍）：
 * 1. 轻：新建只要名字；记互动只点标签 + 一句话；不做「关系健康分」。
 * 2. 有触发点才打开：生日 / 有点久了 / 想起一个人。
 * 3. 隐私：数据只按 user_id 取，家里其他人看不到。
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import BackButton from '@/components/BackButton.vue'
import IconButton from '@/components/common/IconButton.vue'
import relationsApi from '@/api/relations'

const STAR_FILTERS = [
  { v: 0, label: '全部' },
  { v: 5, label: '5★' },
  { v: 4, label: '4★' },
  { v: 3, label: '3★' },
]
const CHANNELS = ['微信', '电话', '见面', '其他']
const TAGS = ['聊工作', '家事', '身体', '钱', '分享好物', '纯闲聊']

const items = ref([])
const dash = ref({ birthdays: [], overdue: [], overdue_total: 0, blind: null })
const keyword = ref('')
const star = ref(0)
const loading = ref(false)

const drawer = ref(false)
const cur = ref(null)
const icing = ref(false)
const iceLines = ref([])
const copiedIdx = ref(-1)

const logForm = ref(false)
const logTags = ref([])
const logDraft = reactive({ channel: '微信', note: '', follow_up: '' })

const dialog = ref(false)
const saving = ref(false)
const form = reactive({
  id: 0, name: '', relation: '', intimacy: 3, topics: '', notes: '',
  birthday: '', birthday_type: 'solar',
})

const isMobile = computed(() => typeof window !== 'undefined' && window.innerWidth < 760)
const drawerSize = computed(() => (isMobile.value ? '100%' : '520px'))
const hasCue = computed(
  () => dash.value.birthdays.length || dash.value.overdue.length || dash.value.blind,
)
const intimacyTip = computed(() => {
  const map = { 5: '30 天没联系就提醒你', 4: '60 天', 3: '90 天', 2: '180 天', 1: '不提醒，安静待着' }
  return map[form.intimacy] || ''
})

function stars(n) {
  const v = n || 3
  return '●'.repeat(v) + '○'.repeat(5 - v)
}

function statusText(c) {
  if (c.last_contact_at) {
    if (c.days_since === 0) return '今天聊过'
    if (c.overdue) return `${c.days_since} 天没联系了 · 超了 ${c.overdue_days} 天`
    return `${c.days_since} 天前聊过`
  }
  if (c.overdue) return '还没记过，先记一次吧'
  return '还没记过'
}

async function loadList() {
  loading.value = true
  try {
    const res = await relationsApi.list({ q: keyword.value, intimacy: star.value })
    items.value = res?.data?.items || []
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function loadDash() {
  try {
    const res = await relationsApi.dashboard()
    dash.value = res?.data || dash.value
  } catch { /* 仪表盘挂了不影响列表 */ }
}

async function openById(id) {
  const found = items.value.find((x) => x.id === id)
  if (found) return open(found)
  await loadList()
  const hit = items.value.find((x) => x.id === id)
  if (hit) open(hit)
}

async function open(c) {
  iceLines.value = []
  logForm.value = false
  logTags.value = []
  logDraft.channel = '微信'
  logDraft.note = ''
  logDraft.follow_up = ''
  drawer.value = true
  await refreshDetail(c.id)
}

async function refreshDetail(id) {
  try {
    const res = await relationsApi.detail(id)
    cur.value = res?.data || null
  } catch {
    ElMessage.error('加载详情失败')
  }
}

function openCreate() {
  Object.assign(form, {
    id: 0, name: '', relation: '', intimacy: 3, topics: '', notes: '',
    birthday: '', birthday_type: 'solar',
  })
  dialog.value = true
}

function openEdit() {
  const c = cur.value
  if (!c) return
  Object.assign(form, {
    id: c.id,
    name: c.name,
    relation: c.relation || '',
    intimacy: c.intimacy || 3,
    topics: c.topics || '',
    notes: c.notes || '',
    birthday: c.birthday_raw || '',
    birthday_type: c.birthday?.type || 'solar',
  })
  dialog.value = true
}

async function submitForm() {
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      relation: form.relation.trim(),
      intimacy: form.intimacy,
      topics: form.topics.trim(),
      notes: form.notes,
      birthday: form.birthday.trim() || null,
      birthday_type: form.birthday_type,
    }
    if (form.id) {
      await relationsApi.update(form.id, payload)
    } else {
      await relationsApi.create(payload)
    }
    dialog.value = false
    await Promise.all([loadList(), loadDash()])
    if (form.id) await refreshDetail(form.id)
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail?.msg || '保存失败')
  } finally {
    saving.value = false
  }
}

async function removeContact() {
  try {
    await ElMessageBox.confirm('删除后可以在回收站找回，确定？', '删除', { type: 'warning' })
  } catch { return }
  try {
    await relationsApi.remove(form.id)
    dialog.value = false
    drawer.value = false
    await Promise.all([loadList(), loadDash()])
    ElMessage.success('已删除')
  } catch {
    ElMessage.error('删除失败')
  }
}

function openLogForm() {
  logForm.value = true
  logDraft.note = ''
  logDraft.follow_up = ''
  logTags.value = []
}

function toggleTag(t) {
  const i = logTags.value.indexOf(t)
  if (i >= 0) logTags.value.splice(i, 1)
  else logTags.value.push(t)
}

async function submitLog() {
  if (!cur.value) return
  saving.value = true
  try {
    const res = await relationsApi.addLog(cur.value.id, {
      channel: logDraft.channel,
      tags: logTags.value.join(','),
      note: logDraft.note.trim(),
      follow_up: logDraft.follow_up.trim(),
    })
    logForm.value = false
    cur.value = { ...cur.value, ...(res?.data?.contact || {}) }
    await refreshDetail(cur.value.id)
    await Promise.all([loadList(), loadDash()])
    ElMessage.success('记下了')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail?.msg || '保存失败')
  } finally {
    saving.value = false
  }
}

async function removeLog(id) {
  try {
    await ElMessageBox.confirm('删掉这条记录？「上次联系」会跟着回退。', '删除', { type: 'warning' })
  } catch { return }
  try {
    await relationsApi.removeLog(id)
    await refreshDetail(cur.value.id)
    await Promise.all([loadList(), loadDash()])
  } catch {
    ElMessage.error('删除失败')
  }
}

async function doIcebreak() {
  if (!cur.value) return
  icing.value = true
  iceLines.value = []
  try {
    const res = await relationsApi.icebreak(cur.value.id)
    iceLines.value = res?.data?.lines || []
    if (!iceLines.value.length) ElMessage.warning('没生成出来，换个说法再试')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail?.msg || '生成失败')
  } finally {
    icing.value = false
  }
}

async function copyLine(line) {
  try {
    await navigator.clipboard.writeText(line)
    copiedIdx.value = iceLines.value.indexOf(line)
    setTimeout(() => { copiedIdx.value = -1 }, 1600)
  } catch {
    ElMessage.warning('复制失败，长按选中吧')
  }
}

onMounted(async () => {
  await Promise.all([loadList(), loadDash()])
})
</script>

<style scoped>
.rl-page { min-height: 100%; padding: 24px 16px 40px; }
.rl-inner { max-width: 820px; margin: 0 auto; }

.rl-head { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.rl-titles { flex: 1; min-width: 0; }
.rl-title { margin: 0; font-size: 20px; letter-spacing: -.01em; }
.rl-sub { margin: 2px 0 0; font-size: 12px; color: var(--tc-text-3, #5b6f8a); }

/* 三个触发点 */
.rl-cues { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-bottom: 14px; }
.rl-cue {
  padding: 10px 12px; border-radius: 12px;
  background: var(--tc-paper-2, rgba(255, 255, 255, .6));
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .1));
}
.rl-cue--bday { border-color: rgba(169, 129, 47, .3); }
.rl-cue--late { border-color: rgba(180, 85, 47, .25); }
.rl-cue-h { display: flex; align-items: center; gap: 5px; font-size: 11.5px; font-weight: 600; color: var(--tc-text-3, #5b6f8a); margin-bottom: 6px; }
.rl-cue-row {
  display: flex; align-items: baseline; justify-content: space-between; gap: 8px;
  width: 100%; padding: 3px 0; border: 0; background: transparent; cursor: pointer;
  font: inherit; text-align: left;
}
.rl-cue-row b { font-size: 13px; font-weight: 600; color: var(--tc-text, #0b1622); }
.rl-cue-row em { font-style: normal; font-size: 11px; color: var(--tc-text-3, #5b6f8a); }
.rl-cue-row:hover b { color: var(--tc-cyan-deep, #0a708c); }
.rl-cue-more { margin: 2px 0 0; font-size: 10.5px; color: var(--tc-text-3, #5b6f8a); }

/* 工具栏 */
.rl-toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
.rl-input {
  flex: 1 1 200px; min-width: 0; padding: 7px 11px; border-radius: 9px;
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .14)); background: transparent;
  font: inherit; font-size: 13px; color: var(--tc-text, #0b1622);
}
.rl-seg { display: inline-flex; gap: 4px; }
.rl-seg-btn {
  padding: 5px 10px; border-radius: 8px; cursor: pointer; font: inherit; font-size: 12px;
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .14)); background: transparent;
  color: var(--tc-text-2, #46586e);
}
.rl-seg-btn.on { border-color: var(--tc-cyan, #0e93b8); color: var(--tc-cyan-deep, #0a708c); background: rgba(14, 147, 184, .1); font-weight: 600; }
.rl-count { font-size: 11.5px; color: var(--tc-text-3, #5b6f8a); }

.rl-empty { margin: 30px 0; text-align: center; font-size: 13px; line-height: 1.9; color: var(--tc-text-3, #5b6f8a); }

/* 列表 */
.rl-list { list-style: none; margin: 0; padding: 0; }
.rl-item {
  display: flex; align-items: center; gap: 12px; padding: 11px 10px; border-radius: 11px;
  cursor: pointer; transition: background-color .15s;
}
.rl-item:hover { background: rgba(14, 147, 184, .05); }
.rl-item + .rl-item { border-top: 1px dashed var(--tc-line, rgba(15, 60, 110, .1)); }
.rl-ava, .rl-dava {
  display: grid; place-items: center; flex: none; width: 36px; height: 36px;
  border-radius: 50%; font-size: 15px; font-weight: 600;
  background: rgba(169, 129, 47, .12); color: var(--lj-seal, #a9812f);
}
.rl-main { flex: 1; min-width: 0; }
.rl-line1 { display: flex; align-items: baseline; gap: 7px; flex-wrap: wrap; }
.rl-line1 b { font-size: 14px; color: var(--tc-text, #0b1622); }
.rl-rel { font-size: 11px; padding: 1px 6px; border-radius: 5px; background: rgba(15, 60, 110, .06); color: var(--tc-text-3, #5b6f8a); }
.rl-bd { font-size: 11px; color: var(--lj-seal, #a9812f); }
.rl-line2 { margin: 3px 0 0; font-size: 11.5px; color: var(--tc-text-3, #5b6f8a); }
.rl-line2.late { color: #b4552f; }
.rl-stars { font-size: 11px; letter-spacing: 1px; color: var(--tc-cyan, #0e93b8); opacity: .7; }

/* 详情抽屉 */
.rl-detail { padding: 18px 20px 40px; }
.rl-dhead { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 14px; }
.rl-dava { width: 46px; height: 46px; font-size: 19px; }
.rl-dinfo { flex: 1; min-width: 0; }
.rl-dinfo h2 { margin: 0; font-size: 19px; }
.rl-dinfo p { margin: 3px 0 0; font-size: 12px; color: var(--tc-text-3, #5b6f8a); }
.rl-dot { margin: 0 5px; }
.rl-dstate.late { color: #b4552f; }
.rl-close { border: 0; background: transparent; font-size: 22px; line-height: 1; color: var(--tc-text-3, #5b6f8a); cursor: pointer; padding: 0 4px; }

.rl-facts { padding: 10px 12px; border-radius: 10px; background: rgba(15, 60, 110, .04); margin-bottom: 12px; }
.rl-facts p { margin: 3px 0; font-size: 12.5px; line-height: 1.7; color: var(--tc-text-2, #46586e); }
.rl-facts i { font-style: normal; display: inline-block; width: 40px; color: var(--tc-text-3, #5b6f8a); font-size: 11px; }

.rl-actions { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.rl-act {
  padding: 7px 14px; border-radius: 9px; cursor: pointer; font: inherit; font-size: 12.5px;
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .16)); background: transparent;
  color: var(--tc-text-2, #46586e);
}
.rl-act:hover { border-color: var(--tc-cyan, #0e93b8); color: var(--tc-cyan-deep, #0a708c); }
.rl-act--main { border-color: var(--tc-cyan, #0e93b8); background: rgba(14, 147, 184, .1); color: var(--tc-cyan-deep, #0a708c); font-weight: 600; }
.rl-act:disabled { opacity: .5; cursor: default; }

.rl-ice { margin-bottom: 14px; padding: 10px 12px; border-radius: 10px; background: var(--tc-seal-soft, rgba(199, 169, 107, .12)); }
.rl-ice-h { font-size: 11px; font-weight: 600; letter-spacing: .06em; color: var(--lj-seal, #a9812f); margin-bottom: 6px; }
.rl-ice-row { display: flex; align-items: flex-start; gap: 8px; padding: 5px 0; }
.rl-ice-row + .rl-ice-row { border-top: 1px dashed rgba(169, 129, 47, .2); }
.rl-ice-row p { flex: 1; margin: 0; font-size: 12.5px; line-height: 1.8; color: var(--tc-text, #0b1622); }
.rl-ice-row button {
  flex: none; border: 1px solid rgba(169, 129, 47, .3); background: transparent; border-radius: 6px;
  padding: 2px 8px; font: inherit; font-size: 10.5px; cursor: pointer; color: var(--lj-seal, #a9812f);
}

.rl-logform { margin-bottom: 14px; padding: 12px; border-radius: 10px; border: 1px dashed var(--tc-line, rgba(15, 60, 110, .2)); }
.rl-lf-row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 9px; }
.rl-chip {
  padding: 3px 10px; border-radius: 999px; cursor: pointer; font: inherit; font-size: 11.5px;
  border: 1px solid var(--tc-line, rgba(15, 60, 110, .14)); background: transparent;
  color: var(--tc-text-2, #46586e);
}
.rl-chip.on { border-color: var(--tc-cyan, #0e93b8); color: var(--tc-cyan-deep, #0a708c); background: rgba(14, 147, 184, .1); }
.rl-lf-follow { margin-top: 8px; }
.rl-lf-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px; }

.rl-timeline { margin-top: 6px; }
.rl-tl-h { font-size: 11px; font-weight: 600; letter-spacing: .08em; color: var(--tc-text-3, #5b6f8a); margin-bottom: 10px; }
.rl-tl-empty { font-size: 12px; line-height: 1.8; color: var(--tc-text-3, #5b6f8a); }
.rl-tl-item { position: relative; padding: 0 0 14px 18px; border-left: 1px solid var(--tc-line, rgba(15, 60, 110, .14)); }
.rl-tl-item:last-child { border-left-color: transparent; }
.rl-tl-dot {
  position: absolute; left: -4px; top: 5px; width: 7px; height: 7px; border-radius: 50%;
  background: var(--tc-cyan, #0e93b8);
}
.rl-tl-top { display: flex; align-items: center; gap: 7px; }
.rl-tl-top b { font-size: 12px; font-variant-numeric: tabular-nums; color: var(--tc-text-2, #46586e); }
.rl-tl-ch { font-size: 10.5px; padding: 0 5px; border-radius: 4px; background: rgba(15, 60, 110, .06); color: var(--tc-text-3, #5b6f8a); }
.rl-tl-del { margin-left: auto; border: 0; background: transparent; cursor: pointer; color: var(--tc-text-3, #5b6f8a); font-size: 15px; line-height: 1; }
.rl-tl-note { margin: 4px 0 0; font-size: 12.5px; line-height: 1.8; color: var(--tc-text, #0b1622); }
.rl-tl-tags { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 5px; }
.rl-tl-tags span { font-size: 10.5px; padding: 1px 6px; border-radius: 4px; background: rgba(14, 147, 184, .1); color: var(--tc-cyan-deep, #0a708c); }
.rl-tl-follow { margin: 5px 0 0; font-size: 11.5px; color: var(--lj-seal, #a9812f); }

/* 表单 */
.rl-form { display: flex; flex-direction: column; gap: 12px; }
.rl-field { display: flex; flex-direction: column; gap: 5px; }
.rl-field > span { font-size: 11.5px; color: var(--tc-text-3, #5b6f8a); }
.rl-tip { margin: 0; font-size: 11px; color: var(--tc-text-3, #5b6f8a); }
.rl-del { color: #b4552f; cursor: pointer; margin-top: 6px; }
.rl-bd-row { display: flex; align-items: center; gap: 6px; }
</style>
