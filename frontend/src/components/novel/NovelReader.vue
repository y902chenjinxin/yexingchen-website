<template>
  <!-- 小说阅读器（v2.46.196）
       集成在小说模块内部，直接读 novels 表的原始文件，不依赖外部应用。
       EPUB 走 epub.js，TXT 前端分章后自己渲染。
       全屏覆盖层（z-index 1600，与项目全屏约定一致）。 -->
  <!-- 🔴 必须 Teleport 到 body：NovelView 的祖先链里有 transform，
       position:fixed 会相对那个祖先定位而不是视口，实测阅读器只占了右侧内容区、
       左边被侧边栏压住一半。挂到 body 才是真正的全屏。 -->
  <Teleport to="body">
  <div class="nrd" :class="[`theme-${theme}`, { 'is-chrome': showChrome }]" :style="cssVars" @click="onRootClick">
    <!-- 菜单遮罩（点空白收起；顶栏/底栏本身不冒泡到这里） -->
    <div v-if="showChrome && !anyPanelOpen()" class="nrd-scrim" @click.stop="showChrome = false" />

    <!-- 抽屉遮罩：抽屉打开时盖住正文，点它关抽屉（同时导航条已收起） -->
    <div v-if="anyPanelOpen()" class="nrd-scrim nrd-scrim-panel" @click.stop="closeAllPanels" />

    <!-- 顶栏：默认隐藏，点击页面中部滑出（番茄式） -->
    <header class="nrd-bar">
      <button class="nrd-ic" type="button" title="返回" @click.stop="$emit('close')">←</button>
      <div class="nrd-title">
        <span class="nrd-name">{{ novel.title }}</span>
        <span class="nrd-pct">{{ percent }}%</span>
      </div>
      <button v-if="kind !== 'pdf'" class="nrd-ic" type="button" title="搜索" @click.stop="openPanel('find')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.7" stroke-linecap="round" aria-hidden="true">
          <circle cx="10.5" cy="10.5" r="6.2" />
          <path d="M15.2 15.2 20 20" />
        </svg>
      </button>
      <button v-if="kind !== 'pdf'" class="nrd-ic" type="button" title="书签" @click.stop="openPanel('marks')">
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
        @click.stop="toggleSpeak"
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
    </header>

    <!-- 加载 / 错误 -->
    <div v-if="loading" class="nrd-mask">
      <div class="nrd-loading">正在打开《{{ novel.title }}》…</div>
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
      @wheel="onWheel"
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
          <section v-for="sec in loadedSecs" :key="'s' + sec.idx" class="nrd-sec" :data-idx="sec.idx">
            <h2 class="nrd-ch-title">{{ sec.title }}</h2>
            <p v-for="(para, i) in sec.paras" :key="'q' + i" class="nrd-p">{{ para }}</p>
          </section>
          <div v-if="loadedSecs.length >= txtChapters.length" class="nrd-end">— 全书完 —</div>
        </template>
      </div>
    </div>

    <!-- 底部导航（番茄式）：进度 + 上一章/下一章 + 目录/夜间/设置 -->
    <footer v-if="kind !== 'pdf'" class="nrd-foot">
      <div class="nrd-foot-prog">
        <span class="nrd-foot-chap">
          <template v-if="kind === 'txt'">第 {{ txtIndex + 1 }}/{{ txtChapters.length }} 章</template>
          <template v-else>目录 {{ tocActive + 1 }}/{{ toc.length }}</template>
        </span>
        <div class="nrd-prog"><i :style="{ width: percent + '%' }" /></div>
        <span class="nrd-foot-pct">{{ percent }}%</span>
      </div>

      <div class="nrd-foot-row">
        <button class="nrd-foot-nav" type="button" :disabled="atStart" @click.stop="prevChapter">上一章</button>
        <button class="nrd-foot-nav" type="button" @click.stop="nextChapter">下一章</button>
      </div>

      <div class="nrd-foot-tools">
        <button type="button" @click.stop="openPanel('toc')">
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="1.7" stroke-linecap="round" aria-hidden="true">
            <path d="M4 6h16M4 12h16M4 18h16" />
          </svg>
          <span>目录</span>
        </button>
        <button type="button" @click.stop="toggleDayNight">
          <svg v-if="theme === 'night'" width="19" height="19" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true">
            <circle cx="12" cy="12" r="4.2" />
            <path d="M12 2.6v2.2M12 19.2v2.2M2.6 12h2.2M19.2 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M18.7 5.3l-1.6 1.6M6.9 17.1l-1.6 1.6" />
          </svg>
          <svg v-else width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="1.6" stroke-linejoin="round" aria-hidden="true">
            <path d="M20.4 14.6A8.6 8.6 0 0 1 9.4 3.6a8.6 8.6 0 1 0 11 11Z" />
          </svg>
          <span>{{ theme === 'night' ? '白天' : '夜间' }}</span>
        </button>
        <button type="button" @click.stop="openPanel('set')">
          <b class="nrd-aa">Aa</b>
          <span>设置</span>
        </button>
      </div>
    </footer>

    <!-- 目录抽屉（底部滑出，可搜索标题） -->
    <div v-if="tocOpen" class="nrd-sheet nrd-sheet-toc" @click.stop>
      <div class="nrd-sheet-head">
        <input
          v-model="tocQ"
          class="nrd-sheet-q"
          type="search"
          placeholder="搜索章节标题"
          aria-label="搜索章节标题"
        />
        <button class="nrd-ic" type="button" @click="tocOpen = false">×</button>
      </div>
      <div class="nrd-toc-list">
        <button
          v-for="item in filteredToc"
          :key="item.i"
          class="nrd-toc-item"
          :class="{ active: item.i === tocActive }"
          type="button"
          @click="jumpTo(item.i)"
        >
          <span class="nrd-toc-label">{{ item.label }}</span>
          <span class="nrd-toc-idx">{{ item.i + 1 }}</span>
        </button>
        <p v-if="!filteredToc.length" class="nrd-toc-empty">
          {{ tocQ ? '没有匹配的章节' : '这本没有可用目录' }}
        </p>
      </div>
    </div>

    <!-- 全文搜索抽屉（v2.46.215） -->
    <transition name="nrd-fade">
      <aside v-if="findOpen" class="nrd-sheet nrd-sheet-toc nrd-find" @click.stop>
        <div class="nrd-sheet-head">
          <span class="nrd-sheet-title">搜索</span>
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
      <aside v-if="marksOpen" class="nrd-sheet nrd-sheet-toc nrd-marks" @click.stop>
        <div class="nrd-sheet-head">
          <span class="nrd-sheet-title">书签与笔记</span>
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
    <div v-if="setOpen" class="nrd-sheet nrd-sheet-set" @click.stop>
      <div class="nrd-sheet-head">
        <span class="nrd-sheet-title">阅读设置</span>
        <button class="nrd-ic" type="button" @click="setOpen = false">×</button>
      </div>
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
              :class="{ on: theme === t.key, 'is-custom': t.key === 'custom' }"
              :style="t.key === 'custom'
                ? { background: `linear-gradient(135deg, ${customColor} 55%, #fff 55%)` }
                : t.key === 'image'
                  ? { background: bgImage ? `center/cover url(${bgImage})` : 'repeating-linear-gradient(45deg, #ddd 0 4px, #bbb 4px 8px)' }
                  : { background: t.bg }"
              :title="t.label"
              @click="setTheme(t.key)"
            />
          </div>
        </div>

        <!-- 自定义背景（v2.46.286）：取色 / 传图 / 清除 -->
        <div class="nrd-set-row">
          <span>底色</span>
          <div class="nrd-bg-tools">
            <label class="nrd-bg-btn" :title="'取色 ' + customColor">
              <input v-model="customColor" type="color" class="nrd-color-input" @input="onCustomColor" />
              颜色
            </label>
            <button class="nrd-bg-btn" type="button" :disabled="bgUploading" @click="pickBgImage">
              {{ bgUploading ? '上传中…' : '上传图片' }}
            </button>
            <button v-if="bgImage" class="nrd-bg-btn" type="button" @click="clearBgImage">清除图片</button>
            <input ref="bgFileRef" type="file" accept="image/*" class="nrd-file-hidden" @change="onBgFile" />
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
          <span>段距</span>
          <div class="nrd-slider">
            <input v-model.number="paraGap" type="range" min="0" max="1.6" step="0.05" @input="onTypesetChange" />
            <em>{{ paraGap.toFixed(2) }}</em>
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
          <span>缩进</span>
          <div class="nrd-seg">
            <button type="button" :class="{ on: indent }" @click="setIndent(true)">首行缩进 2 字</button>
            <button type="button" :class="{ on: !indent }" @click="setIndent(false)">不缩进</button>
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
  // v2.46.286：自定义底色 / 自定义背景图（bg 与文字色由 curTheme 动态算）
  { key: 'custom', label: '自定义色', bg: '#f0e6cd', text: '#2b2b2b', sub: '#8a8a8a', line: 'rgba(0,0,0,.1)' },
  { key: 'image', label: '背景图', bg: '#fbf7ee', text: '#2b2b2b', sub: '#7b7368', line: 'rgba(0,0,0,.12)' },
]
// v2.46.281：宋/黑/楷三档首选换成 GitHub 开源字体（服务器 /fonts/ 下，FontFace 按需加载），
// 系统栈保留做兜底 —— 鸿蒙等无宋/楷字库的设备不再整体退化成黑体。
const FONTS = [
  { key: 'song', label: '宋体', stack: '"Noto Serif CJK SC", "Songti SC", "SimSun", serif', webfont: 'Noto Serif CJK SC', file: '/fonts/NotoSerifSC-Regular.otf' },
  { key: 'hei', label: '黑体', stack: '"Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", sans-serif', webfont: 'Noto Sans CJK SC', file: '/fonts/NotoSansSC-Regular.otf' },
  { key: 'kai', label: '楷体', stack: '"LXGW WenKai", "Kaiti SC", "KaiTi", serif', webfont: 'LXGW WenKai', file: '/fonts/LXGWWenKai-Regular.ttf' },
  { key: 'fang', label: '仿宋', stack: '"Zhuque Fangsong", "FangSong", "STFangsong", serif', webfont: 'Zhuque Fangsong', file: '/fonts/ZhuqueFangsong-Regular.ttf' },
  // 夜星自找的三款（v2.46.282）：思源宋体 VF 实例化 Bold、思源黑体 Medium、文源宋体
  { key: 'songb', label: '宋粗', stack: '"Source Han Serif SC VF", "Songti SC", serif', webfont: 'Source Han Serif SC VF', file: '/fonts/SourceHanSerifSC-Bold.ttf' },
  { key: 'heim', label: '黑中', stack: '"Source Han Sans SC Medium", "PingFang SC", "Microsoft YaHei", sans-serif', webfont: 'Source Han Sans SC Medium', file: '/fonts/SourceHanSansSC-Medium.otf' },
  { key: 'wenyuan', label: '文源宋', stack: '"WenYuan Serif SC", "Songti SC", serif', webfont: 'WenYuan Serif SC', file: '/fonts/WenYuanSerifSC-Regular.ttf' },
  // v2.46.283：方正楷体简体（GB2312 6763 字，方正免费商用清单内）
  { key: 'fzkai', label: '方正楷', stack: '"FZKai-Z03S", "Kaiti SC", "KaiTi", serif', webfont: 'FZKai-Z03S', file: '/fonts/FZKai-Z03S.ttf' },
]

const SET_KEY = 'xuanhuang:reader:settings'
const defaultSettings = {
  theme: 'day', font: 'song', size: 19, lineHeight: 1.9, padding: 28, flow: 'paginated',
  brightness: 100, followSys: false,
  // v2.46.285 排版（Kindle 风）：首行缩进 2 字、段间距 0.85em
  indent: true, paraGap: 0.85,
  // v2.46.286 自定义底色
  customColor: '#f0e6cd',
}
const settings = ref({ ...defaultSettings })
const theme = computed(() => settings.value.theme)
const font = computed(() => settings.value.font)
const size = computed({ get: () => settings.value.size, set: (v) => (settings.value.size = v) })
const lineHeight = computed({ get: () => settings.value.lineHeight, set: (v) => (settings.value.lineHeight = v) })
const padding = computed({ get: () => settings.value.padding, set: (v) => (settings.value.padding = v) })
const flow = computed({ get: () => settings.value.flow, set: (v) => (settings.value.flow = v) })
const brightness = computed({ get: () => settings.value.brightness ?? 100, set: (v) => (settings.value.brightness = v) })
const followSys = computed({ get: () => !!settings.value.followSys, set: (v) => (settings.value.followSys = v) })
const indent = computed({ get: () => settings.value.indent !== false, set: (v) => (settings.value.indent = v) })
const paraGap = computed({ get: () => settings.value.paraGap ?? 0.85, set: (v) => (settings.value.paraGap = v) })
const autoPlay = ref(false)   // 自动翻页：运行态不进 localStorage，翻页档位「自动」= paginated + autoPlay
const fontLoading = ref('')   // 正在加载的 webfont key（按钮转圈提示）

/* ---- 自定义背景（v2.46.286）---- */
const customColor = ref(settings.value.customColor || '#f0e6cd')
const bgImage = ref('')          // 服务器返回的 url（带 token 的接口路径）
const bgUploading = ref(false)
const bgFileRef = ref(null)

/** #rrggbb → 是否偏亮（决定文字用深色还是浅色） */
function isLightColor(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(String(hex || ''))
  if (!m) return true
  const n = parseInt(m[1], 16)
  const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255
  return (0.299 * r + 0.587 * g + 0.114 * b) > 148
}

const curTheme = computed(() => {
  const t = THEMES.find((x) => x.key === theme.value) || THEMES[0]
  if (t.key === 'custom') {
    const c = customColor.value
    const light = isLightColor(c)
    return {
      ...t, bg: c,
      text: light ? '#2b2b2b' : '#e9e9e9',
      sub: light ? '#8a8a8a' : '#9aa0a6',
      line: light ? 'rgba(0,0,0,.12)' : 'rgba(255,255,255,.16)',
    }
  }
  if (t.key === 'image') {
    // 图片上压一层主题底色，保证正文始终可读（按白天底算，字深）
    return { ...t, bg: '#fbf7ee', text: '#2b2b2b', sub: '#7b7368', line: 'rgba(0,0,0,.12)' }
  }
  return t
})
const curFont = computed(() => FONTS.find((f) => f.key === font.value) || FONTS[0])

/* 手机浏览器的 layout viewport 比可视区高（地址栏/工具栏占位），
   `position: fixed; inset: 0` 会按 layout viewport 撑高 → 底栏被推到浏览器工具栏
   后面、点不到（v2.46.288 夜星反馈「底部目录/设置按钮点不到」）。
   用 visualViewport 的实时高度给容器定高，底部按钮才落在可视区内。 */
const vpHeight = ref(0)
function syncVpHeight() {
  const vv = window.visualViewport
  vpHeight.value = Math.round((vv && vv.height) || window.innerHeight || 0)
}

const cssVars = computed(() => {
  const veil = 'rgba(251, 247, 238, .78)'
  const bgImageStyle = theme.value === 'image' && bgImage.value
    ? `linear-gradient(${veil}, ${veil}), url("${bgImage.value}")`
    : 'none'
  return {
    '--nrd-bg': curTheme.value.bg,
    '--nrd-text': curTheme.value.text,
    '--nrd-sub': curTheme.value.sub,
    '--nrd-line': curTheme.value.line,
    '--nrd-size': size.value + 'px',
    '--nrd-lh': String(lineHeight.value),
    '--nrd-pad': padding.value + 'px',
    '--nrd-font': curFont.value.stack,
    '--nrd-indent': indent.value ? '2em' : '0em',
    '--nrd-pgap': paraGap.value + 'em',
    '--nrd-bg-image': bgImageStyle,
    // 有实测值就写死像素，否则回落到 CSS 的 100dvh
    height: vpHeight.value ? `${vpHeight.value}px` : undefined,
  }
})

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
  if (settings.value.customColor) customColor.value = settings.value.customColor
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
    // 分页 ↔ 滚动：分页要重新量页宽；滚动要确保当前章 ± 邻章在 DOM 里
    nextTick(async () => {
      if (v === 'paginated') { txtPage.value = 0; measurePages() }
      else {
        await ensureSec(txtIndex.value)
        await ensureSec(txtIndex.value + 1)
        syncTxtPercent()
      }
    })
  }
}
/** 排版类改动（段距/缩进）：存盘 + 重新分页（页数会变，不重算会翻页错位） */
function onTypesetChange() {
  saveSettings()
  onResize()
}
function setIndent(v) {
  indent.value = v
  saveSettings()
  onResize()
}

/* ---------------- 番茄式交互（v2.46.286） ----------------
   点击页面：左 1/3 上一页、右 1/3 下一页、中间 / 滚动模式任意处 → 唤出顶栏+底栏。
   再点空白（或遮罩）收起。目录与设置都是底部抽屉。 */
const showChrome = ref(false)
const tocQ = ref('')

/** 是否有任一抽屉打开（目录/设置/搜索/书签） */
/* 🔴 必须是函数不是 computed：tocOpen(748) / findOpen(1304) / marksOpen(1352) 都定义在
   这里之后，computed 被 watch 立即求值会撞 TDZ（Cannot access 'tocOpen' before initialization）。 */
function anyPanelOpen() {
  return tocOpen.value || setOpen.value || findOpen.value || marksOpen.value
}

function closeAllPanels() {
  tocOpen.value = false
  setOpen.value = false
  findOpen.value = false
  marksOpen.value = false
}

function onRootClick(e) {
  // 点在交互元素上不当作「翻页/唤菜单」
  if (e.target.closest('button, input, label, a, .nrd-sheet, .nrd-bar, .nrd-foot, .nrd-set, .nrd-toc, .nrd-dim')) return
  if (window.getSelection && String(window.getSelection())) return   // 正在划线选字
  // v2.46.287：抽屉开着时点空白 = 关抽屉（番茄行为），不能反过来把顶栏底栏唤出来
  // —— 否则两侧同时出现，导航条会压着抽屉（夜星截图反馈）
  if (anyPanelOpen()) { closeAllPanels(); return }
  if (showChrome.value) { showChrome.value = false; return }
  if (flow.value === 'paginated' && kind.value !== 'pdf') {
    const w = window.innerWidth || 1
    if (e.clientX < w * 0.3) { txtPrev(); return }
    if (e.clientX > w * 0.7) { txtNext(); return }
  }
  showChrome.value = true
}

/** 打开某个面板（收起 chrome，保证抽屉独占视线） */
function openPanel(which) {
  showChrome.value = false
  const cur = { toc: tocOpen.value, marks: marksOpen.value, set: setOpen.value, find: findOpen.value }
  closeAllPanels()
  if (cur[which]) return
  if (which === 'toc') tocOpen.value = true
  else if (which === 'marks') { marksOpen.value = true; loadMarks() }
  else if (which === 'find') { findOpen.value = true; nextTick(() => document.querySelector('.nrd-find-input')?.focus()) }
  else setOpen.value = true
}


/** 目录搜索过滤（保留原始索引，跳转要用） */
const filteredToc = computed(() => {
  const q = tocQ.value.trim()
  const all = toc.value.map((x, i) => ({ ...x, i }))
  if (!q) return all
  return all.filter((x) => String(x.label || '').includes(q))
})

function prevChapter() {
  if (kind.value === 'epub') { rendition?.prev(); return }
  if (txtIndex.value > 0) goChapter(txtIndex.value - 1, flow.value === 'paginated')
}

function nextChapter() {
  if (kind.value === 'epub') { rendition?.next(); return }
  if (txtIndex.value < txtChapters.value.length - 1) goChapter(txtIndex.value + 1)
}

/** 底栏「夜间/白天」：当前是夜间就回白天，否则进夜间 */
function toggleDayNight() {
  setTheme(theme.value === 'night' ? 'day' : 'night')
}

/* ---- 自定义背景：取色 / 传图 / 清除 ---- */
function onCustomColor() {
  settings.value.customColor = customColor.value
  setTheme('custom')
}
function pickBgImage() {
  bgFileRef.value?.click()
}
async function onBgFile(e) {
  const f = e.target.files && e.target.files[0]
  if (!f) return
  bgUploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', f)
    const r = await fetch('/api/novels/reader-bg', { method: 'POST', headers: authHeaders(), body: fd })
    const j = await r.json().catch(() => null)
    if (!r.ok || !j || j.code !== 0) throw new Error((j && j.msg) || `HTTP ${r.status}`)
    bgImage.value = j.data.url
    setTheme('image')
  } catch (err) {
    error.value = `背景上传失败：${err.message || err}`
    setTimeout(() => { error.value = '' }, 2500)
  } finally {
    bgUploading.value = false
    e.target.value = ''
  }
}
async function clearBgImage() {
  bgImage.value = ''
  if (theme.value === 'image') setTheme('eye')
  try {
    await fetch('/api/novels/reader-bg/img', { method: 'DELETE', headers: authHeaders() })
  } catch { /* 忽略 */ }
}
async function loadReaderBg() {
  try {
    const r = await fetch('/api/novels/reader-bg', { headers: authHeaders() })
    const j = await r.json()
    if (j && j.code === 0 && j.data && j.data.url) bgImage.value = j.data.url
  } catch { /* 忽略 */ }
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
/* EPUB 的「是否在开头」由 epub.js relocated 事件给；TXT 得自己算。
   🔴 v2.46.284：原来只有 ref 且只在 EPUB 事件里赋值 → TXT 模式下永远是 true，
   「上一页」按钮永久禁用（夜星反馈「点不了上一页」正是这个）。 */
const epubAtStart = ref(true)

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

/** 「上一页」禁用判定：EPUB 用 epub.js 的位置，TXT 看「第0章第0页」 */
const atStart = computed(() => {
  if (kind.value === 'epub') return epubAtStart.value
  return txtIndex.value === 0 && txtPage.value === 0
})
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

/** 滚动模式：确保第 idx 章已渲染（稀疏加载 —— 只取需要的章）。
    🔴 v2.46.284：旧实现 `loadUntil(curIdx)` 会把 0..curIdx 全部塞进 DOM。
    改成按章请求后这就成了「打开时串行发 curIdx 个请求」——上次读到第 800 章
    就要跑 800 个网络请求，表现为一直转圈 + 卡死（夜星反馈「一直在解析」）。
    现在只加载当前章 ± 邻章。 */
async function ensureSec(idx) {
  if (idx < 0 || idx >= txtChapters.value.length) return false
  if (loadedSecs.value.some((s) => s.idx === idx)) return true
  const c = txtChapters.value[idx]
  if (!c) return false
  await loadChapterData(idx)
  loadedSecs.value = [...loadedSecs.value, { idx, title: c.title, paras: c.paras || [] }]
    .sort((a, b) => a.idx - b.idx)
  return true
}

/** 加载已渲染的最后一章的下一章 */
let secLoading = false
async function ensureNext() {
  if (secLoading) return
  const last = loadedSecs.value[loadedSecs.value.length - 1]
  const next = last ? last.idx + 1 : 0
  if (next >= txtChapters.value.length) return
  secLoading = true
  try { await ensureSec(next) } finally { secLoading = false }
}

/** 往前加载一章，并补偿滚动位置（否则插入内容会把读者视野顶走） */
async function ensurePrev() {
  if (secLoading) return
  const first = loadedSecs.value[0]
  if (!first || first.idx <= 0) return
  const el = txtRef.value
  const prevH = el ? el.scrollHeight : 0
  const prevTop = el ? el.scrollTop : 0
  secLoading = true
  try {
    await ensureSec(first.idx - 1)
    await nextTick()
    if (el) el.scrollTop = prevTop + (el.scrollHeight - prevH)
  } finally {
    secLoading = false
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

/* ---------------- TXT 后端预解析：索引 + 按章取（v2.46.283） ----------------
   旧做法每次打开都全量拉文件、在手机上切几十万行、整本段落驻内存 —— 13MB 的书
   直接卡死。现在后端一次解析成「归一化 UTF-8 + 字节偏移索引」，前端只拉章节目录
   （几十 KB）和当前章正文（几十 KB），滚动模式往后预取。 */
const txtStatus = ref('')       // '' / pending / done / failed
const chapterLoading = ref(false)

function authHeaders() {
  return { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }
}

async function novelApi(path, opts = {}) {
  // v2.46.284：加超时 —— 后端解析卡住时不能无限转圈（夜星遇到「一直在解析」）
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), opts.timeout || 30000)
  try {
    const res = await fetch(`/api/novels/${props.novel.id}${path}`, {
      ...opts,
      signal: ctrl.signal,
      headers: { ...authHeaders(), ...(opts.headers || {}) },
    })
    const json = await res.json().catch(() => null)
    if (!res.ok || !json || json.code !== 0) {
      throw new Error((json && (json.msg || json.detail)) || `HTTP ${res.status}`)
    }
    return json.data
  } catch (e) {
    if (e.name === 'AbortError') throw new Error('请求超时（30s），请稍后重试')
    throw e
  } finally {
    clearTimeout(timer)
  }
}

/** 拉章节索引；若后端还没解析过（老书），先同步触发一次解析再拉。 */
async function loadChapterIndex() {
  let d = await novelApi('/chapters')
  txtStatus.value = d.status || ''
  if (d.status !== 'done') {
    // 解析 12MB 约 0.3~0.6s，同步等一次比让用户自己点更好
    await novelApi('/parse', { method: 'POST' })
    d = await novelApi('/chapters')
    txtStatus.value = d.status || ''
  }
  if (d.status !== 'done' || !(d.chapters || []).length) {
    throw new Error('解析失败，请重试或换一个 TXT 文件')
  }
  txtChapters.value = d.chapters.map((c) => ({ title: c.t, paras: null }))
  return d
}

/** 按章取正文（幂等：已加载直接返回）。返回 false 表示失败。 */
async function loadChapterData(idx) {
  const c = txtChapters.value[idx]
  if (!c) return false
  if (c.paras) return true
  chapterLoading.value = true
  try {
    const d = await novelApi(`/chapters/${idx}`)
    c.paras = d.paras && d.paras.length ? d.paras : ['（本章无内容）']
    return true
  } catch {
    c.paras = ['（本章加载失败，滑走再回来可重试）']
    return false
  } finally {
    chapterLoading.value = false
  }
}

function pickKind(name) {
  const n = String(name || props.novel.original_filename || '').toLowerCase()
  if (n.endsWith('.epub')) return 'epub'
  if (n.endsWith('.txt')) return 'txt'
  if (n.endsWith('.pdf')) return 'pdf'
  return ''
}

/* v2.46.283：TXT 的解码与分章已全部移到后端（app/services/novel_parser.py），
   前端只拿「章节索引 + 按章正文」。原 decodeText / splitChapters 已删除
   —— 13MB 的书在手机上 split 几十万行会把页面卡死，这是本次改造的根因。 */

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
  // PDF 内嵌在 iframe 里，点击冒泡不出来 → 让顶栏常显，否则唤不出菜单
  showChrome.value = true
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
    epubAtStart.value = !!loc?.atStart
  })
  rendition.on('keyup', onKey)
  // 给每章 iframe 内部挂触摸手势（外部监听收不到 iframe 里的 touch）
  rendition.hooks.content.register((contents) => {
    const doc = contents && contents.document
    if (!doc) return
    doc.addEventListener('touchstart', onTouchStart, { passive: true })
    doc.addEventListener('touchend', onTouchEnd, { passive: true })
    // v2.46.286：iframe 内的点击不会冒泡到父页面 —— 必须单独挂，
    // 否则 EPUB 看书点页面出不来顶栏/底栏（TXT 没有 iframe 所以之前没暴露）
    doc.addEventListener('click', (ev) => {
      if (showChrome.value) { showChrome.value = false; return }
      const vw = contents.window?.innerWidth || window.innerWidth || 1
      const x = ev.clientX ?? 0
      if (flow.value === 'paginated') {
        if (x < vw * 0.3) { rendition?.prev(); return }
        if (x > vw * 0.7) { rendition?.next(); return }
      }
      showChrome.value = true
    })
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
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 60) {
    ensureNext()
    nextTick(() => el.scrollBy({ top: el.clientHeight * 0.9, behavior: 'smooth' }))
    return
  }
  el.scrollBy({ top: el.clientHeight * 0.9, behavior: 'smooth' })
}

/** 切章（分页模式重置到第一页；toLast=true 时落到最后一页） */
let navSeq = 0
async function goChapter(i, toLast = false) {
  if (i < 0 || i >= txtChapters.value.length) return
  const my = ++navSeq          // 连点防乱序：只有最后一次生效（不再直接 return 吞点击）
  txtIndex.value = i
  tocActive.value = i
  await loadChapterData(i)     // v2.46.283：正文按需取
  if (my !== navSeq) return
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
    await ensureSec(i)
    await nextTick()
    const el = txtRef.value
    const sec = el?.querySelector(`.nrd-sec[data-idx="${i}"]`)
    if (sec && el) el.scrollTop = sec.offsetTop
    syncTxtPercent()
  }
}

function switchChapter(i) {
  return goChapter(i, false)
}

/** 桌面端分页模式：鼠标滚轮 → 上一页/下一页（v2.46.284，夜星「上下滑动不了」） */
let wheelLock = 0
function onWheel(e) {
  if (kind.value !== 'txt' || flow.value !== 'paginated') return   // 滚动模式交给浏览器原生
  if (Math.abs(e.deltaY) < 10) return
  e.preventDefault()
  const now = Date.now()
  if (now - wheelLock < 380) return     // 触控板一次滑动会连发几十个事件，必须锁
  wheelLock = now
  if (e.deltaY > 0) txtNext()
  else txtPrev()
}

let scrollTimer = 0
let scrollRaf = 0
function onTxtScroll() {
  const el = txtRef.value
  if (!el) return

  if (flow.value === 'scroll') {
    // 滚动事件每帧都来，DOM 查询（querySelectorAll + offsetTop）必须节流到 rAF 里做，
    // 否则桌面上快速滚动会明显掉帧（v2.46.284）
    if (!scrollRaf) {
      scrollRaf = requestAnimationFrame(() => {
        scrollRaf = 0
        const cur = txtRef.value
        if (!cur) return
        // 接近底部：追加下一章；接近顶部：往前补一章（稀疏加载，只按需取）
        if (cur.scrollTop + cur.clientHeight > cur.scrollHeight - 800) ensureNext()
        else if (cur.scrollTop < 80) ensurePrev()
        // 反推当前章节：必须读 data-idx（稀疏加载后渲染序号 ≠ 章节号）
        const secs = cur.querySelectorAll('.nrd-sec')
        let idx = txtIndex.value
        secs.forEach((sd) => {
          if (sd.offsetTop <= cur.scrollTop + 8) idx = Number(sd.dataset.idx ?? idx)
        })
        if (idx !== txtIndex.value) { txtIndex.value = idx; tocActive.value = idx }
      })
    }
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

async function runFind() {
  const q = findQ.value.trim()
  findResults.value = []
  if (!q) { findTip.value = ''; return }

  if (kind.value === 'txt') {
    // v2.46.283：全文在服务器（归一化缓存），搜索走接口 —— 前端不再持全书正文
    findTip.value = '搜索中…'
    try {
      const d = await novelApi(`/search?q=${encodeURIComponent(q)}&limit=300`)
      findResults.value = (d.items || []).map((it) => ({
        ci: it.i,
        chapter: it.title,
        snippet: it.snippet,
      }))
      findTip.value = d.count ? `共 ${d.count} 处` : '没有找到'
    } catch {
      findTip.value = '搜索失败，请重试'
    }
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

/* v2.46.286：面板开关统一走 openPanel（见上），旧的 togglePanel 已删除 ——
   顶栏/底栏都改成「打开指定面板」，不再需要 toggle 语义。 */

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

/* 真全屏页：隐藏站点外壳 + 手机切真机 viewport（统一实现，见 useFullscreenPage）
   keepOverlays：看小说时保留音乐条与桌宠（夜星要求），牌桌那类全屏仍全收 */
useFullscreenPage({ keepOverlays: true })

/* ---------------- 初始化 ---------------- */
onMounted(async () => {
  loadSettings()
  watchSysTheme()
  if (followSys.value) applySysTheme()
  // 当前选中的 webfont 异步加载（不阻塞正文渲染，加载完 applyAll 里自动重注入）
  ensureFont(curFont.value)
  loadReaderBg()
  syncVpHeight()
  window.visualViewport?.addEventListener('resize', syncVpHeight)
  window.addEventListener('keydown', onKey)
  window.addEventListener('resize', onResize)
  enterTouchMode()
  try {
    kind.value = pickKind()
    if (!kind.value) throw new Error('只支持 EPUB 和 TXT 格式')
    if (kind.value === 'txt') {
      // v2.46.283：先取后端解析好的章节目录，正文按章拉 —— 不再全量下载 + 前端切章
      await loadChapterIndex()
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
      percent.value = Math.round((txtIndex.value / txtChapters.value.length) * 100)
      await loadChapterData(txtIndex.value)   // 当前章正文
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
        // 滚动模式：只铺当前章 + 后一章（不再 0..curIdx 全量铺开）
        await ensureSec(txtIndex.value)
        await ensureSec(txtIndex.value + 1)
        await nextTick()
        if (saved?.scrollTop && txtRef.value) txtRef.value.scrollTop = saved.scrollTop
      }
    } else {
      const buf = await fetchBuffer()
      if (kind.value === 'pdf') {
        openPdf(buf)
      } else {
        await openEpub(buf)
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
  window.visualViewport?.removeEventListener('resize', syncVpHeight)

  clearTimeout(scrollTimer)
  try { rendition?.destroy() } catch { /* 忽略 */ }
  try { book?.destroy() } catch { /* 忽略 */ }
  if (pdfUrl.value) URL.revokeObjectURL(pdfUrl.value)
})

/* 窗口尺寸 / 边距 / 字号变化 → 分页模式要重新切页 */
let resizeTimer = 0
function onResize() {
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => { measurePages() }, 180)
}
watch([size, lineHeight, padding], () => { onResize() })

/* 抽屉一打开就收掉导航条（防止顶栏/底栏压着抽屉，v2.46.287 夜星反馈）。
   放文件末尾：tocOpen/findOpen/marksOpen 都在上方定义完毕，不会撞 TDZ。 */
watch([tocOpen, setOpen, findOpen, marksOpen], (vals) => {
  if (vals.some(Boolean)) showChrome.value = false
})
</script>

<style scoped>
.nrd {
  position: fixed;
  inset: 0;
  /* v2.46.205：1600 会被站点侧栏/桌宠(1800)压住，实测手机上左侧被侧栏挡掉一半。
     提到 1900（仍低于全局提示层 9999 与 ElMessage 2000）。 */
  z-index: 1900;
  display: block;
  overflow: hidden;
  /* 兜底高度：visualViewport 不支持时靠 dvh；两行都被忽略就回到 inset:0 的老行为 */
  height: 100dvh;
  background-color: var(--nrd-bg);
  /* v2.46.286：自定义背景图（半透明底色已叠在图上方，保证正文可读） */
  background-image: var(--nrd-bg-image, none);
  background-size: cover;
  background-position: center;
  color: var(--nrd-text);
  font-family: var(--nrd-font);
}

/* 菜单遮罩：点空白收起顶栏/底栏（番茄只是轻微压暗，不要压太重） */
.nrd-scrim {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, .1);
  z-index: 11;
}
/* 抽屉遮罩：压暗正文并把点击焦点交给「关抽屉」，层级夹在 chrome(12) 与抽屉(14) 之间 */
.nrd-scrim-panel {
  z-index: 13;
  background: rgba(0, 0, 0, .22);
}

/* 顶栏：默认隐藏，点页面中部滑出（番茄式） */
.nrd-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 52px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  border-bottom: 1px solid var(--nrd-line);
  background: var(--nrd-bg);
  z-index: 12;
  transform: translateY(-100%);
  opacity: 0;
  pointer-events: none;
  transition: transform .22s cubic-bezier(.22, .61, .36, 1), opacity .16s;
}
.nrd.is-chrome .nrd-bar {
  transform: none;
  opacity: 1;
  pointer-events: auto;
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
/* 内容舞台：铺满整个视口（顶栏/底栏是浮层，不占位） */
.nrd-stage { position: absolute; inset: 0; overflow: hidden; }
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
  margin: 0 0 var(--nrd-pgap, .85em);
  text-indent: var(--nrd-indent, 2em);
  text-align: justify;
  word-break: break-word;
  /* 中文正文排版细节（v2.46.285）：标点挤压 + 更好的字形渲染 */
  text-justify: inter-ideograph;
  -webkit-font-smoothing: antialiased;
}
.nrd-end {
  margin: 2.4em 0 1em;
  text-align: center;
  font-size: .85em;
  color: var(--nrd-sub);
}

/* 底栏（番茄式三段：进度 / 上一章下一章 / 目录-夜间-设置） */
.nrd-foot {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 12px 16px calc(8px + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid var(--nrd-line);
  background: var(--nrd-bg);
  z-index: 12;
  transform: translateY(100%);
  opacity: 0;
  pointer-events: none;
  transition: transform .22s cubic-bezier(.22, .61, .36, 1), opacity .16s;
}
.nrd.is-chrome .nrd-foot {
  transform: none;
  opacity: 1;
  pointer-events: auto;
}
.nrd-foot-prog {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11.5px;
  color: var(--nrd-sub);
  font-variant-numeric: tabular-nums;
}
.nrd-foot-chap { flex-shrink: 0; }
.nrd-foot-pct { flex-shrink: 0; width: 34px; text-align: right; }
.nrd-foot-row {
  display: flex;
  gap: 10px;
  margin: 12px 0 4px;
}
.nrd-foot-nav {
  flex: 1;
  padding: 9px 0;
  border-radius: 10px;
  border: 1px solid var(--nrd-line);
  background: transparent;
  color: var(--nrd-text);
  font-size: 13px;
  cursor: pointer;
}
.nrd-foot-nav:disabled { opacity: .35; cursor: default; }
.nrd-foot-tools {
  display: flex;
  align-items: center;
  justify-content: space-around;
  margin-top: 6px;
}
.nrd-foot-tools button {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 6px 0;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--nrd-text);
  font-size: 11.5px;
  cursor: pointer;
}
.nrd-foot-tools button:hover { background: rgba(127, 127, 127, .12); }
.nrd-aa { font-size: 16px; line-height: 19px; font-weight: 600; }

/* 底部抽屉（目录 / 设置共用） */
.nrd-sheet {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  max-height: 74vh;
  display: flex;
  flex-direction: column;
  background: var(--nrd-bg);
  border-radius: 18px 18px 0 0;
  box-shadow: 0 -14px 40px -18px rgba(0, 0, 0, .45);
  z-index: 14;
  animation: nrd-sheet-up .2s cubic-bezier(.22, .61, .36, 1);
}
@keyframes nrd-sheet-up { from { transform: translateY(100%); } to { transform: none; } }
.nrd-sheet-head {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 14px 10px;
  border-bottom: 1px solid var(--nrd-line);
}
.nrd-sheet-title { flex: 1; font-size: 14px; font-weight: 500; }
.nrd-sheet-q {
  flex: 1;
  height: 34px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid var(--nrd-line);
  background: transparent;
  color: var(--nrd-text);
  font-size: 13px;
  outline: none;
  font-family: inherit;
}
.nrd-sheet-toc .nrd-toc-list { flex: 1; min-height: 0; overflow-y: auto; padding: 4px 0 20px; }
.nrd-sheet-set {
  padding: 0 18px calc(12px + env(safe-area-inset-bottom, 0px));
  overflow-y: auto;
}
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
/* 遮罩 */
.nrd-mask {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: var(--nrd-bg);
  z-index: 20;
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

/* 目录列表（放在底部抽屉 .nrd-sheet-toc 里） */
.nrd-toc-list { flex: 1; min-height: 0; overflow-y: auto; padding: 4px 0 20px; }
.nrd-toc-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 18px;
  border: 0;
  background: transparent;
  color: var(--nrd-text);
  font-size: 13.5px;
  line-height: 1.5;
  text-align: left;
  cursor: pointer;
}
.nrd-toc-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nrd-toc-idx {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--nrd-sub);
  font-variant-numeric: tabular-nums;
}
.nrd-toc-item:hover { background: rgba(127, 127, 127, .12); }
.nrd-toc-item.active { font-weight: 600; background: rgba(127, 127, 127, .16); }
.nrd-toc-item.active .nrd-toc-label { color: var(--nrd-text); }
.nrd-toc-empty { padding: 20px 18px; font-size: 12.5px; color: var(--nrd-sub); }

/* 设置抽屉内部（外层是 .nrd-sheet-set） */
.nrd-set-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.nrd-set-row:first-of-type { margin-top: 12px; }
.nrd-set-row > span {
  flex-shrink: 0;
  width: 36px;
  font-size: 12.5px;
  color: var(--nrd-sub);
}
/* 自定义背景工具行 */
.nrd-bg-tools {
  flex: 1;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.nrd-bg-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 30px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid var(--nrd-line);
  background: transparent;
  color: var(--nrd-text);
  font-size: 12.5px;
  cursor: pointer;
  overflow: hidden;
}
.nrd-bg-btn:hover { background: rgba(127, 127, 127, .12); }
.nrd-color-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
  width: 100%;
  height: 100%;
  border: 0;
  padding: 0;
}
.nrd-file-hidden { display: none; }
/* 背景色圆点（5 主题 + 自定义色 + 背景图 = 7 个，gap 收紧 + 允许换行） */
.nrd-dots {
  flex: 1;
  display: flex;
  gap: 9px;
  flex-wrap: wrap;
}
.nrd-dot {
  width: 24px;
  height: 24px;
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
/* 字体 8 档：横向滑动展示（v2.46.285，夜星给的方案）。
   🔴 必须用双类提高特异性 —— `.nrd-seg button{flex:1}` 是 (0,1,1)，
   单类写法 `.nrd-seg-fonts button` 也是 (0,1,1) 且定义在前，会被它压回去，
   表现就是 8 个按钮挤成一行还被面板裁掉。 */
.nrd-seg.nrd-seg-fonts {
  flex-wrap: nowrap;
  overflow-x: auto;
  overflow-y: hidden;
  gap: 6px;
  padding-bottom: 4px;
  scrollbar-width: thin;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior-x: contain;
}
.nrd-seg.nrd-seg-fonts button {
  flex: 0 0 auto;          /* 不被压缩，宽度按文字撑开 */
  min-width: 52px;
  padding: 7px 11px;
  white-space: nowrap;
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
/* 搜索抽屉（底部）：宽度交给 .nrd-sheet，这里只调内部间距 */
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
