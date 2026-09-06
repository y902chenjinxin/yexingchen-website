<template>
  <div class="ted">
    <div class="ted-head">
      <h3 class="ted-title">{{ isEdit ? '编辑旅程' : '记下旅程' }}</h3>
      <span class="ted-sub">{{ isEdit ? '修改这段行程足迹' : '记录曾走过的地方与那一段故事' }}</span>
    </div>

    <div class="ted-grid">
      <!-- 左：基本信息 -->
      <div class="ted-col">
        <div class="ted-field">
          <label class="ted-label">行程名称 <i>*</i></label>
          <input v-model="d.title" class="ted-input" placeholder="如：江南山水 · 杭州绍兴三日" />
        </div>

        <div class="ted-row">
          <div class="ted-field">
            <label class="ted-label">出发日期</label>
            <input v-model="d.start_date" type="date" class="ted-input" />
          </div>
          <div class="ted-field">
            <label class="ted-label">结束日期</label>
            <input v-model="d.end_date" type="date" class="ted-input" />
          </div>
        </div>

        <div class="ted-field">
          <label class="ted-label">一句话摘要</label>
          <input v-model="d.summary" class="ted-input" placeholder="时间线卡片上的副标题" />
        </div>

        <div class="ted-field">
          <label class="ted-label">标签（逗号分隔）</label>
          <input v-model="d.tags" class="ted-input" placeholder="海边 · 古镇 · 亲子" />
        </div>

        <div class="ted-field">
          <label class="ted-label">评价星级</label>
          <div class="ted-stars">
            <button v-for="n in 5" :key="n" type="button" class="ted-star" :class="{ on: d.star >= n }" @click="d.star = n">★</button>
            <span class="ted-star-empty">{{ makeStars(d.star) }}</span>
          </div>
        </div>

        <div class="ted-field">
          <label class="ted-label">浏览权限</label>
          <div class="ted-vis">
            <label class="ted-radio">
              <input type="radio" value="1" v-model="d.is_public" /> 公开（访客可看）
            </label>
            <label class="ted-radio">
              <input type="radio" value="0" v-model="d.is_public" /> 仅自己可见
            </label>
          </div>
        </div>
      </div>

      <!-- 右：城市 + 内容 -->
      <div class="ted-col">
        <div class="ted-field">
          <label class="ted-label">途经城市（按顺序添加）</label>
          <div class="ted-citylist">
            <div v-for="(c, i) in d.cities" :key="i" class="ted-city">
              <span class="ted-city-seq">{{ i + 1 }}</span>
              <span class="ted-city-name">{{ c.city }}<em v-if="c.province"> · {{ c.province }}</em></span>
              <span class="ted-city-ops">
                <button type="button" class="ted-city-btn" :disabled="i === 0" @click="move(i, -1)">↑</button>
                <button type="button" class="ted-city-btn" :disabled="i === d.cities.length - 1" @click="move(i, 1)">↓</button>
                <button type="button" class="ted-city-btn danger" @click="d.cities.splice(i, 1)">✕</button>
              </span>
            </div>
            <TravelCityPicker @add="onCityAdd" :cities="d.cities" />
          </div>
        </div>
      </div>
    </div>

    <!-- 封面 / 相册 -->
    <div class="ted-field">
      <label class="ted-label">封面 & 相册（可传多张）</label>
      <div class="ted-photos">
        <div v-for="(p, i) in d.photos" :key="i" class="ted-photo">
          <img :src="p" alt="" />
          <button type="button" class="ted-photo-del" @click="d.photos.splice(i, 1)">✕</button>
        </div>
        <label class="ted-photo-add">
          <input type="file" accept="image/*" multiple hidden @change="onPhotos" />
          <span class="ted-add-plus">＋</span>
          <span class="ted-add-txt">传图</span>
        </label>
      </div>
    </div>

    <!-- 视频 -->
    <div class="ted-field">
      <label class="ted-label">视频（可选，mp4/webm/mov ≤200MB）</label>
      <div class="ted-video-row">
        <label class="ted-upload-btn">
          <input type="file" accept="video/*" hidden @change="onVideo" />{{ d.busyUploading ? '上传中…' : (d.video ? '重新上传视频' : '上传视频') }}
        </label>
        <input v-model.trim="d.video" class="ted-input" placeholder="或粘贴视频链接" />
        <button v-if="d.video" type="button" class="ted-city-btn danger" @click="d.video = ''">清除</button>
      </div>
      <video v-if="d.video && isVideoUrl(d.video)" :src="d.video" controls class="ted-video" @error="onVideoError"></video>
    </div>

    <!-- 游记正文 markdown -->
    <div class="ted-field">
      <label class="ted-label">游记（Markdown 可写 # 标题 / **加粗** / 列表）</label>
      <textarea v-model="d.markdown" class="ted-textarea" rows="7"
        placeholder="把这一路的心情写下来…
# 初见西湖
三天两夜，杭州的雨把屋檐洗得发亮…"></textarea>
    </div>

    <div class="ted-actions">
      <button class="ted-btn ghost" @click="emit('cancel')">取消</button>
      <button class="ted-btn" :disabled="busy" @click="submit">{{ busy ? '保存中…' : '保存足迹' }}</button>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import TravelCityPicker from './TravelCityPicker.vue'
import { uploadMedia } from '@/api/travels'

const props = defineProps({
  initial: { type: Object, default: null },
  busy: { type: Boolean, default: false }
})
const emit = defineEmits(['save', 'cancel'])
const isEdit = !!props.initial

const d = reactive({
  title: props.initial?.title || '',
  start_date: props.initial?.start_date || '',
  end_date: props.initial?.end_date || '',
  summary: props.initial?.summary || '',
  cover: props.initial?.cover || '',
  tags: (props.initial?.tags || []).join('，'),
  star: props.initial?.star || 0,
  is_public: String(props.initial?.is_public ?? 1),
  markdown: props.initial?.markdown || '',
  photos: [...(props.initial?.photos || [])],
  video: props.initial?.video || '',
  cities: [...(props.initial?.cities || [])].map((c) => ({ city: c.city, province: c.province, lon: c.lon, lat: c.lat })),
  busyUploading: false
})

function makeStars(n) { return n ? '' : '未评分' }
function isVideoUrl(u) { return /\.(mp4|webm|mov)(\?|$)/i.test(u || '') }
function onVideoError() { }

async function onPhotos(e) {
  const files = Array.from(e.target.files || [])
  e.target.value = ''
  if (!files.length) return
  d.busyUploading = true
  try {
    for (const f of files) {
      const r = await uploadMedia('image', f)
      if (r && r.data && r.data.url) d.photos.push(r.data.url)
    }
    if (!d.cover) d.cover = d.photos[0] || ''
  } finally {
    d.busyUploading = false
  }
}

async function onVideo(e) {
  const f = e.target.files && e.target.files[0]
  e.target.value = ''
  if (!f) return
  d.busyUploading = true
  try {
    const r = await uploadMedia('video', f)
    if (r && r.data && r.data.url) d.video = r.data.url
  } finally {
    d.busyUploading = false
  }
}

function onCityAdd(c) {
  const { city, province, lon, lat } = c
  if (d.cities.some((x) => x.city === city)) return
  d.cities.push({ city, province, lon, lat })
}
function move(i, dir) {
  const j = i + dir
  if (j < 0 || j >= d.cities.length) return
  const t = d.cities[i]; d.cities[i] = d.cities[j]; d.cities[j] = t
}
function submit() {
  if (!d.title.trim()) { d.title = '未命名行程' }
  const payload = {
    title: d.title.trim(),
    summary: d.summary.trim(),
    markdown: d.markdown,
    cover: d.cover || d.photos[0] || '',
    start_date: d.start_date || null,
    end_date: d.end_date || null,
    star: d.star,
    tags: d.tags.split(/[,，]/).map((x) => x.trim()).filter(Boolean),
    photos: d.photos,
    video: d.video,
    is_public: Number(d.is_public),
    cities: d.cities.map((c, i) => ({ ...c, seq: i }))
  }
  emit('save', payload)
}
</script>

<style scoped>
.ted { padding: 18px; border-radius: 16px; background: var(--lj-glass); -webkit-backdrop-filter: var(--lj-glass-blur); backdrop-filter: var(--lj-glass-blur);
  border: 1px solid var(--lj-line); box-shadow: var(--glass-highlight), var(--glass-shadow); }
.ted-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 16px; }
.ted-title { margin: 0; font-size: 18px; letter-spacing: .1em; color: var(--lj-text); }
.ted-sub { font-size: 12px; color: var(--lj-text-3); }
.ted-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.ted-col { display: flex; flex-direction: column; gap: 12px; }
.ted-field { display: flex; flex-direction: column; gap: 6px; }
.ted-label { font-size: 12px; letter-spacing: .08em; color: var(--lj-text-2); }
.ted-label i { color: var(--lj-vermilion, #c23c3c); font-style: normal; }
.ted-input { padding: 8px 12px; border-radius: 10px; border: 1px solid var(--lj-line); background: rgba(255,255,255,.04); color: var(--lj-text); font-size: 13.5px; outline: none; box-sizing: border-box; width: 100%; }
.ted-input:focus { border-color: var(--lj-dai); }
.ted-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.ted-stars { display: flex; align-items: center; gap: 3px; }
.ted-star { font-size: 20px; line-height: 1; border: none; background: none; color: rgba(120,135,145,.25); cursor: pointer; }
.ted-star.on { color: var(--lj-ochre, #C7A96B); }
.ted-star-empty { margin-left: 8px; font-size: 11px; color: var(--lj-text-3); }
.ted-vis { display: flex; gap: 18px; font-size: 13px; color: var(--lj-text-2); }
.ted-radio { display: inline-flex; align-items: center; gap: 5px; cursor: pointer; }
.ted-citylist { display: flex; flex-direction: column; gap: 6px; }
.ted-city { display: flex; align-items: center; gap: 8px; padding: 7px 10px; border-radius: 9px; border: 1px solid var(--lj-line); background: rgba(255,255,255,.03); }
.ted-city-seq { width: 20px; height: 20px; border-radius: 50%; background: rgba(127,168,163,.16); color: var(--lj-dai, #7FA8A3); font-size: 11px; display: grid; place-items: center; flex: none; }
.ted-city-name { flex: 1; font-size: 13px; color: var(--lj-text); }
.ted-city-name em { font-style: normal; font-size: 11px; color: var(--lj-text-3); }
.ted-city-ops { display: flex; gap: 4px; flex: none; }
.ted-city-btn { padding: 2px 7px; border-radius: 6px; border: 1px solid var(--lj-line); background: none; color: var(--lj-text-2); cursor: pointer; font-size: 12px; }
.ted-city-btn:disabled { opacity: .35; cursor: not-allowed; }
.ted-city-btn.danger { color: var(--lj-vermilion, #c23c3c); }
.ted-photos { display: flex; flex-wrap: wrap; gap: 10px; }
.ted-photo { position: relative; width: 84px; height: 84px; border-radius: 10px; overflow: hidden; border: 1px solid var(--lj-line); }
.ted-photo img { width: 100%; height: 100%; object-fit: cover; }
.ted-photo-del { position: absolute; top: 3px; right: 3px; width: 18px; height: 18px; border-radius: 50%; border: none; background: rgba(0,0,0,.6); color: #fff; font-size: 11px; cursor: pointer; line-height: 1; }
.ted-photo-add { width: 84px; height: 84px; border-radius: 10px; border: 1px dashed var(--lj-line); display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; color: var(--lj-text-3); }
.ted-photo-add:hover { border-color: var(--lj-dai); color: var(--lj-dai); }
.ted-add-plus { font-size: 22px; line-height: 1; }
.ted-add-txt { font-size: 11px; }
.ted-video-row { display: flex; gap: 10px; align-items: center; }
.ted-upload-btn { flex: none; padding: 8px 14px; border-radius: 10px; border: 1px solid var(--lj-line); background: rgba(255,255,255,.05); color: var(--lj-text); font-size: 13px; cursor: pointer; }
.ted-video { margin-top: 8px; max-width: 100%; max-height: 300px; border-radius: 10px; }
.ted-textarea { width: 100%; box-sizing: border-box; min-height: 160px; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--lj-line); background: rgba(255,255,255,.04); color: var(--lj-text); font-size: 13.5px; line-height: 1.7; resize: vertical; outline: none; font-family: inherit; }
.ted-textarea:focus { border-color: var(--lj-dai); }
.ted-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; }
.ted-btn { padding: 9px 22px; border-radius: 999px; border: 1px solid var(--lj-line-strong); background: linear-gradient(135deg, rgba(127,168,163,.25), rgba(199,169,107,.16)); color: var(--lj-text); font-size: 13.5px; cursor: pointer; }
.ted-btn.ghost { background: none; border-color: var(--lj-line); color: var(--lj-text-2); }
.ted-btn:disabled { opacity: .5; cursor: not-allowed; }
@media (max-width: 760px) { .ted-grid { grid-template-columns: 1fr; } }
</style>