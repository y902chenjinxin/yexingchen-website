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
          <span>游戏</span>
          <select class="em-sel grow" :value="''" @change="onPickRom">
            <option value="">{{ romLoading ? '读取中…' : '选一个游戏，选中即开始…' }}</option>
            <optgroup label="内置（开源）">
              <option v-for="g in romLib.builtin" :key="'b-' + g.file" :value="'b:' + g.file">
                {{ g.label }}{{ g.tag ? ' · ' + g.tag : '' }}
              </option>
            </optgroup>
            <optgroup v-if="romLib.uploaded.length" label="我上传的">
              <option v-for="g in romLib.uploaded" :key="'u-' + g.file" :value="'u:' + g.file">
                {{ g.label }}
              </option>
            </optgroup>
          </select>
        </label>
      </div>
      <p class="em-builtin-note">
        <template v-for="g in romLib.builtin" :key="'n-' + g.file">
          <b>{{ g.label }}</b>：{{ g.credit }}<br />
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
        <button class="em-btn primary" type="button" @click="uploadInput?.click()">上传 ROM（可多选，支持 zip）</button>
        <button class="em-btn" type="button" @click="pickFile">本地直接玩（不落盘）</button>
        <button v-if="savedName" class="em-btn ghost" type="button" @click="playSaved">
          继续：{{ savedName }}
        </button>
        <button v-if="savedName" class="em-btn ghost" type="button" @click="forget">清除本地缓存</button>
      </div>

      <p class="em-note">
        <strong>上传到服务器</strong>：存进你自己的目录，以后直接在下拉里选，换设备也能玩（上限 64MB）。<br />
        <strong>本地直接玩</strong>：只在浏览器内存里跑，服务器不留文件。<br />
        内置游戏为开源 homebrew（GPL / CC）；本模块不预置任何商业游戏 ROM。
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
      ref="uploadInput"
      type="file"
      multiple
      accept=".zip,.nes,.sfc,.smc,.gba,.gb,.gbc,.md,.gen,.bin,.iso,.n64,.z64"
      hidden
      @change="onUploadFile"
    />
    <input
      ref="fileInput"
      type="file"
      accept=".zip,.nes,.sfc,.smc,.gba,.gb,.gbc,.n64,.z64,.bin,.iso"
      hidden
      @change="onFile"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { listRoms, uploadRom } from '@/api/emulator'
import JSZip from 'jszip'

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

/* ---- ROM 库（v2.46.192）----
   列表来自后端 `GET /api/emulator/roms`：
   - builtin：随项目发布的**开源 homebrew**（只读，Nova the Squirrel / Thwaite）
   - uploaded：**本账号自己上传**的文件，存在服务器 roms/user/ 下
   本模块不预置任何商业游戏 ROM。 */
/* 本地 ROM 缓存（IndexedDB）：用于「本地直接玩」记住上次的文件 */
const DB_NAME = 'xuanhuang-emu'
const STORE = 'roms'
const KEY = 'last'

const romLib = ref({ builtin: [], uploaded: [] })
const romLoading = ref(false)

async function loadRoms() {
  romLoading.value = true
  try {
    const res = await listRoms()
    romLib.value = res.data || { builtin: [], uploaded: [] }
  } catch { /* 列表拉不到不阻塞本地 ROM */ }
  finally { romLoading.value = false }
}

const fileInput = ref(null)
const uploadInput = ref(null)
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
  const picked = Array.from(e.target.files || [])
  e.target.value = ''
  let file = picked[0]
  if (!file) return

  // zip 先解包（取里面层级最浅的 ROM；本地播放只播一个）
  if (isZipFile(file)) {
    const got = await expandFiles([file])
    if (!got.length) return
    file = got[0]
    if (got.length > 1) ElMessage.info(`已从压缩包里取出 ${got.length} 个 ROM，先播放「${file.name}」`)
  }

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
function onPickRom(e) {
  const v = e && e.target ? e.target.value : ''
  if (e && e.target) e.target.value = ''
  if (!v) return
  const [kind, file] = [v.slice(0, 1), v.slice(2)]
  const pool = kind === 'b' ? romLib.value.builtin : romLib.value.uploaded
  const item = (pool || []).find((g) => g.file === file)
  if (item) playServerRom(item)
}

/** 播放服务器上的 ROM（内置或已上传），用完整绝对地址 */
function playServerRom(item) {
  core.value = item.core || 'nes'
  const base = (typeof location !== 'undefined' && location.origin) || ''
  bootFromUrl(`${base}${item.url}`, item.label || item.file, item.size, item.core)
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

/* ---------------- zip 支持（v2.46.220） ----------------
   夜星反馈："在 D 盘下载了游戏 zip，但不给我上传"。
   原因：accept 只列了裸 ROM 后缀，zip 在文件选择器里是灰的；
   后端也只认裸 ROM（服务器不存压缩包）。而 ROM 站下载的基本都是 zip。

   做法：**在前端解压**，取出里面的 ROM 文件再逐个上传/播放。
   服务器上仍然只有 ROM 文件，不改变"不存商业 ROM 包"的前提。 */

/** 与后端 EXT_CORE 对齐：只认这些后缀 */
const ROM_EXTS = ['.nes', '.sfc', '.smc', '.gba', '.gb', '.gbc', '.md', '.gen', '.bin', '.iso', '.n64', '.z64']

function isZipFile(f) {
  return /\.zip$/i.test(f.name || '') || f.type === 'application/zip' || f.type === 'application/x-zip-compressed'
}

/** 从 zip 条目里挑 ROM：跳过 Mac 垃圾/隐藏文件，层级浅的排前面 */
function pickRoms(entries) {
  return entries
    .filter((e) => {
      const n = e.name.toLowerCase()
      if (n.includes('__macosx') || n.startsWith('.')) return false
      return ROM_EXTS.some((x) => n.endsWith(x))
    })
    .sort((a, b) => a.name.split('/').length - b.name.split('/').length)
}

/**
 * 解不开时告诉用户包里**到底是什么**（v2.46.221）。
 *
 * 原来只甩一句"没找到 ROM 文件"，用户不知道是自己下错了还是我们认不出。
 * 华军软件园这类站下的"双截龙"往往是 **Windows 版（含 setup.exe）**，
 * 跟模拟器能跑的主机 ROM 完全是两种东西 —— 必须说清楚，否则用户会一直重试。
 */
function describeEntries(entries) {
  const names = entries.map((e) => (e.name.split('/').pop() || '').toLowerCase())
  const hasExe = names.some((n) => n.endsWith('.exe'))
  const hasDll = names.some((n) => n.endsWith('.dll'))
  const sample = entries.slice(0, 4).map((e) => e.name.split('/').pop()).join('、')
  const more = entries.length > 4 ? ` 等 ${entries.length} 个文件` : ''

  if (hasExe || hasDll) {
    return `这是 Windows 游戏（${sample}${more}），要在电脑上安装运行；`
      + '这个模拟器只能跑主机 ROM（.nes / .sfc / .gba / .md / .bin 等）。'
  }
  // 街机 MAME romset：一堆无扩展名或纯数字分片
  const weird = names.filter((n) => !n.includes('.')).length
  if (entries.length > 3 && weird >= entries.length * 0.6) {
    return `包里是 ${entries.length} 个没有扩展名的分片文件（${sample}${more}），`
      + '看起来像街机 MAME romset；当前只支持主机 ROM（.nes / .sfc / .gba / .md 等）。'
  }
  return `包内是：${sample}${more}，没有模拟器支持的 ROM 后缀（.nes / .sfc / .gba / .md / .bin / .iso 等）。`
}

/**
 * 把选中的文件展开成待处理的 File 列表：
 * zip 自动解包（**最多两层**，街机包常是 zip 套 zip），普通 ROM 原样返回。
 */
async function expandFiles(files, depth = 0) {
  const out = []
  for (const f of files) {
    if (!isZipFile(f)) { out.push(f); continue }

    let entries
    try {
      const zip = await JSZip.loadAsync(f)
      entries = Object.values(zip.files || {}).filter((e) => !e.dir)
    } catch (err) {
      ElMessage.error(`「${f.name}」解压失败：${err?.message || '不是有效的 zip（可能已损坏，或其实是 rar/7z 改了后缀）'}`)
      continue
    }

    const roms = pickRoms(entries)
    if (roms.length) {
      for (const e of roms) {
        const blob = await e.async('blob')
        const base = (e.name.split('/').pop() || 'rom').trim()
        out.push(new File([blob], base, { type: 'application/octet-stream' }))
      }
      if (roms.length > 1) ElMessage.info(`「${f.name}」里有 ${roms.length} 个 ROM，已全部取出`)
      continue
    }

    // 包里没有裸 ROM：再试一层（街机 romset 是 zip 里放 zip）
    const innerZips = entries.filter((e) => /\.zip$/i.test(e.name) && !/__macosx/i.test(e.name))
    if (innerZips.length && depth < 1) {
      const inner = []
      for (const iz of innerZips) {
        const blob = await iz.async('blob')
        inner.push(new File([blob], (iz.name.split('/').pop() || 'inner.zip'), { type: 'application/zip' }))
      }
      const got = await expandFiles(inner, depth + 1)
      if (got.length) { out.push(...got); continue }
      ElMessage.warning(`「${f.name}」里 ${innerZips.length} 个内层压缩包解开后也没有 ROM。`)
      continue
    }

    ElMessage.warning(`「${f.name}」—— ${describeEntries(entries)}`)
  }
  return out
}

/** 上传自己的 ROM（支持一次选多个，逐个传，存到服务器 roms/user/） */
async function onUploadFile(e) {
  const picked = Array.from(e?.target?.files || [])
  if (e?.target) e.target.value = ''
  if (!picked.length) return

  // 先解包再判大小：zip 本身可能超过 64MB，但里面的 ROM 是小的
  const files = await expandFiles(picked)
  if (!files.length) return

  // 常见压缩格式里只有 zip 能直接读；7z/rar 得先自己解压
  const unsupported = files.filter((f) => !ROM_EXTS.some((x) => f.name.toLowerCase().endsWith(x)))
  if (unsupported.length) {
    ElMessage.warning(`只能直接传 zip 或 ROM 文件：${unsupported.map((f) => f.name).join('、')}（7z/rar 请先解压）`)
  }
  const usable = files.filter((f) => ROM_EXTS.some((x) => f.name.toLowerCase().endsWith(x)))
  if (!usable.length) return

  const tooBig = usable.filter((f) => f.size > 64 * 1024 * 1024)
  const ok = usable.filter((f) => f.size <= 64 * 1024 * 1024)
  if (tooBig.length) ElMessage.warning(`${tooBig.length} 个文件超过 64MB，已跳过`)
  if (!ok.length) return

  let done = 0
  const failed = []
  for (const f of ok) {
    const fd = new FormData()
    fd.append('file', f)
    fd.append('label', f.name.replace(/\.[^.]+$/, ''))
    try {
      await uploadRom(fd)
      done++
    } catch (err) {
      failed.push(`${f.name}（${err?.response?.data?.msg || err?.message || '失败'}）`)
    }
  }
  if (done) ElMessage.success(`已上传 ${done} 个，下拉里可以选了`)
  if (failed.length) ElMessage.error('失败：' + failed.join('; '))
  await loadRoms()
}

onMounted(async () => {
  loadRoms()
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
