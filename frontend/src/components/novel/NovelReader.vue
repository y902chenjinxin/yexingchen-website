<template>
  <!-- 小说阅读器（v2.46.196）
       集成在小说模块内部，直接读 novels 表的原始文件，不依赖外部应用。
       EPUB 走 epub.js，TXT 前端分章后自己渲染。
       全屏覆盖层（z-index 1600，与项目全屏约定一致）。 -->
  <div class="nrd" :class="`theme-${theme}`" :style="cssVars">
    <!-- 顶栏 -->
    <header class="nrd-bar">
      <button class="nrd-ic" type="button" title="返回" @click="$emit('close')">←</button>
      <div class="nrd-title">
        <span class="nrd-name">{{ novel.title }}</span>
        <span class="nrd-pct">{{ percent }}%</span>
      </div>
      <button class="nrd-ic" type="button" title="目录" @click="tocOpen = !tocOpen">☰</button>
      <button class="nrd-ic" type="button" title="设置" @click="setOpen = !setOpen">Aa</button>
    </header>

    <!-- 加载 / 错误 -->
    <div v-if="loading" class="nrd-mask">
      <div class="nrd-loading">正在解析《{{ novel.title }}》…</div>
    </div>
    <div v-else-if="error" class="nrd-mask">
      <div class="nrd-err">
        <p>{{ error }}</p>
        <button class="nrd-btn" type="button" @click="$emit('close')">返回书架</button>
      </div>
    </div>

    <!-- EPUB 容器 -->
    <!-- 🔴 不能加 v-show="!loading"：loading 期间 stage 是 display:none，尺寸为 0，
       epub.js 会在 0×0 容器里渲染，加载完显示出来就是一片空白（实测踩过）。
       遮罩 .nrd-mask 本来就盖在正文区上，不需要靠隐藏 stage 来挡。 -->
    <div v-show="!error && kind === 'epub'" ref="epubRef" class="nrd-stage" />

    <!-- TXT 容器（v2.46.201）
         分页模式：CSS 多列，一列 = 一页，翻页整体 translateX，一页正好填满屏幕；
         滚动模式：连续上下滑，滚到接近底部按章懒加载下一章。 -->
    <div
      v-show="!error && kind === 'txt'"
      ref="txtRef"
      class="nrd-stage nrd-txt"
      :class="{ 'is-paged': flow === 'paginated' }"
      @scroll.passive="onTxtScroll"
    >
      <div ref="colsRef" class="nrd-txt-cols" :style="colsStyle">
        <template v-if="flow === 'paginated'">
          <h2 v-if="txtChapter" class="nrd-ch-title">{{ txtChapter.title }}</h2>
          <p v-for="(para, i) in txtParas" :key="'p' + i" class="nrd-p">{{ para }}</p>
          <div v-if="txtChapter && txtIndex >= txtChapters.length - 1" class="nrd-end">— 全书完 —</div>
        </template>
        <template v-else>
          <section v-for="sec in loadedSecs" :key="'s' + sec.idx" class="nrd-sec">
            <h2 class="nrd-ch-title">{{ sec.title }}</h2>
            <p v-for="(para, i) in sec.paras" :key="'q' + i" class="nrd-p">{{ para }}</p>
          </section>
          <div v-if="loadedSecs.length >= txtChapters.length" class="nrd-end">— 全书完 —</div>
        </template>
      </div>
    </div>

    <!-- 底部：进度 + 翻页 -->
    <footer class="nrd-foot">
      <button class="nrd-nav" type="button" :disabled="atStart" @click="goPrev">上一页</button>
      <div class="nrd-prog">
        <i :style="{ width: percent + '%' }" />
      </div>
      <button class="nrd-nav" type="button" @click="goNext">下一页</button>
    </footer>

    <!-- 目录抽屉 -->
    <transition name="nrd-fade">
      <aside v-if="tocOpen" class="nrd-toc">
        <div class="nrd-toc-head">
          <span>目录</span>
          <button class="nrd-ic" type="button" @click="tocOpen = false">×</button>
        </div>
        <div class="nrd-toc-list">
          <button
            v-for="(item, i) in toc"
            :key="i"
            class="nrd-toc-item"
            :class="{ active: i === tocActive }"
            type="button"
            @click="jumpTo(i)"
          >
            {{ item.label }}
          </button>
          <p v-if="!toc.length" class="nrd-toc-empty">这本没有可用目录</p>
        </div>
      </aside>
    </transition>

    <!-- 设置面板 -->
    <transition name="nrd-fade">
      <div v-if="setOpen" class="nrd-set">
        <div class="nrd-set-row">
          <span>主题</span>
          <div class="nrd-seg">
            <button
              v-for="t in THEMES"
              :key="t.key"
              type="button"
              :class="{ on: theme === t.key }"
              @click="setTheme(t.key)"
            >{{ t.label }}</button>
          </div>
        </div>

        <div class="nrd-set-row">
          <span>字体</span>
          <div class="nrd-seg">
            <button
              v-for="f in FONTS"
              :key="f.key"
              type="button"
              :class="{ on: font === f.key }"
              :style="{ fontFamily: f.stack }"
              @click="setFont(f.key)"
            >{{ f.label }}</button>
          </div>
        </div>

        <div class="nrd-set-row">
          <span>字号</span>
          <div class="nrd-slider">
            <button class="nrd-step" type="button" @click="bump('size', -1)">A-</button>
            <input v-model.number="size" type="range" min="14" max="30" step="1" @input="applyAll" />
            <button class="nrd-step" type="button" @click="bump('size', 1)">A+</button>
            <em>{{ size }}px</em>
          </div>
        </div>

        <div class="nrd-set-row">
          <span>行距</span>
          <div class="nrd-slider">
            <input v-model.number="lineHeight" type="range" min="1.4" max="2.4" step="0.1" @input="applyAll" />
            <em>{{ lineHeight.toFixed(1) }}</em>
          </div>
        </div>

        <div class="nrd-set-row">
          <span>边距</span>
          <div class="nrd-slider">
            <input v-model.number="padding" type="range" min="8" max="64" step="2" @input="applyAll" />
            <em>{{ padding }}px</em>
          </div>
        </div>

        <div class="nrd-set-row">
          <span>翻页</span>
          <div class="nrd-seg">
            <button type="button" :class="{ on: flow === 'paginated' }" @click="setFlow('paginated')">左右翻页</button>
            <button type="button" :class="{ on: flow === 'scroll' }" @click="setFlow('scroll')">上下滚动</button>
          </div>
        </div>

        <div class="nrd-set-foot">
          <button class="nrd-btn" type="button" @click="resetAll">恢复默认</button>
          <button class="nrd-btn primary" type="button" @click="setOpen = false">完成</button>
        </div>
      </div>
    </transition>

    <!-- 点击左右边缘翻页（分页模式） -->
    <template v-if="!loading && !error && flow === 'paginated'">
      <button class="nrd-edge left" type="button" aria-label="上一页" @click="goPrev" />
      <button class="nrd-edge right" type="button" aria-label="下一页" @click="goNext" />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import ePub from 'epubjs'

const props = defineProps({
  novel: { type: Object, required: true },
})
const emit = defineEmits(['close'])

/* ---------------- 设置（全部持久化） ---------------- */
const THEMES = [
  { key: 'day', label: '白天', bg: '#fbfaf7', text: '#2b2b2b', sub: '#8a8a8a', line: 'rgba(0,0,0,.1)' },
  { key: 'eye', label: '护眼', bg: '#e8e0c8', text: '#3a3428', sub: '#7d7458', line: 'rgba(90,75,40,.16)' },
  { key: 'night', label: '夜间', bg: '#16181c', text: '#cfd4da', sub: '#7c848e', line: 'rgba(255,255,255,.1)' },
]
const FONTS = [
  { key: 'song', label: '宋体', stack: '"Songti SC", "SimSun", "Noto Serif SC", serif' },
  { key: 'hei', label: '黑体', stack: '"PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif' },
  { key: 'kai', label: '楷体', stack: '"Kaiti SC", "KaiTi", "STKaiti", serif' },
]

const SET_KEY = 'xuanhuang:reader:settings'
const defaultSettings = { theme: 'day', font: 'song', size: 19, lineHeight: 1.9, padding: 28, flow: 'paginated' }
const settings = ref({ ...defaultSettings })
const theme = computed(() => settings.value.theme)
const font = computed(() => settings.value.font)
const size = computed({ get: () => settings.value.size, set: (v) => (settings.value.size = v) })
const lineHeight = computed({ get: () => settings.value.lineHeight, set: (v) => (settings.value.lineHeight = v) })
const padding = computed({ get: () => settings.value.padding, set: (v) => (settings.value.padding = v) })
const flow = computed({ get: () => settings.value.flow, set: (v) => (settings.value.flow = v) })

const curTheme = computed(() => THEMES.find((t) => t.key === theme.value) || THEMES[0])
const curFont = computed(() => FONTS.find((f) => f.key === font.value) || FONTS[0])

const cssVars = computed(() => ({
  '--nrd-bg': curTheme.value.bg,
  '--nrd-text': curTheme.value.text,
  '--nrd-sub': curTheme.value.sub,
  '--nrd-line': curTheme.value.line,
  '--nrd-size': size.value + 'px',
  '--nrd-lh': String(lineHeight.value),
  '--nrd-pad': padding.value + 'px',
  '--nrd-font': curFont.value.stack,
}))

function loadSettings() {
  try {
    const raw = localStorage.getItem(SET_KEY)
    if (raw) settings.value = { ...defaultSettings, ...JSON.parse(raw) }
  } catch { /* 忽略 */ }
}
function saveSettings() {
  try { localStorage.setItem(SET_KEY, JSON.stringify(settings.value)) } catch { /* 忽略 */ }
}
function setTheme(k) { settings.value.theme = k; saveSettings(); applyAll() }
function setFont(k) { settings.value.font = k; saveSettings(); applyAll() }
function setFlow(v) {
  if (settings.value.flow === v) return
  settings.value.flow = v
  saveSettings()
  if (kind.value === 'epub') { rebuildEpub(); return }
  if (kind.value === 'txt') {
    // 分页 ↔ 滚动：分页要重新量页宽；滚动要确保当前章已加载
    nextTick(() => {
      if (v === 'paginated') { txtPage.value = 0; measurePages() }
      else { loadUntil(txtIndex.value); syncTxtPercent() }
    })
  }
}
function bump(key, d) {
  settings.value[key] = Math.max(14, Math.min(30, settings.value[key] + d * 1))
  saveSettings(); applyAll()
}
function resetAll() {
  settings.value = { ...defaultSettings }
  saveSettings(); applyAll()
  if (kind.value === 'epub') rebuildEpub()
}

/* ---------------- 状态 ---------------- */
const loading = ref(true)
const error = ref('')
const kind = ref('')          // epub | txt
const percent = ref(0)
const toc = ref([])
const tocActive = ref(0)
const tocOpen = ref(false)
const setOpen = ref(false)
const atStart = ref(true)

const epubRef = ref(null)
const txtRef = ref(null)
let book = null
let rendition = null

/* TXT */
const txtChapters = ref([])   // [{ title, paras: [] }]
const txtIndex = ref(0)
const txtChapter = computed(() => txtChapters.value[txtIndex.value] || null)
const txtParas = computed(() => (txtChapter.value ? txtChapter.value.paras : []))

/* v2.46.201：分页模式改用「CSS 多列」做真实分页（一页正好填满屏幕），
   翻页 = 整块 translateX；滚动模式按章懒加载，不再一次渲染全书。 */
const txtPage = ref(0)        // 分页模式：章内第几页
const txtPageCount = ref(1)   // 分页模式：本章总页数
const pageWidth = ref(0)      // 一页可用宽度（容器宽 - 左右边距）
const loadedSecs = ref([])    // 滚动模式：已加载的章节段
const colsRef = ref(null)
const PAGE_GAP = 40

const colsStyle = computed(() => {
  if (flow.value !== 'paginated') return {}
  return {
    columnWidth: `${pageWidth.value}px`,
    columnGap: `${PAGE_GAP}px`,
    columnFill: 'auto',
    transform: `translateX(-${txtPage.value * (pageWidth.value + PAGE_GAP)}px)`,
  }
})

/** 量页宽 + 本章页数 */
function measurePages() {
  if (flow.value !== 'paginated' || kind.value !== 'txt') return
  const el = txtRef.value
  if (!el) return
  pageWidth.value = Math.max(120, el.clientWidth - padding.value * 2)
  requestAnimationFrame(() => {
    const cols = colsRef.value
    if (!cols) return
    const per = pageWidth.value + PAGE_GAP
    txtPageCount.value = Math.max(1, Math.round((cols.scrollWidth + PAGE_GAP) / per))
    if (txtPage.value > txtPageCount.value - 1) txtPage.value = txtPageCount.value - 1
  })
}

/** 滚动模式：按需把 0..idx 的章节塞进 DOM */
function loadUntil(idx) {
  const target = Math.min(idx, txtChapters.value.length - 1)
  for (let k = loadedSecs.value.length; k <= target; k++) {
    const c = txtChapters.value[k]
    if (!c) break
    loadedSecs.value.push({ idx: k, title: c.title, paras: c.paras })
  }
}

/** 进度 = (章序号 + 章内页比) / 总章数 */
function syncTxtPercent() {
  const n = Math.max(1, txtChapters.value.length)
  const inChap = txtPageCount.value > 1 ? txtPage.value / txtPageCount.value : 0
  percent.value = Math.min(100, Math.round(((txtIndex.value + inChap) / n) * 100))
  saveProgress({ chapter: txtIndex.value, page: txtPage.value, percent: percent.value / 100 })
}

const PROG_KEY = computed(() => `xuanhuang:reader:prog:${props.novel.id}`)

/* ---------------- 读取文件 ---------------- */
/**
 * 取原始文件字节。
 * 🔴 不能用项目封装的 api：它的响应拦截器会判断 response.data.code，
 * 而二进制响应没有 code 字段 → 直接 reject 一个 ArrayBuffer（不是 Error，message 为空），
 * 表现为阅读器只显示「解析失败」、什么都看不到。
 * 这里走原生 fetch 绕开拦截器。
 */
async function fetchBuffer() {
  const tk = localStorage.getItem('token') || ''
  const res = await fetch(`/api/novels/${props.novel.id}/file`, {
    headers: { Authorization: `Bearer ${tk}` },
  })
  if (!res.ok) throw new Error(`文件读取失败（HTTP ${res.status}）`)
  return await res.arrayBuffer()
}

function pickKind(name) {
  const n = String(name || props.novel.original_filename || '').toLowerCase()
  if (n.endsWith('.epub')) return 'epub'
  if (n.endsWith('.txt')) return 'txt'
  return ''
}

/** TXT 解码：BOM → 严格 UTF-8 → GBK 兜底 */
function decodeText(buf) {
  const u8 = new Uint8Array(buf)
  if (u8[0] === 0xef && u8[1] === 0xbb && u8[2] === 0xbf) {
    return new TextDecoder('utf-8').decode(u8.subarray(3))
  }
  if (u8[0] === 0xff && u8[1] === 0xfe) return new TextDecoder('utf-16le').decode(u8.subarray(2))
  if (u8[0] === 0xfe && u8[1] === 0xff) return new TextDecoder('utf-16be').decode(u8.subarray(2))
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(u8)
  } catch {
    try { return new TextDecoder('gbk').decode(u8) } catch { return new TextDecoder('utf-8').decode(u8) }
  }
}

/** TXT 分章：匹配「第x章/回/节/卷」「卷x」「序章/楔子/番外」 */
const CHAPTER_RE = /^[\s\u3000]*(第\s*[0-9零一二三四五六七八九十百千万两]+\s*[章回节卷篇]|卷\s*[0-9零一二三四五六七八九十百千万两]+|序章|楔子|引子|尾声|后记|番外)[^\n]{0,40}$/

function splitChapters(text) {
  const lines = text.replace(/\r\n?/g, '\n').split('\n')
  const chapters = []
  let cur = { title: '开始', paras: [] }
  let buf = []

  const flushPara = () => {
    const t = buf.join('').trim()
    if (t) cur.paras.push(t)
    buf = []
  }

  for (const raw of lines) {
    const line = raw.replace(/\u00a0/g, ' ').trim()
    if (!line) { flushPara(); continue }
    if (CHAPTER_RE.test(line) && line.length <= 42) {
      flushPara()
      if (cur.paras.length || cur.title !== '开始') chapters.push(cur)
      cur = { title: line, paras: [] }
      continue
    }
    buf.push(line)
  }
  flushPara()
  if (cur.paras.length || cur.title !== '开始') chapters.push(cur)

  if (!chapters.length) chapters.push({ title: props.novel.title || '正文', paras: [text.trim()] })
  return chapters
}

/* ---------------- EPUB ---------------- */
async function openEpub(buffer) {
  book = ePub(buffer)
  await book.ready
  await renderEpub()

  // 目录
  const nav = await book.loaded.navigation.catch(() => null)
  toc.value = (nav?.toc || []).map((it) => ({ label: it.label.trim(), href: it.href }))

  // 进度恢复
  let saved = null
  try { saved = JSON.parse(localStorage.getItem(PROG_KEY.value) || 'null') } catch { /* 忽略 */ }
  if (saved?.cfi) {
    await rendition.display(saved.cfi).catch(() => rendition.display())
    percent.value = Math.round((saved.percent || 0) * 100)
  } else {
    await rendition.display()
  }

  rendition.on('relocated', (loc) => {
    const p = loc?.start?.percentage
    if (typeof p === 'number') percent.value = Math.round(p * 100)
    saveProgress({ cfi: loc?.start?.cfi || '', percent: p || 0 })
    syncTocActive(loc?.start?.href || '')
    atStart.value = !!loc?.atStart
  })
  rendition.on('keyup', onKey)
}

async function renderEpub() {
  rendition = book.renderTo(epubRef.value, {
    width: '100%',
    height: '100%',
    flow: flow.value === 'scroll' ? 'scrolled' : 'paginated',
    spread: 'none',
    allowScriptedContent: false,
  })
  applyEpubTheme()
  await rendition.display()
}

async function rebuildEpub() {
  if (!book || !rendition) return
  const loc = rendition.currentLocation()
  const cfi = loc?.start?.cfi
  try { rendition.destroy() } catch { /* 忽略 */ }
  await renderEpub()
  if (cfi) await rendition.display(cfi).catch(() => {})
}

/**
 * 把主题/字体/字号/行距/边距注入 EPUB 的 iframe。
 * 🔴 不能用 themes.register + select：每次 select 会重建 stylesheet，
 * 实测切主题后 iframe 里的正文直接消失（只剩空白）。
 * themes.override 是逐条设置属性，不重建样式表，切主题即时生效且内容不丢。
 */
function applyEpubTheme() {
  if (!rendition) return
  const t = curTheme.value
  const f = curFont.value
  const ov = (k, v) => { try { rendition.themes.override(k, v, true) } catch { /* 忽略 */ } }

  ov('color', t.text)
  ov('background', 'transparent')
  ov('font-family', f.stack)
  ov('line-height', String(lineHeight.value))
  ov('text-align', 'justify')
  ov('padding', `${padding.value}px`)
  ov('box-sizing', 'border-box')
  try { rendition.themes.fontSize(`${size.value}px`) } catch { /* 忽略 */ }

  // 改了字号/行距后 epub.js 会重新分页，但不自动回到原位置 ——
  // 表现为「切完主题正文不见了」（其实停在了空白处）。这里重新定位一次。
  clearTimeout(relocateTimer)
  relocateTimer = setTimeout(() => {
    try {
      const cfi = rendition.currentLocation()?.start?.cfi
      if (cfi) rendition.display(cfi).catch(() => {})
    } catch { /* 忽略 */ }
  }, 140)
}
let relocateTimer = 0

/* ---------------- 进度 ---------------- */
function saveProgress(obj) {
  try {
    localStorage.setItem(PROG_KEY.value, JSON.stringify({ ...obj, at: Date.now() }))
  } catch { /* 忽略 */ }
}

function syncTocActive(href) {
  if (!href) return
  const clean = href.split('#')[0]
  const i = toc.value.findIndex((t) => (t.href || '').split('#')[0] === clean)
  if (i >= 0) tocActive.value = i
}

/* ---------------- 翻页 ---------------- */
function goPrev() {
  if (kind.value === 'epub') { rendition?.prev(); return }
  txtPrev()
}
function goNext() {
  if (kind.value === 'epub') { rendition?.next(); return }
  txtNext()
}

function onKey(e) {
  if (e.key === 'ArrowLeft') goPrev()
  else if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault?.(); goNext() }
  else if (e.key === 'Escape') emit('close')
}

/* ---------------- TXT 逻辑 ---------------- */
function txtPrev() {
  if (kind.value === 'epub') { rendition?.prev(); return }
  if (flow.value === 'paginated') {
    if (txtPage.value > 0) { txtPage.value -= 1; syncTxtPercent(); return }
    if (txtIndex.value > 0) { goChapter(txtIndex.value - 1, true); return }
    return
  }
  txtRef.value?.scrollBy({ top: -txtRef.value.clientHeight * 0.9, behavior: 'smooth' })
}

function txtNext() {
  if (kind.value === 'epub') { rendition?.next(); return }
  if (flow.value === 'paginated') {
    if (txtPage.value < txtPageCount.value - 1) { txtPage.value += 1; syncTxtPercent(); return }
    if (txtIndex.value < txtChapters.value.length - 1) { goChapter(txtIndex.value + 1); return }
    return
  }
  const el = txtRef.value
  if (!el) return
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 60 && loadedSecs.value.length < txtChapters.value.length) {
    loadUntil(loadedSecs.value.length)
    nextTick(() => el.scrollBy({ top: el.clientHeight * 0.9, behavior: 'smooth' }))
    return
  }
  el.scrollBy({ top: el.clientHeight * 0.9, behavior: 'smooth' })
}

/** 切章（分页模式重置到第一页；toLast=true 时落到最后一页） */
function goChapter(i, toLast = false) {
  if (i < 0 || i >= txtChapters.value.length) return
  txtIndex.value = i
  tocActive.value = i
  if (flow.value === 'paginated') {
    txtPage.value = 0
    nextTick(() => {
      measurePages()
      if (toLast) {
        requestAnimationFrame(() => {
          txtPage.value = Math.max(0, txtPageCount.value - 1)
          syncTxtPercent()
        })
      } else syncTxtPercent()
    })
  } else {
    loadUntil(i)
    nextTick(() => {
      const el = txtRef.value
      const sec = el?.querySelectorAll('.nrd-sec')?.[i]
      if (sec && el) el.scrollTop = sec.offsetTop
      syncTxtPercent()
    })
  }
}

function switchChapter(i) {
  return goChapter(i, false)
}

let scrollTimer = 0
function onTxtScroll() {
  const el = txtRef.value
  if (!el) return

  if (flow.value === 'scroll') {
    // 接近底部：追加下一章（按章懒加载）
    if (loadedSecs.value.length < txtChapters.value.length &&
        el.scrollTop + el.clientHeight > el.scrollHeight - 800) {
      loadUntil(loadedSecs.value.length)
    }
    // 反推当前章节
    const secs = el.querySelectorAll('.nrd-sec')
    let cur = 0
    secs.forEach((sd, k) => { if (sd.offsetTop <= el.scrollTop + 8) cur = k })
    if (cur !== txtIndex.value) { txtIndex.value = cur; tocActive.value = cur }
  }

  clearTimeout(scrollTimer)
  scrollTimer = setTimeout(() => {
    saveProgress({ chapter: txtIndex.value, page: txtPage.value, scrollTop: el.scrollTop, percent: percent.value / 100 })
  }, 400)
}

/* ---------------- 目录跳转 ---------------- */
function jumpTo(i) {
  tocOpen.value = false
  if (kind.value === 'epub') {
    const it = toc.value[i]
    if (!it) return
    tocActive.value = i
    rendition?.display(it.href)
    return
  }
  switchChapter(i)
}

/* ---------------- 统一应用设置 ---------------- */
function applyAll() {
  saveSettings()
  if (kind.value === 'epub') applyEpubTheme()
}

/* ---------------- 初始化 ---------------- */
onMounted(async () => {
  loadSettings()
  window.addEventListener('keydown', onKey)
  window.addEventListener('resize', onResize)
  try {
    kind.value = pickKind()
    if (!kind.value) throw new Error('只支持 EPUB 和 TXT 格式')
    const buf = await fetchBuffer()
    if (kind.value === 'epub') {
      await openEpub(buf)
    } else {
      const text = decodeText(buf)
      txtChapters.value = splitChapters(text)
      toc.value = txtChapters.value.map((c) => ({ label: c.title }))
      let saved = null
      try { saved = JSON.parse(localStorage.getItem(PROG_KEY.value) || 'null') } catch { /* 忽略 */ }
      const ci = saved && Number.isInteger(saved.chapter) ? saved.chapter : 0
      txtIndex.value = Math.min(Math.max(0, ci), txtChapters.value.length - 1)
      percent.value = Math.round(((txtIndex.value + 1) / txtChapters.value.length) * 100)
      await nextTick()
      if (flow.value === 'paginated') {
        measurePages()
        // 恢复章内页码（等测量完再设，否则会被 clamp 回 0）
        if (saved && Number.isInteger(saved.page) && saved.page > 0) {
          requestAnimationFrame(() => {
            txtPage.value = Math.min(saved.page, Math.max(0, txtPageCount.value - 1))
            syncTxtPercent()
          })
        }
      } else {
        loadUntil(txtIndex.value)
        await nextTick()
        if (saved?.scrollTop && txtRef.value) txtRef.value.scrollTop = saved.scrollTop
      }
    }
  } catch (e) {
    error.value = e?.response?.data?.msg || e?.message || '解析失败'
  } finally {
    loading.value = false
    // 双保险：容器尺寸在 loading 前后可能变化，让 epub.js 重算一次
    if (kind.value === 'epub') {
      await nextTick()
      setTimeout(() => { try { rendition?.resize() } catch { /* 忽略 */ } }, 60)
    }
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('resize', onResize)
  clearTimeout(scrollTimer)
  try { rendition?.destroy() } catch { /* 忽略 */ }
  try { book?.destroy() } catch { /* 忽略 */ }
})

watch(atStart, (v) => { atStart.value = v })

/* 窗口尺寸 / 边距 / 字号变化 → 分页模式要重新切页 */
let resizeTimer = 0
function onResize() {
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => { measurePages() }, 180)
}
watch([size, lineHeight, padding], () => { onResize() })
</script>

<style scoped>
.nrd {
  position: fixed;
  inset: 0;
  z-index: 1600;
  display: flex;
  flex-direction: column;
  background: var(--nrd-bg);
  color: var(--nrd-text);
  font-family: var(--nrd-font);
}

/* 顶栏 */
.nrd-bar {
  flex-shrink: 0;
  height: 50px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  border-bottom: 1px solid var(--nrd-line);
}
.nrd-ic {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--nrd-text);
  font-size: 15px;
  cursor: pointer;
}
.nrd-ic:hover { background: rgba(127, 127, 127, .14); }
.nrd-title {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.nrd-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-family: inherit;
}
.nrd-pct { flex-shrink: 0; font-size: 12px; color: var(--nrd-sub); }

/* 内容舞台 */
.nrd-stage { flex: 1; min-height: 0; position: relative; overflow: hidden; }
.nrd-txt { overflow-y: auto; overflow-x: hidden; }
.nrd-txt-cols {
  font-size: var(--nrd-size);
  line-height: var(--nrd-lh);
  padding: var(--nrd-pad);
  box-sizing: border-box;
}
/* 分页模式：多列横向排布，一列 = 一页，超出部分隐藏，翻页靠 translateX */
.nrd-txt.is-paged {
  overflow: hidden;
}
.nrd-txt.is-paged .nrd-txt-cols {
  height: 100%;
  will-change: transform;
  transition: transform .28s cubic-bezier(.22, .61, .36, 1);
}
.nrd-txt.is-paged .nrd-ch-title {
  break-inside: avoid;
  column-span: none;
}
.nrd-txt.is-paged .nrd-p {
  break-inside: avoid;
}
/* 滚动模式：普通块流 */
.nrd-sec + .nrd-sec {
  margin-top: 1.6em;
}
.nrd-ch-title {
  margin: 0 0 1.2em;
  font-size: 1.25em;
  font-weight: 500;
  text-align: center;
  letter-spacing: .04em;
}
.nrd-p {
  margin: 0 0 .85em;
  text-indent: 2em;
  text-align: justify;
  word-break: break-word;
}
.nrd-end {
  margin: 2.4em 0 1em;
  text-align: center;
  font-size: .85em;
  color: var(--nrd-sub);
}

/* 底栏 */
.nrd-foot {
  flex-shrink: 0;
  height: 46px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  border-top: 1px solid var(--nrd-line);
}
.nrd-nav {
  padding: 6px 14px;
  border-radius: 8px;
  border: 1px solid var(--nrd-line);
  background: transparent;
  color: var(--nrd-text);
  font-size: 13px;
  cursor: pointer;
}
.nrd-nav:disabled { opacity: .4; cursor: default; }
.nrd-prog {
  flex: 1;
  height: 3px;
  border-radius: 2px;
  background: var(--nrd-line);
  overflow: hidden;
}
.nrd-prog i {
  display: block;
  height: 100%;
  background: currentColor;
  opacity: .45;
  transition: width .25s;
}

/* 翻页热区 */
.nrd-edge {
  position: absolute;
  top: 50px;
  bottom: 46px;
  width: 12%;
  border: 0;
  background: transparent;
  cursor: pointer;
}
.nrd-edge.left { left: 0; }
.nrd-edge.right { right: 0; }

/* 遮罩 */
.nrd-mask {
  position: absolute;
  inset: 50px 0 46px;
  display: grid;
  place-items: center;
  background: var(--nrd-bg);
  z-index: 2;
}
.nrd-loading { font-size: 13px; color: var(--nrd-sub); }
.nrd-err { text-align: center; max-width: 380px; padding: 0 20px; }
.nrd-err p { font-size: 13.5px; line-height: 1.7; }
.nrd-btn {
  margin-top: 12px;
  padding: 8px 18px;
  border-radius: 9px;
  border: 1px solid var(--nrd-line);
  background: transparent;
  color: var(--nrd-text);
  font-size: 13px;
  cursor: pointer;
}
.nrd-btn.primary {
  background: var(--nrd-text);
  color: var(--nrd-bg);
  border-color: transparent;
}

/* 目录 */
.nrd-toc {
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 300px;
  max-width: 82vw;
  display: flex;
  flex-direction: column;
  background: var(--nrd-bg);
  border-right: 1px solid var(--nrd-line);
  z-index: 5;
}
.nrd-toc-head {
  flex-shrink: 0;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px 0 18px;
  font-size: 14px;
  border-bottom: 1px solid var(--nrd-line);
}
.nrd-toc-list { flex: 1; overflow-y: auto; padding: 8px 0 20px; }
.nrd-toc-item {
  display: block;
  width: 100%;
  padding: 9px 18px;
  border: 0;
  background: transparent;
  color: var(--nrd-text);
  font-size: 13.5px;
  line-height: 1.5;
  text-align: left;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nrd-toc-item:hover { background: rgba(127, 127, 127, .12); }
.nrd-toc-item.active { font-weight: 500; background: rgba(127, 127, 127, .16); }
.nrd-toc-empty { padding: 20px 18px; font-size: 12.5px; color: var(--nrd-sub); }

/* 设置面板 */
.nrd-set {
  position: absolute;
  right: 12px;
  top: 56px;
  width: 330px;
  max-width: calc(100vw - 24px);
  padding: 16px;
  border-radius: 14px;
  background: var(--nrd-bg);
  border: 1px solid var(--nrd-line);
  box-shadow: 0 18px 40px -20px rgba(0, 0, 0, .4);
  z-index: 6;
}
.nrd-set-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.nrd-set-row > span {
  flex-shrink: 0;
  width: 36px;
  font-size: 12.5px;
  color: var(--nrd-sub);
}
.nrd-seg {
  flex: 1;
  display: flex;
  gap: 6px;
}
.nrd-seg button {
  flex: 1;
  padding: 7px 4px;
  border-radius: 8px;
  border: 1px solid var(--nrd-line);
  background: transparent;
  color: var(--nrd-text);
  font-size: 12.5px;
  cursor: pointer;
}
.nrd-seg button.on {
  background: var(--nrd-text);
  color: var(--nrd-bg);
  border-color: transparent;
}
.nrd-slider {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}
.nrd-slider input[type='range'] { flex: 1; accent-color: currentColor; }
.nrd-slider em {
  flex-shrink: 0;
  width: 42px;
  font-size: 12px;
  font-style: normal;
  color: var(--nrd-sub);
  text-align: right;
}
.nrd-step {
  flex-shrink: 0;
  padding: 4px 8px;
  border-radius: 7px;
  border: 1px solid var(--nrd-line);
  background: transparent;
  color: var(--nrd-text);
  font-size: 12px;
  cursor: pointer;
}
.nrd-set-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}

.nrd-fade-enter-active, .nrd-fade-leave-active { transition: opacity .16s ease; }
.nrd-fade-enter-from, .nrd-fade-leave-to { opacity: 0; }

/* 主题过渡 */
.nrd, .nrd-toc, .nrd-set { transition: background .22s ease, color .22s ease; }
</style>
