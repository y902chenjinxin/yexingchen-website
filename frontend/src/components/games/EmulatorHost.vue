<template>
  <!-- 经典模拟器宿主（v2.46.185）
       设计前提：**服务器不存放任何 ROM**。
       ROM 由用户在本机选择 → 存进浏览器 IndexedDB → 运行时转成 data URL 灌进隔离 iframe。
       整条链路数据不出本机，所以「站点公网可访问」也不会变成「提供 ROM 下载」。
       EmulatorJS 走官方 CDN（stable），不自托管数据文件。 -->
  <div class="em-host" :class="{ 'is-bare': bare }">
    <!-- 未运行：选游戏 -->
    <div v-if="!frameSrc" class="em-intro">
      <div class="em-badge">内置游戏 · 点开即玩</div>
      <h3 class="em-title">经典游戏模拟器</h3>
      <p class="em-desc">
        下拉选一个<strong>内置游戏</strong>直接开玩，也可以加载自己机器上的 ROM。
      </p>

      <!-- 内置游戏：下拉即启动 -->
      <div class="em-picks">
        <label class="em-field grow">
          <span>内置游戏</span>
          <select class="em-sel grow" :value="''" @change="onPickBuiltin">
            <option value="">选一个游戏，选中即开始…</option>
            <option v-for="g in BUILTIN" :key="g.id" :value="g.id">
              {{ g.name }} · {{ g.tag }}
            </option>
          </select>
        </label>
      </div>
      <p class="em-builtin-note">
        <template v-for="g in BUILTIN" :key="g.id">
          <b>{{ g.name }}</b>：{{ g.note }}<br />
        </template>
      </p>

      <div class="em-divider"><span>或者用你自己的 ROM</span></div>

      <div class="em-picks">
        <label class="em-field">
          <span>主机</span>
          <select v-model="core" class="em-sel">
            <option v-for="c in CORES" :key="c.v" :value="c.v">{{ c.label }}</option>
          </select>
        </label>
      </div>

      <div class="em-acts">
        <button class="em-btn" type="button" @click="pickFile">选择本地 ROM</button>
        <button v-if="savedName" class="em-btn ghost" type="button" @click="playSaved">
          继续：{{ savedName }}
        </button>
        <button v-if="savedName" class="em-btn ghost" type="button" @click="forget">清除</button>
      </div>

      <p class="em-note">
        本地 ROM 只存在<strong>这个浏览器</strong>里，不上传服务器。
        内置游戏为开源 homebrew（GPL / CC），商业游戏 ROM 不提供。
      </p>
    </div>

    <!-- 运行中 -->
    <div v-else class="em-stage">
      <div class="em-bar">
        <span class="em-name" :title="romName">{{ romName }}</span>
        <span class="em-size">{{ (romSize / 1024 / 1024).toFixed(1) }} MB</span>
        <button class="em-btn sm" type="button" @click="pickFile">换 ROM</button>
        <button class="em-btn sm ghost" type="button" @click="unload">关闭</button>
      </div>
      <iframe
        :src="frameSrc"
        class="em-frame"
        allow="gamepad; fullscreen; autoplay"
        referrerpolicy="no-referrer"
      />
    </div>

    <input
      ref="fileInput"
      type="file"
      accept=".nes,.sfc,.smc,.gba,.gb,.gbc,.gbc,.n64,.z64,.bin,.iso"
      hidden
      @change="onFile"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'

defineProps({ bare: { type: Boolean, default: false } })

const CORES = [
  { v: 'nes', label: 'NES / FC（.nes）' },
  { v: 'snes', label: 'SNES / SFC（.sfc .smc）' },
  { v: 'gba', label: 'GBA（.gba）' },
  { v: 'gb', label: 'GB / GBC（.gb .gbc）' },
  { v: 'n64', label: 'N64（.n64 .z64）' },
  { v: 'segaMD', label: 'Mega Drive（.md .bin）' },
  { v: 'psx', label: 'PlayStation（.bin .iso）' },
]

const CDN = 'https://cdn.emulatorjs.org/stable/data/'

/* ---- 内置 ROM（v2.46.190）----
   全部是**明确允许再分发**的 homebrew，放在本站 /roms/ 下：
   - Nova the Squirrel：GPL-3.0（代码）+ CC BY-NC-SA 4.0（素材），作者 NovaSquirrel
   - Thwaite：作者 pinobatch，开源（GPL），GitHub releases 分发
   商业游戏（忍者神龟 / 双截龙 / 拳皇等）的 ROM 不在此列 —— 那是受版权保护的作品，
   任何来源的 ROM 都不能拿到公开站点上分发。 */
const BUILTIN = [
  { id: 'nova', name: 'Nova the Squirrel', file: 'nova.nes', core: 'nes', size: 262160,
    tag: '平台动作', note: 'GPL-3.0 / CC BY-NC-SA · 作者 NovaSquirrel' },
  { id: 'thwaite', name: 'Thwaite', file: 'thwaite.nes', core: 'nes', size: 24592,
    tag: '射击', note: '开源 · 作者 pinobatch' },
]
const DB_NAME = 'xuanhuang-emu'
const STORE = 'roms'
const KEY = 'last'

const fileInput = ref(null)
const core = ref('nes')
const frameSrc = ref('')
const romName = ref('')
const romSize = ref(0)
const savedName = ref('')

/* ---------------- IndexedDB ---------------- */
function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE)
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function dbPut(value) {
  const db = await openDb()
  await new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite')
    tx.objectStore(STORE).put(value, KEY)
    tx.oncomplete = resolve
    tx.onerror = () => reject(tx.error)
  })
  db.close()
}

async function dbGet() {
  const db = await openDb()
  const value = await new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readonly')
    const req = tx.objectStore(STORE).get(KEY)
    req.onsuccess = () => resolve(req.result || null)
    req.onerror = () => reject(req.error)
  })
  db.close()
  return value
}

async function dbDel() {
  const db = await openDb()
  await new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite')
    tx.objectStore(STORE).delete(KEY)
    tx.oncomplete = resolve
    tx.onerror = () => reject(tx.error)
  })
  db.close()
}

/* ---------------- 启动 ---------------- */
function pickFile() {
  fileInput.value?.click()
}

async function onFile(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  if (!file.size) { ElMessage.error('文件为空'); return }
  if (file.size > 64 * 1024 * 1024) { ElMessage.error('ROM 超过 64MB，暂不支持'); return }

  // 按扩展名猜主机，用户选过的就尊重用户选择
  const ext = (file.name.split('.').pop() || '').toLowerCase()
  const guess = { nes: 'nes', sfc: 'snes', smc: 'snes', gba: 'gba', gb: 'gb', gbc: 'gb', n64: 'n64', z64: 'n64' }[ext]
  if (guess) core.value = guess

  const blob = file.slice(0, file.size, 'application/octet-stream')
  try {
    await dbPut({ name: file.name, size: file.size, core: core.value, blob })
    savedName.value = file.name
  } catch {
    ElMessage.warning('ROM 保存失败（浏览器可能禁用了本地存储），本次仍可继续玩')
  }
  await boot(blob, file.name, file.size)
}

async function playSaved() {
  try {
    const rec = await dbGet()
    if (!rec) { savedName.value = ''; ElMessage.warning('没有已保存的 ROM'); return }
    core.value = rec.core || 'nes'
    await boot(rec.blob, rec.name, rec.size)
  } catch (e) {
    ElMessage.error('读取失败：' + (e?.message || '未知错误'))
  }
}

async function forget() {
  try {
    await dbDel()
    savedName.value = ''
    ElMessage.success('已清除本机保存的 ROM')
  } catch {
    ElMessage.error('清除失败')
  }
}

function unload() {
  revoke()
  frameSrc.value = ''
  romName.value = ''
  romSize.value = 0
}

/* ---------------- 生成 iframe ---------------- */
let currentUrl = ''

function revoke() {
  if (currentUrl) { URL.revokeObjectURL(currentUrl); currentUrl = '' }
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const fr = new FileReader()
    fr.onload = () => resolve(String(fr.result))
    fr.onerror = () => reject(fr.error)
    fr.readAsDataURL(blob)
  })
}

/** ROM 用 data URL 内联进 iframe 的 HTML：
 *  iframe 用 blob 承载时是 opaque origin，直接引用父页面的 blob URL 会被拦；
 *  data URL 不涉及网络与跨源，最稳，且整份 ROM 只在内存里。 */
/** 直接按 URL 启动（内置 ROM 走这条，不需要读本地文件） */
function bootFromUrl(url, name, size, coreId) {
  const html = buildFrameHtml(url, name, coreId || 'nes')
  revoke()
  currentUrl = URL.createObjectURL(new Blob([html], { type: 'text/html' }))
  romName.value = name
  romSize.value = size || 0
  frameSrc.value = currentUrl
}

/** 下拉选中即启动 */
function onPickBuiltin(e) {
  const id = e && e.target ? e.target.value : ''
  if (!id) return
  const item = BUILTIN.find((g) => g.id === id)
  if (item) playBuiltin(item)
  if (e && e.target) e.target.value = ''
}

/** 内置游戏：点一下直接玩 */
function playBuiltin(item) {
  core.value = item.core || 'nes'
  // iframe 由 blob 承载，是不透明来源 —— 相对路径 / 无法解析（会报 Invalid URL）
  // 必须给完整绝对地址；/roms/ 已带 Access-Control-Allow-Origin *
  const base = (typeof location !== 'undefined' && location.origin) || ''
  bootFromUrl(`${base}/roms/${item.file}`, item.name, item.size, item.core)
}

function buildFrameHtml(gameUrl, name, coreId) {
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<style>html,body{margin:0;height:100%;background:#000;overflow:hidden}#game{width:100%;height:100%}</style>
</head><body><div id="game"></div>
<script>
  EJS_player = '#game';
  EJS_core = ${JSON.stringify(coreId || 'nes')};
  EJS_gameUrl = ${JSON.stringify(gameUrl)};
  EJS_gameName = ${JSON.stringify(name)};
  EJS_pathtodata = ${JSON.stringify(CDN)};
  EJS_startOnLoaded = true;
  EJS_fullscreenOnLoaded = false;
</` + `script>
<script src="${CDN}loader.js"></` + `script>
</body></html>`
}

async function boot(blob, name, size) {
  try {
    const dataUrl = await blobToDataUrl(blob)
    const html = buildFrameHtml(dataUrl, name, core.value)

    revoke()
    currentUrl = URL.createObjectURL(new Blob([html], { type: 'text/html' }))
    romName.value = name
    romSize.value = size
    frameSrc.value = currentUrl
  } catch (e) {
    ElMessage.error('启动失败：' + (e?.message || '未知错误'))
  }
}

onMounted(async () => {
  try {
    const rec = await dbGet()
    if (rec?.name) { savedName.value = rec.name; core.value = rec.core || 'nes' }
  } catch { /* 忽略：本地库不可用不影响手动选择 */ }
})

onBeforeUnmount(() => {
  revoke()
})
</script>

<style scoped>
.em-host { height: 100%; min-height: 0; display: flex; flex-direction: column; }
.em-host.is-bare { padding: 0; }

/* 未运行 */
.em-intro {
  margin: auto; max-width: 560px; padding: 28px 24px; text-align: center;
  border-radius: 18px; border: 1px solid var(--color-border, rgba(140, 160, 180, .22));
  background: var(--color-surface, rgba(255, 255, 255, .04));
}
.em-badge {
  display: inline-block; margin-bottom: 12px; padding: 3px 10px; border-radius: 999px;
  font-size: 11px; letter-spacing: .08em; color: var(--color-text-3, #8b98a8);
  background: rgba(140, 160, 180, .12);
}
.em-title { margin: 0 0 10px; font-size: 20px; color: var(--color-text, #e8eef5); }
.em-desc { margin: 0 0 18px; font-size: 13px; line-height: 1.7; color: var(--color-text-2, #a8b6c6); }
.em-desc strong { color: var(--color-text, #e8eef5); }
.em-picks { display: flex; justify-content: center; gap: 12px; margin-bottom: 18px; flex-wrap: wrap; }
.em-field { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--color-text-2, #a8b6c6); }
.em-sel {
  padding: 6px 10px; border-radius: 8px; font-size: 13px;
  border: 1px solid var(--color-border, rgba(140, 160, 180, .28));
  background: var(--color-surface-2, rgba(255, 255, 255, .06));
  color: var(--color-text, #e8eef5);
}
.em-acts { display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; }
.em-btn {
  padding: 9px 18px; border-radius: 10px; font-size: 13px; cursor: pointer;
  border: 1px solid var(--color-border, rgba(140, 160, 180, .3));
  background: var(--color-surface-2, rgba(255, 255, 255, .06));
  color: var(--color-text, #e8eef5); transition: all .2s;
}
.em-btn:hover { border-color: var(--color-accent, #c7a96b); }
.em-btn.primary {
  background: linear-gradient(135deg, rgba(199, 169, 107, .85), rgba(127, 168, 163, .85));
  border-color: transparent; color: #fff; font-weight: 600;
}
.em-btn.ghost { background: transparent; color: var(--color-text-3, #8b98a8); }
.em-btn.sm { padding: 5px 12px; font-size: 12px; }
.em-note { margin: 16px 0 0; font-size: 11.5px; line-height: 1.6; color: var(--color-text-3, #8b98a8); }
.em-field.grow, .em-sel.grow { flex: 1; min-width: 0; }
.em-builtin-note {
  margin: 0 0 16px; font-size: 11.5px; line-height: 1.7; text-align: left;
  color: var(--color-text-3, #8b98a8); padding: 0 4px;
}
.em-builtin-note b { color: var(--color-text-2, #a8b6c6); font-weight: 600; }
.em-divider {
  display: flex; align-items: center; gap: 12px; margin: 18px 0;
  font-size: 11.5px; color: var(--color-text-3, #8b98a8);
}
.em-divider::before, .em-divider::after {
  content: ''; flex: 1; height: 1px; background: var(--color-border, rgba(140, 160, 180, .22));
}

/* 运行中 */
.em-stage { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 8px; }
.em-bar {
  display: flex; align-items: center; gap: 10px; padding: 0 4px;
  font-size: 12px; color: var(--color-text-2, #a8b6c6);
}
.em-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.em-size { color: var(--color-text-3, #8b98a8); }
.em-frame {
  flex: 1; min-height: 0; width: 100%; border: 0; border-radius: 12px;
  background: #000; display: block;
}
</style>
