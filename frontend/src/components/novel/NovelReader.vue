<template>
  <!-- 小说阅读器（v2.46.196）
       集成在小说模块内部，直接读 novels 表的原始文件，不依赖外部应用。
       EPUB 走 epub.js，TXT 前端分章后自己渲染。
       全屏覆盖层（z-index 1600，与项目全屏约定一致）。 -->
  <!-- 🔴 必须 Teleport 到 body：NovelView 的祖先链里有 transform，
       position:fixed 会相对那个祖先定位而不是视口，实测阅读器只占了右侧内容区、
       左边被侧边栏压住一半。挂到 body 才是真正的全屏。 -->
  <Teleport to="body">
  <div class="nrd" :class="`theme-${theme}`" :style="cssVars">
    <!-- 顶栏 -->
    <header class="nrd-bar">
      <button class="nrd-ic" type="button" title="返回" @click="$emit('close')">←</button>
      <div class="nrd-title">
        <span class="nrd-name">{{ novel.title }}</span>
        <span class="nrd-pct">{{ percent }}%</span>
      </div>
      <button v-if="kind !== 'pdf'" class="nrd-ic" type="button" title="目录" @click="togglePanel('toc')">☰</button>
      <button v-if="kind !== 'pdf'" class="nrd-ic" type="button" title="搜索" @click="togglePanel('find')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.7" stroke-linecap="round" aria-hidden="true">
          <circle cx="10.5" cy="10.5" r="6.2" />
          <path d="M15.2 15.2 20 20" />
        </svg>
      </button>
      <button v-if="kind !== 'pdf'" class="nrd-ic" type="button" title="书签" @click="togglePanel('marks')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.6" stroke-linejoin="round" aria-hidden="true">
          <path d="M7 4.5h10v15l-5-3.4-5 3.4v-15Z" />
        </svg>
      </button>
      <button
        v-if="kind !== 'pdf'"
        class="nrd-ic"
        :class="{ on: speaking }"
        type="button"
        :title="speaking ? '停止朗读' : '朗读'"
        @click="toggleSpeak"
      >
        <svg v-if="speaking" width="15" height="15" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <rect x="6.5" y="5" width="4" height="14" rx="1" />
          <rect x="13.5" y="5" width="4" height="14" rx="1" />
        </svg>
        <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.6" stroke-linejoin="round" aria-hidden="true">
          <path d="M8.5 5.5 18 12l-9.5 6.5v-13Z" />
        </svg>
      </button>
      <button v-if="kind !== 'pdf'" class="nrd-ic" type="button" title="设置" @click="togglePanel('set')">Aa</button>
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

    <!-- PDF（v2.46.215）：用浏览器原生查看器，不改主题不重排 ——
         自带渲染层（pdf.js）在手机上体验也未必更好，且要额外维护 worker。
         手机浏览器大多不内嵌 PDF，检测到时给下载入口。 -->
    <div v-if="kind === 'pdf'" class="nrd-stage nrd-pdf">
      <iframe v-if="!pdfBlocked && pdfUrl" :src="pdfUrl" class="nrd-pdf-frame" title="PDF" />
      <div v-else class="nrd-pdf-fallback">
        <p>{{ pdfBlocked ? '当前浏览器不支持内嵌 PDF' : 'PDF 加载中…' }}</p>
        <a v-if="pdfUrl" class="nrd-btn primary" :href="pdfUrl" :download="novel.title + '.pdf'">下载后用其他应用打开</a>
      </div>
    </div>

    <!-- TXT 容器（v2.46.201）
         分页模式：CSS 多列，一列 = 一页，翻页整体 translateX，一页正好填满屏幕；
         滚动模式：连续上下滑，滚到接近底部按章懒加载下一章。 -->
    <div
      v-show="!error && kind === 'txt'"
      ref="txtRef"
      class="nrd-stage nrd-txt"
      :class="{ 'is-paged': flow === 'paginated' }"
      @scroll.passive="onTxtScroll"
      @touchstart.passive="onTouchStart"
      @touchend.passive="onTouchEnd"
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
    <footer v-if="kind !== 'pdf'" class="nrd-foot">
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

    <!-- 全文搜索抽屉（v2.46.215） -->
    <transition name="nrd-fade">
      <aside v-if="findOpen" class="nrd-toc nrd-find">
        <div class="nrd-toc-head">
          <span>搜索</span>
          <button class="nrd-ic" type="button" @click="findOpen = false">×</button>
        </div>
        <div class="nrd-find-box">
          <input
            v-model="findQ"
            class="nrd-find-input"
            type="search"
            placeholder="输入关键词"
            @keyup.enter="runFind"
          />
          <button class="nrd-btn primary" type="button" @click="runFind">搜索</button>
        </div>
        <p class="nrd-find-tip">{{ findTip }}</p>
        <div class="nrd-toc-list">
          <button
            v-for="(r, i) in findResults"
            :key="i"
            class="nrd-find-item"
            type="button"
            @click="jumpToResult(r)"
          >
            <span class="nrd-find-ch">{{ r.chapter }}</span>
            <span class="nrd-find-snip">{{ r.snippet }}</span>
          </button>
          <p v-if="findQ && !findResults.length && findTip" class="nrd-toc-empty">没有找到「{{ findQ }}」</p>
        </div>
      </aside>
    </transition>

    <!-- 书签 / 笔记抽屉 -->
    <transition name="nrd-fade">
      <aside v-if="marksOpen" class="nrd-toc nrd-marks">
        <div class="nrd-toc-head">
          <span>书签与笔记</span>
          <button class="nrd-ic" type="button" @click="marksOpen = false">×</button>
        </div>
        <div class="nrd-mark-add">
          <button class="nrd-btn primary" type="button" @click="addMark('bookmark')">当前位置加书签</button>
          <button class="nrd-btn" type="button" @click="addMark('note')">写笔记</button>
        </div>
        <div class="nrd-toc-list">
          <div v-for="m in marks" :key="m.id" class="nrd-mark">
            <button class="nrd-mark-main" type="button" @click="jumpToMark(m)">
              <span class="nrd-mark-kind">{{ MARK_LABEL[m.kind] || '书签' }}</span>
              <span class="nrd-mark-text">{{ m.note || m.quote || m.chapter || '（无内容）' }}</span>
              <span class="nrd-mark-pct">{{ Math.round((m.percent || 0) * 100) }}%</span>
            </button>
            <button class="nrd-mark-del" type="button" title="删除" @click="removeMark(m)">×</button>
          </div>
          <p v-if="!marks.length" class="nrd-toc-empty">还没有书签。读到喜欢的地方点「当前位置加书签」。</p>
        </div>
      </aside>
    </transition>

    <!-- 设置面板 -->
    <transition name="nrd-fade">
      <div v-if="setOpen" class="nrd-set">
        <div class="nrd-set-row">
          <span>亮度</span>
          <div class="nrd-slider">
            <input v-model.number="brightness" type="range" min="35" max="100" step="1" @input="saveSettings" />
            <em>{{ brightness }}%</em>
          </div>
        </div>

        <div class="nrd-set-row">
          <span>&nbsp;</span>
          <div class="nrd-seg">
            <button type="button" :class="{ on: followSys }" @click="toggleFollowSys">跟随系统日/夜</button>
          </div>
        </div>

        <div class="nrd-set-row">
          <span>背景</span>
          <div class="nrd-dots">
            <button
              v-for="t in THEMES"
              :key="t.key"
              type="button"
              class="nrd-dot"
              :class="{ on: theme === t.key }"
              :style="{ background: t.bg }"
              :title="t.label"
              @click="setTheme(t.key)"
            />
          </div>
        </div>

        <div class="nrd-set-row">
          <span>字体</span>
          <div class="nrd-seg nrd-seg-fonts">
            <button
              v-for="f in FONTS"
              :key="f.key"
              type="button"
              :class="{ on: font === f.key, loading: fontLoading === f.key }"
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
            <button type="button" :class="{ on: flow === 'paginated' && !autoPlay }" @click="setFlow('paginated')">左右</button>
            <button type="button" :class="{ on: flow === 'scroll' }" @click="setFlow('scroll')">上下</button>
            <button type="button" :class="{ on: autoPlay }" @click="setFlow('auto')">自动</button>
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

    <!-- 亮度遮罩（纯压暗，不挡交互；brightness < 100 时出现） -->
    <div
      v-if="brightness < 100"
      class="nrd-dim"
      :style="{ opacity: (100 - brightness) / 100 * 0.78 }"
      aria-hidden="true"
    />
  </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import ePub from 'epubjs'
import { useFullscreenPage } from '@/composables/useFullscreenPage'

const props = defineProps({
  novel: { type: Object, required: true },
})
const emit = defineEmits(['close'])

/* ---------------- 设置（全部持久化） ---------------- */
const THEMES = [
  { key: 'day', label: '白天', bg: '#fbfaf7', text: '#2b2b2b', sub: '#8a8a8a', line: 'rgba(0,0,0,.1)' },
  { key: 'eye', label: '护眼', bg: '#f3ecd2', text: '#3a3428', sub: '#7d7458', line: 'rgba(90,75,40,.16)' },
  { key: 'blue', label: '蓝', bg: '#e8eff5', text: '#2c3540', sub: '#75828e', line: 'rgba(40,70,100,.14)' },
  { key: 'green', label: '绿', bg: '#e6efdf', text: '#2e3a2c', sub: '#75816f', line: 'rgba(60,100,50,.14)' },
  { key: 'night', label: '夜间', bg: '#16181c', text: '#cfd4da', sub: '#7c848e', line: 'rgba(255,255,255,.1)' },
]
// v2.46.281：宋/黑/楷三档首选换成 GitHub 开源字体（服务器 /fonts/ 下，FontFace 按需加载），
// 系统栈保留做兜底 —— 鸿蒙等无宋/楷字库的设备不再整体退化成黑体。
const FONTS = [
  { key: 'song', label: '宋体', stack: '"Noto Serif CJK SC", "Songti SC", "SimSun", serif', webfont: 'Noto Serif CJK SC', file: '/fonts/NotoSerifSC-Regular.otf' },
  { key: 'hei', label: '黑体', stack: '"Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", sans-serif', webfont: 'Noto Sans CJK SC', file: '/fonts/NotoSansSC-Regular.otf' },
  { key: 'kai', label: '楷体', stack: '"LXGW WenKai", "Kaiti SC", "KaiTi", serif', webfont: 'LXGW WenKai', file: '/fonts/LXGWWenKai-Regular.ttf' },
  { key: 'fang', label: '仿宋', stack: '"Zhuque Fangsong", "FangSong", "STFangsong", serif', webfont: 'Zhuque Fangsong', file: '/fonts/ZhuqueFangsong-Regular.ttf' },
]

const SET_KEY = 'xuanhuang:reader:settings'
const defaultSettings = { theme: 'day', font: 'song', size: 19, lineHeight: 1.9, padding: 28, flow: 'paginated', brightness: 100, followSys: false }
const settings = ref({ ...defaultSettings })
const theme = computed(() => settings.value.theme)
const font = computed(() => settings.value.font)
const size = computed({ get: () => settings.value.size, set: (v) => (settings.value.size = v) })
const lineHeight = computed({ get: () => settings.value.lineHeight, set: (v) => (settings.value.lineHeight = v) })
const padding = computed({ get: () => settings.value.padding, set: (v) => (settings.value.padding = v) })
const flow = computed({ get: () => settings.value.flow, set: (v) => (settings.value.flow = v) })
const brightness = computed({ get: () => settings.value.brightness ?? 100, set: (v) => (settings.value.brightness = v) })
const followSys = computed({ get: () => !!settings.value.followSys, set: (v) => (settings.value.followSys = v) })
const autoPlay = ref(false)   // 自动翻页：运行态不进 localStorage，翻页档位「自动」= paginated + autoPlay
const fontLoading = ref('')   // 正在加载的 webfont key（按钮转圈提示）

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

function isTouchDevice() {
  return (navigator.maxTouchPoints || 0) > 0 || 'ontouchstart' in window
}

function loadSettings() {
  // 触摸设备首次阅读：边距收窄（28px 在 375 宽的屏上太占地方），字号略小
  const base = isTouchDevice()
    ? { ...defaultSettings, padding: 20, size: 18 }
    : defaultSettings
  try {
    const raw = localStorage.getItem(SET_KEY)
    settings.value = raw ? { ...base, ...JSON.parse(raw) } : { ...base }
  } catch { /* 忽略 */ }
}
function saveSettings() {
  try { localStorage.setItem(SET_KEY, JSON.stringify(settings.value)) } catch { /* 忽略 */ }
}
function setTheme(k) { settings.value.theme = k; saveSettings(); applyAll() }

/* ---- webfont 按需加载（v2.46.281）----
   字体文件 8~25MB，绝不能在 <head> 里无条件 @font-face（打开阅读器就白拉 70MB）。
   用 FontFace API 只加载「当前选中」的那一款，成功后加入 document.fonts。
   epub.js 的 iframe 里字体继承父页注册（同源 /fonts/），加载完成要重新 applyAll 注入。 */
const loadedFonts = new Set()
async function ensureFont(f) {
  if (!f.webfont || !f.file || loadedFonts.has(f.key)) return
  loadedFonts.add(f.key)
  fontLoading.value = f.key
  try {
    const face = new FontFace(f.webfont, `url(${f.file})`, { display: 'swap' })
    await face.load()
    document.fonts.add(face)
    applyAll()   // 字体真正可用后重注入（EPUB iframe / TXT 立即生效）
  } catch { /* 加载失败退回系统字体栈，不阻塞阅读 */ }
  if (fontLoading.value === f.key) fontLoading.value = ''
}
async function setFont(k) {
  settings.value.font = k
  saveSettings()
  applyAll()
  await ensureFont(FONTS.find((f) => f.key === k) || FONTS[0])
}

function toggleFollowSys() {
  followSys.value = !followSys.value
  saveSettings()
  if (followSys.value) applySysTheme()
}
let sysMq = null
function applySysTheme() {
  if (!followSys.value || !sysMq) return
  settings.value.theme = sysMq.matches ? 'night' : 'day'
  saveSettings(); applyAll()
}
function watchSysTheme() {
  if (!window.matchMedia) return
  sysMq = window.matchMedia('(prefers-color-scheme: dark)')
  const h = () => applySysTheme()
  if (sysMq.addEventListener) sysMq.addEventListener('change', h)
  else if (sysMq.addListener) sysMq.addListener(h)   // 旧 WebView
}

/* ---- 自动翻页：12 秒一页，任何触摸/翻页操作即停 ---- */
let autoTimer = null
function stopAutoPlay() {
  if (autoTimer) { clearInterval(autoTimer); autoTimer = null }
  autoPlay.value = false
}
function startAutoPlay() {
  stopAutoPlay()
  autoPlay.value = true
  autoTimer = setInterval(() => {
    if (document.hidden) return   // 后台标签页不空翻
    goNext()
  }, 12000)
}
function setFlow(v) {
  if (v === 'auto') {
    // 自动 = 分页模式 + 定时翻页；当前在滚动模式时先切回分页
    if (settings.value.flow !== 'paginated') {
      settings.value.flow = 'paginated'
      saveSettings()
      if (kind.value === 'epub') rebuildEpub()
      else if (kind.value === 'txt') nextTick(() => { txtPage.value = 0; measurePages() })
    }
    startAutoPlay()
    setOpen.value = false   // 挂机模式直接收起面板
    return
  }
  stopAutoPlay()
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
  stopAutoPlay()
  settings.value = { ...defaultSettings }
  saveSettings(); applyAll()
  ensureFont(curFont.value)
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
  saveProgress({ chapter: txtIndex.value, chapterTitle: txtChapter.value?.title || '',
                 page: txtPage.value, percent: percent.value / 100 })
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
  if (n.endsWith('.pdf')) return 'pdf'
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

/* ---------------- PDF（v2.46.215） ---------------- */
const pdfUrl = ref('')
const pdfBlocked = ref(false)

function openPdf(buf) {
  const blob = new Blob([buf], { type: 'application/pdf' })
  pdfUrl.value = URL.createObjectURL(blob)
  // 手机浏览器普遍不内嵌 PDF（会直接下载或白屏），给下载兜底
  const ua = navigator.userAgent || ''
  const mobile = /Android|iPhone|iPad|iPod|HarmonyOS|Mobile|MicroMessenger/i.test(ua)
  pdfBlocked.value = mobile
  percent.value = 0
}

/* ---------------- EPUB ---------------- */
async function openEpub(buffer) {
  book = ePub(buffer)
  await book.ready
  await renderEpub()

  // 目录
  const nav = await book.loaded.navigation.catch(() => null)
  toc.value = (nav?.toc || []).map((it) => ({ label: it.label.trim(), href: it.href }))

  // 进度恢复：服务器 > 本地（服务器是跨设备的权威来源）
  let saved = null
  try { saved = JSON.parse(localStorage.getItem(PROG_KEY.value) || 'null') } catch { /* 忽略 */ }
  const serverCfi = props.novel.progress_cfi || ''
  const startCfi = serverCfi || saved?.cfi || ''
  if (startCfi) {
    await rendition.display(startCfi).catch(() => rendition.display())
    const sp = Number(props.novel.progress_percent) || 0
    percent.value = Math.round((serverCfi ? sp : (saved?.percent || 0)) * 100)
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
  // 给每章 iframe 内部挂触摸手势（外部监听收不到 iframe 里的 touch）
  rendition.hooks.content.register((contents) => {
    const doc = contents && contents.document
    if (!doc) return
    doc.addEventListener('touchstart', onTouchStart, { passive: true })
    doc.addEventListener('touchend', onTouchEnd, { passive: true })
    // 分页模式下禁止 iframe 内横向滚动干扰
    try { doc.documentElement.style.touchAction = 'pan-y' } catch { /* 忽略 */ }
  })
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
  queueRemoteSave(obj)
}

/* ---------------- 进度云端同步（v2.46.212） ----------------
   之前只存 localStorage：换设备 / 清缓存就丢。现在防抖上报到服务器，
   打开时优先用服务器进度（本地只作兜底）。
   时长每 60 秒结算一次增量，避免每次翻页都写库。 */
let remoteTimer = 0
let pendingProgress = null
let sessionStart = Date.now()
let sentSeconds = 0

function queueRemoteSave(obj) {
  pendingProgress = obj
  clearTimeout(remoteTimer)
  remoteTimer = setTimeout(flushProgress, 1200)
}

function flushProgress() {
  if (!pendingProgress) return
  const obj = pendingProgress
  pendingProgress = null
  const tk = localStorage.getItem('token') || ''
  // 阅读时长：距上次上报超过 30 秒才算有效（防挂机刷时长）
  const now = Date.now()
  const elapsed = Math.round((now - sessionStart) / 1000)
  let seconds = 0
  if (elapsed - sentSeconds >= 30) {
    seconds = elapsed - sentSeconds
    sentSeconds = elapsed
  }
  fetch(`/api/novels/${props.novel.id}/progress`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${tk}` },
    body: JSON.stringify({
      cfi: obj.cfi || '',
      chapter: obj.chapterTitle || '',
      percent: obj.percent || 0,
      seconds,
    }),
    keepalive: true,
  }).catch(() => { /* 网络失败不影响本地阅读 */ })
}

function syncTocActive(href) {
  if (!href) return
  const clean = href.split('#')[0]
  const i = toc.value.findIndex((t) => (t.href || '').split('#')[0] === clean)
  if (i >= 0) tocActive.value = i
}

/* ---------------- 翻页 ---------------- */
/* ---------------- 移动端：触摸手势（v2.46.202） ----------------
   viewport 切换 / 外壳隐藏已统一到 composables/useFullscreenPage.js（v2.46.217），
   这里只保留触摸能力判断，供默认字号与手势逻辑使用。 */
const isTouch = ref(false)
function enterTouchMode() {
  isTouch.value = (navigator.maxTouchPoints || 0) > 0 || 'ontouchstart' in window
}

/* 触摸滑动翻页（分页模式）。滚动模式交给原生滚动，不拦截。 */
let tX = 0
let tY = 0
let tActive = false
function onTouchStart(e) {
  if (e.touches.length !== 1) return
  tX = e.touches[0].clientX
  tY = e.touches[0].clientY
  tActive = true
}
function onTouchEnd(e) {
  if (!tActive) return
  tActive = false
  const t = e.changedTouches && e.changedTouches[0]
  if (!t) return
  const dx = t.clientX - tX
  const dy = t.clientY - tY
  // 竖直方向占主导 → 用户想滚动，不翻页
  if (Math.abs(dy) > Math.abs(dx)) return
  if (Math.abs(dx) < 46) return
  if (dx < 0) goNext()
  else goPrev()
}

/* 自动翻页器自己调 goNext 时置位，避免用户 goNext 处理器把自动翻页杀掉 */
let autoStepping = false
function goPrev() {
  if (!autoStepping) stopAutoPlay()
  if (kind.value === 'epub') { rendition?.prev(); return }
  txtPrev()
}
function goNext() {
  if (!autoStepping) stopAutoPlay()
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

/* ---------------- 全文搜索（v2.46.215） ----------------
   TXT：直接在分章后的段落里找，返回章节 + 上下文片段；
   EPUB：正文在各章 iframe 里，逐章抽取文本成本高，先只搜目录标题。 */
const findOpen = ref(false)
const findQ = ref('')
const findResults = ref([])
const findTip = ref('')

function runFind() {
  const q = findQ.value.trim()
  findResults.value = []
  if (!q) { findTip.value = ''; return }

  if (kind.value === 'txt') {
    const out = []
    txtChapters.value.forEach((c, ci) => {
      c.paras.forEach((p) => {
        let idx = p.indexOf(q)
        while (idx >= 0 && out.length < 300) {
          out.push({
            ci,
            chapter: c.title,
            snippet: p.slice(Math.max(0, idx - 24), idx + q.length + 34),
          })
          idx = p.indexOf(q, idx + q.length)
        }
      })
    })
    findResults.value = out
    findTip.value = out.length ? `共 ${out.length} 处` : ''
    return
  }

  // EPUB：只搜目录
  const out = toc.value
    .map((t, i) => ({ t, i }))
    .filter(({ t }) => (t.label || '').includes(q))
    .map(({ t, i }) => ({ ci: i, chapter: t.label, snippet: '目录匹配', href: t.href }))
  findResults.value = out
  findTip.value = out.length
    ? `目录命中 ${out.length} 条（EPUB 正文全文搜索暂未支持）`
    : 'EPUB 只能搜目录标题，正文搜索待后续版本'
}

function jumpToResult(r) {
  findOpen.value = false
  if (kind.value === 'epub') {
    if (r.href) rendition?.display(r.href)
    return
  }
  goChapter(r.ci)
}

/* ---------------- 书签 / 笔记（v2.46.212） ---------------- */
const marksOpen = ref(false)
const marks = ref([])
const MARK_LABEL = { bookmark: '书签', highlight: '划线', note: '笔记' }

/** 三个面板互斥（目录 / 书签 / 设置），避免叠在一起 */
function togglePanel(which) {
  // 🔴 必须取 .value：直接放 ref 对象，`!ref` 恒为 false，面板永远打不开
  const cur = { toc: tocOpen.value, marks: marksOpen.value, set: setOpen.value, find: findOpen.value }
  const next = !cur[which]
  tocOpen.value = false
  marksOpen.value = false
  setOpen.value = false
  findOpen.value = false
  if (which === 'toc') tocOpen.value = next
  else if (which === 'marks') { marksOpen.value = next; if (next) loadMarks() }
  else if (which === 'find') { findOpen.value = next; if (next) nextTick(() => document.querySelector('.nrd-find-input')?.focus()) }
  else setOpen.value = next
}

async function loadMarks() {
  const tk = localStorage.getItem('token') || ''
  try {
    const r = await fetch(`/api/novels/${props.novel.id}/bookmarks`, {
      headers: { Authorization: `Bearer ${tk}` },
    })
    const j = await r.json()
    marks.value = Array.isArray(j.data?.list) ? j.data.list : []
  } catch { marks.value = [] }
}

/** 当前位置加书签 / 写笔记 */
async function addMark(kind) {
  const tk = localStorage.getItem('token') || ''
  const cfi = kind.value === 'epub'
    ? (rendition?.currentLocation()?.start?.cfi || '')
    : ''
  const chapter = kind.value === 'epub'
    ? (toc.value[tocActive.value]?.label || '')
    : (txtChapter.value?.title || '')

  let note = ''
  if (kind === 'note') {
    const txt = window.prompt('记点什么：', '')
    if (txt === null) return
    note = txt.trim()
    if (!note) return
  }

  try {
    await fetch(`/api/novels/${props.novel.id}/bookmarks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${tk}` },
      body: JSON.stringify({
        kind, cfi, chapter, note,
        quote: kind === 'highlight' ? note : '',
        percent: (percent.value || 0) / 100,
      }),
    })
    await loadMarks()
  } catch { /* 忽略 */ }
}

async function removeMark(m) {
  const tk = localStorage.getItem('token') || ''
  try {
    await fetch(`/api/novels/bookmarks/${m.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${tk}` },
    })
    marks.value = marks.value.filter((x) => x.id !== m.id)
  } catch { /* 忽略 */ }
}

/** 跳转到书签位置 */
function jumpToMark(m) {
  marksOpen.value = false
  if (kind.value === 'epub') {
    if (m.cfi) rendition?.display(m.cfi)
    return
  }
  // TXT：先找章节标题，找不到就按百分比估算章节
  const idx = txtChapters.value.findIndex((c) => c.title === m.chapter)
  if (idx >= 0) { goChapter(idx); return }
  const guess = Math.min(
    txtChapters.value.length - 1,
    Math.max(0, Math.floor((m.percent || 0) * txtChapters.value.length))
  )
  goChapter(guess)
}

/* ---------------- 朗读（Web Speech API） ---------------- */
const speaking = ref(false)
let utter = null

function currentSpeakText() {
  if (kind.value === 'txt') {
    const c = txtChapter.value
    if (!c) return ''
    return `${c.title}。${c.paras.join(' ')}`
  }
  return ''
}

function toggleSpeak() {
  if (speaking.value) { stopSpeak(); return }
  const text = currentSpeakText()
  if (!text) {
    // EPUB 的正文在 iframe 里，取不到纯文本；TXT 才有内容可读
    window.alert('朗读目前只支持 TXT 书籍')
    return
  }
  if (!('speechSynthesis' in window)) {
    window.alert('当前浏览器不支持语音朗读')
    return
  }
  utter = new SpeechSynthesisUtterance(text.slice(0, 8000))
  utter.lang = 'zh-CN'
  utter.rate = 1
  utter.onend = () => { speaking.value = false }
  utter.onerror = () => { speaking.value = false }
  speaking.value = true
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(utter)
}

function stopSpeak() {
  try { window.speechSynthesis.cancel() } catch { /* 忽略 */ }
  speaking.value = false
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

/* 真全屏页：隐藏站点外壳 + 手机切真机 viewport（统一实现，见 useFullscreenPage） */
useFullscreenPage()

/* ---------------- 初始化 ---------------- */
onMounted(async () => {
  loadSettings()
  watchSysTheme()
  if (followSys.value) applySysTheme()
  // 当前选中的 webfont 异步加载（不阻塞正文渲染，加载完 applyAll 里自动重注入）
  ensureFont(curFont.value)
  window.addEventListener('keydown', onKey)
  window.addEventListener('resize', onResize)
  enterTouchMode()
  try {
    kind.value = pickKind()
    if (!kind.value) throw new Error('只支持 EPUB 和 TXT 格式')
    const buf = await fetchBuffer()
    if (kind.value === 'pdf') {
      openPdf(buf)
    } else if (kind.value === 'epub') {
      await openEpub(buf)
    } else {
      const text = decodeText(buf)
      txtChapters.value = splitChapters(text)
      toc.value = txtChapters.value.map((c) => ({ label: c.title }))
      let saved = null
      try { saved = JSON.parse(localStorage.getItem(PROG_KEY.value) || 'null') } catch { /* 忽略 */ }
      // 服务器进度（progress_chapter 存的是章节标题，找它的下标）
      let ci = saved && Number.isInteger(saved.chapter) ? saved.chapter : 0
      const srvChapter = String(props.novel.progress_chapter || '')
      if (srvChapter) {
        const idx = txtChapters.value.findIndex((c) => c.title === srvChapter)
        if (idx >= 0) ci = idx
      }
      txtIndex.value = Math.min(Math.max(0, ci), txtChapters.value.length - 1)
      // 进度统一由 syncTxtPercent 算（含章内页比）；这里先给个粗值，nextTick 后再校准
      percent.value = Math.round((txtIndex.value / txtChapters.value.length) * 100)
      await nextTick()
      syncTxtPercent()
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
  stopSpeak()
  stopAutoPlay()
  clearTimeout(remoteTimer)
  flushProgress()
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('resize', onResize)

  clearTimeout(scrollTimer)
  try { rendition?.destroy() } catch { /* 忽略 */ }
  try { book?.destroy() } catch { /* 忽略 */ }
  if (pdfUrl.value) URL.revokeObjectURL(pdfUrl.value)
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
  /* v2.46.205：1600 会被站点侧栏/桌宠(1800)压住，实测手机上左侧被侧栏挡掉一半。
     提到 1900（仍低于全局提示层 9999 与 ElMessage 2000）。 */
  z-index: 1900;
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
/* 手机端：底部抽屉（对齐主流阅读 App 的设置面板习惯，拇指好够） */
@media (max-width: 640px) {
  .nrd-set {
    top: auto;
    right: 0;
    left: 0;
    bottom: 0;
    width: 100%;
    max-width: none;
    max-height: 72vh;
    overflow-y: auto;
    border-radius: 18px 18px 0 0;
    border-left: 0;
    border-right: 0;
    border-bottom: 0;
    padding: 18px 18px calc(16px + env(safe-area-inset-bottom, 0px));
    box-shadow: 0 -12px 40px -18px rgba(0, 0, 0, .5);
  }
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
/* 背景 5 色圆点 */
.nrd-dots {
  flex: 1;
  display: flex;
  gap: 12px;
}
.nrd-dot {
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  border-radius: 50%;
  border: 1px solid var(--nrd-line);
  cursor: pointer;
  transition: transform .15s, box-shadow .15s;
}
.nrd-dot.on {
  box-shadow: 0 0 0 2px var(--nrd-bg), 0 0 0 3.5px var(--nrd-text);
  transform: scale(1.05);
}
.nrd-seg-fonts button.loading {
  opacity: .55;
  pointer-events: none;
}
/* 亮度遮罩：盖住整个阅读器压暗画面，pointer-events:none 不挡任何交互 */
.nrd-dim {
  position: absolute;
  inset: 0;
  background: #000;
  pointer-events: none;
  z-index: 30;
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

/* ================= 移动端 / 触摸设备（v2.46.202） =================
   用 pointer: coarse 判断而不是屏幕宽度 —— 本站手机浏览器 viewport 被覆写成 1280，
   @media (max-width: 767px) 在手机上根本不触发。 */
.nrd {
  padding-top: env(safe-area-inset-top, 0);
  padding-bottom: env(safe-area-inset-bottom, 0);
}
.nrd-bar { padding-left: calc(12px + env(safe-area-inset-left, 0)); padding-right: calc(12px + env(safe-area-inset-right, 0)); }

@media (pointer: coarse) {
  /* 手指目标放大到 42px 以上 */
  .nrd-bar { height: 56px; }
  .nrd-ic { width: 42px; height: 42px; font-size: 17px; }
  .nrd-name { font-size: 15px; }
  .nrd-foot { height: 54px; }
  .nrd-nav { padding: 10px 18px; font-size: 14px; }

  /* 点击翻页热区扩到两侧 30%：手机上比 12% 好按得多 */
  .nrd-edge { top: 56px; bottom: 54px; width: 30%; }

  /* 设置面板改成底部弹出，占满宽度，拇指够得着 */
  .nrd-set {
    left: 8px;
    right: 8px;
    top: auto;
    bottom: 0;
    width: auto;
    max-width: none;
    padding: 18px 16px calc(18px + env(safe-area-inset-bottom, 0));
    border-radius: 18px 18px 0 0;
  }
  .nrd-set-row > span { width: 34px; font-size: 13px; }
  .nrd-seg button { padding: 10px 4px; font-size: 13px; }
  .nrd-slider input[type='range'] { height: 28px; }
  .nrd-btn { padding: 11px 20px; font-size: 14px; }

  /* 目录抽屉占满更多宽度，条目更高 */
  .nrd-toc { width: 86vw; max-width: 86vw; }
  .nrd-toc-item { padding: 13px 18px; font-size: 14.5px; }

  /* 分页模式下禁止浏览器接管手势，滑动由我们处理 */
  .nrd-txt.is-paged { touch-action: none; }
  /* 滚动模式允许原生纵向滚动 */
  .nrd-txt:not(.is-paged) { touch-action: pan-y; -webkit-overflow-scrolling: touch; }
}

/* PDF 容器（v2.46.215） */
.nrd-pdf { background: #525659; }
.nrd-pdf-frame { width: 100%; height: 100%; border: 0; display: block; }
.nrd-pdf-fallback {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  color: #e8e8e8;
  font-size: 13.5px;
  padding: 0 24px;
  text-align: center;
}
.nrd-pdf-fallback .nrd-btn {
  border: 0;
  background: #fff;
  color: #333;
  text-decoration: none;
  margin-top: 0;
}

/* 搜索抽屉（v2.46.215） */
.nrd-find { width: 340px; max-width: 88vw; }
.nrd-find-box {
  display: flex;
  gap: 8px;
  padding: 12px 14px 6px;
}
.nrd-find-input {
  flex: 1;
  min-width: 0;
  padding: 8px 12px;
  border-radius: 9px;
  border: 1px solid var(--nrd-line);
  background: transparent;
  color: inherit;
  font-size: 13.5px;
  font-family: inherit;
  outline: none;
}
.nrd-find-input:focus { border-color: currentColor; }
.nrd-find-box .nrd-btn { margin-top: 0; flex-shrink: 0; }
.nrd-find-tip {
  margin: 0;
  padding: 0 16px 8px;
  font-size: 11.5px;
  opacity: .55;
}
.nrd-find-item {
  display: block;
  width: 100%;
  padding: 10px 16px;
  border: 0;
  border-bottom: 1px solid var(--nrd-line);
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}
.nrd-find-item:hover { background: rgba(127, 127, 127, .1); }
.nrd-find-ch { display: block; font-size: 11.5px; opacity: .55; margin-bottom: 3px; }
.nrd-find-snip {
  display: block;
  font-size: 13px;
  line-height: 1.45;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* 书签抽屉（v2.46.212） */
.nrd-marks { width: 320px; max-width: 86vw; }
.nrd-mark-add {
  display: flex;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--nrd-line);
}
.nrd-mark-add .nrd-btn { flex: 1; margin-top: 0; }
.nrd-mark {
  display: flex;
  align-items: stretch;
  border-bottom: 1px solid var(--nrd-line);
}
.nrd-mark-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px 14px;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}
.nrd-mark-main:hover { background: rgba(127, 127, 127, .1); }
.nrd-mark-kind { font-size: 11px; opacity: .55; }
.nrd-mark-text {
  font-size: 13px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nrd-mark-pct { font-size: 11px; opacity: .45; }
.nrd-mark-del {
  width: 42px;
  flex-shrink: 0;
  border: 0;
  background: transparent;
  color: inherit;
  opacity: .45;
  font-size: 17px;
  cursor: pointer;
}
.nrd-mark-del:hover { opacity: .9; }
.nrd-ic.on { background: rgba(127, 127, 127, .18); }

/* 主题过渡 */
.nrd, .nrd-toc, .nrd-set { transition: background .22s ease, color .22s ease; }
</style>
