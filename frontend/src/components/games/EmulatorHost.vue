<template>
  <!-- 经典模拟器宿主（v2.46.185）
       设计前提：**服务器不存放任何 ROM**。
       ROM 由用户在本机选择 → 存进浏览器 IndexedDB → 运行时转成 data URL 灌进隔离 iframe。
       整条链路数据不出本机，所以「站点公网可访问」也不会变成「提供 ROM 下载」。
       EmulatorJS 走官方 CDN（stable），不自托管数据文件。 -->
  <div class="em-host" :class="{ 'is-bare': bare }">
    <!-- 未运行：选择 ROM -->
    <div v-if="!frameSrc" class="em-intro">
      <div class="em-badge">EmulatorJS · 本地加载</div>
      <h3 class="em-title">经典游戏模拟器</h3>
      <p class="em-desc">
        选一个 ROM 就能玩。文件只存进<strong>这个浏览器的本地数据库</strong>，
        <strong>不会上传到服务器</strong>，换设备 / 清缓存后需要重新选择。
      </p>

      <div class="em-picks">
        <label class="em-field">
          <span>主机</span>
          <select v-model="core" class="em-sel">
            <option v-for="c in CORES" :key="c.v" :value="c.v">{{ c.label }}</option>
          </select>
        </label>
      </div>

      <div class="em-acts">
        <button class="em-btn primary" type="button" @click="pickFile">选择 ROM 文件</button>
        <button v-if="savedName" class="em-btn" type="button" @click="playSaved">
          继续：{{ savedName }}
        </button>
        <button v-if="savedName" class="em-btn ghost" type="button" @click="forget">清除已存 ROM</button>
      </div>

      <p class="em-note">
        ROM 请自备（自有卡带 dump / 开源 homebrew）。本站不提供、不存储、不分发任何 ROM。
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
async function boot(blob, name, size) {
  try {
    const dataUrl = await blobToDataUrl(blob)
    const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<style>html,body{margin:0;height:100%;background:#000;overflow:hidden}#game{width:100%;height:100%}</style>
</head><body><div id="game"></div>
<script>
  EJS_player = '#game';
  EJS_core = ${JSON.stringify(core.value)};
  EJS_gameUrl = ${JSON.stringify(dataUrl)};
  EJS_gameName = ${JSON.stringify(name)};
  EJS_pathtodata = ${JSON.stringify(CDN)};
  EJS_startOnLoaded = true;
  EJS_fullscreenOnLoaded = false;
</` + `script>
<script src="${CDN}loader.js"></` + `script>
</body></html>`

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
