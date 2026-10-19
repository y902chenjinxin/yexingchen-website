<template>
  <!-- v2.46.120 小说下载工具（夜星：支持番茄/起点，带精校）
       流程：粘贴目录页 URL → 识别站点拉目录 → 选范围抓正文（单批≤60，限速）
       → 规则精校（去广告噪声行/规范化/段落规整）→ 导出 TXT/Markdown。
       合规：仅公开免费章节，付费/登录章节标注跳过，不破解任何保护。 -->
  <IslandInnerBase type="tool" title="小说下载" subtitle="番茄 / 起点 · 目录抓取 · 精校导出">
    <div class="ndl">
      <div class="ndl-row">
        <el-input
          v-model="url" placeholder="粘贴小说目录页地址（如 https://fanqienovel.com/page/xxxx 或 https://www.qidian.com/book/xxxx/）"
          clearable @keyup.enter="loadOutline"
        />
        <el-button type="primary" :loading="loadingOutline" @click="loadOutline">解析目录</el-button>
      </div>
      <p class="ndl-note">仅抓公开免费章节；付费/需登录章节自动标注跳过（不做绕过）。请遵守站点规则，文件仅限个人离线阅读。</p>

      <el-alert v-if="outlineErr" :title="outlineErr" type="error" :closable="false" show-icon />

      <template v-if="outline">
        <div class="ndl-book">
          <b>{{ outline.title }}</b>
          <span>{{ outline.author || '未知作者' }}</span>
          <span>共 {{ outline.chapters.length }} 章 · {{ sourceLabel }}</span>
        </div>

        <div class="ndl-row ndl-range">
          <span class="ndl-label">章节范围</span>
          <el-input-number v-model="from" :min="1" :max="outline.chapters.length" />
          <span class="ndl-dash">—</span>
          <el-input-number v-model="to" :min="1" :max="outline.chapters.length" />
          <el-checkbox v-model="polish" border size="small">精校（去广告/规范排版）</el-checkbox>
          <el-button type="primary" :loading="loadingCh" @click="fetchChapters">
            {{ loadingCh ? `抓取中 ${done}/${rangeLen}` : `抓取 ${rangeLen} 章` }}
          </el-button>
        </div>
        <p class="ndl-hint">单批最多 60 章（对目标站友好限速），长书请分批；抓完的章节在本页累计，随时导出。</p>

        <el-alert v-if="chErr" :title="chErr" type="error" :closable="false" show-icon />

        <template v-if="chapters.length">
          <div class="ndl-stat">
            <span>已抓 <b>{{ chapters.length }}</b> 章</span>
            <span class="ok">成功 {{ okCount }}</span>
            <span class="bad">付费/失败 {{ payCount }}</span>
            <span class="ndl-ops">
              <el-button size="small" type="primary" plain :disabled="!okCount" @click="exportBook('txt')">导出 TXT</el-button>
              <el-button size="small" plain :disabled="!okCount" @click="exportBook('md')">导出 Markdown</el-button>
              <el-button size="small" text type="danger" @click="chapters = []">清空</el-button>
            </span>
          </div>

          <div class="ndl-list">
            <div v-for="(ch, i) in chapters" :key="i" class="ndl-ch" :class="{ pay: ch.paywalled || !ch.content }">
              <b>{{ i + 1 }}. {{ ch.title || '未命名' }}</b>
              <span v-if="ch.paywalled || !ch.content" class="ndl-ch-note">{{ ch.note || '未取到正文' }}</span>
              <span v-else>{{ ch.content.length }} 字</span>
            </div>
          </div>
        </template>
      </template>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { crawlerApi } from '@/api/crawler'

defineOptions({ name: 'NovelDlToolView' })

const url = ref('')
const loadingOutline = ref(false)
const outlineErr = ref('')
const outline = ref(null)

const from = ref(1)
const to = ref(1)
const polish = ref(true)
const loadingCh = ref(false)
const chErr = ref('')
const chapters = ref([])
const done = ref(0)

const sourceLabel = computed(() => outline.value?.source === 'fanqie' ? '番茄' : outline.value?.source === 'qidian' ? '起点' : '未知')
const rangeLen = computed(() => Math.max(0, Math.min(to.value, outline.value?.chapters.length || 1) - from.value + 1))
const okCount = computed(() => chapters.value.filter((c) => c.content).length)
const payCount = computed(() => chapters.value.length - okCount.value)

async function loadOutline() {
  if (!url.value.trim()) { ElMessage.warning('先粘贴目录页地址'); return }
  loadingOutline.value = true
  outlineErr.value = ''
  outline.value = null
  chapters.value = []
  try {
    const res = await crawlerApi.novelOutline(url.value.trim())
    if (res.data?.code === 1) { outlineErr.value = res.data.msg || '解析失败'; return }
    outline.value = res.data?.data
    if (outline.value) {
      to.value = Math.min(60, outline.value.chapters.length)
      from.value = 1
      if (!outline.value.chapters.length) outlineErr.value = '目录解析成功但未取到章节列表（站点结构可能变化）'
    }
  } catch (e) {
    outlineErr.value = e?.response?.data?.msg || e?.message || '请求失败'
  } finally { loadingOutline.value = false }
}

async function fetchChapters() {
  const list = outline.value.chapters.slice(from.value - 1, to.value)
  if (!list.length) return
  loadingCh.value = true
  chErr.value = ''
  done.value = 0
  try {
    // 单批 ≤60 后端已限；这里直接一把请求，后端限速逐章抓
    const res = await crawlerApi.novelChapters(
      { source: outline.value.source, items: list, polish: polish.value })
    if (res.data?.code === 1) { chErr.value = res.data.msg; return }
    const got = res.data?.data?.list || []
    chapters.value.push(...got)
    done.value = got.length
    ElMessage.success(`抓取完成：成功 ${res.data?.data?.ok ?? 0} / ${got.length}`)
  } catch (e) {
    chErr.value = e?.response?.data?.msg || e?.message || '抓取请求失败'
  } finally { loadingCh.value = false }
}

async function exportBook(fmt) {
  try {
    const res = await crawlerApi.novelExport(
      { title: outline.value.title, author: outline.value.author, chapters: chapters.value, fmt })
    const blob = new Blob([res.data])
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${outline.value.title}.${fmt}`
    a.click()
    URL.revokeObjectURL(a.href)
    ElMessage.success('已导出')
  } catch (e) {
    ElMessage.error(e?.message || '导出失败')
  }
}
</script>

<style scoped>
.ndl { display: flex; flex-direction: column; gap: 14px; }
.ndl-row { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.ndl-row .el-input { flex: 1; min-width: 280px; }
.ndl-note, .ndl-hint { margin: 0; font-size: 12px; color: var(--ls-text-3, var(--color-text-secondary)); line-height: 1.7; }
.ndl-book { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; font-size: 13px; color: var(--color-text-secondary); }
.ndl-book b { font-size: 17px; color: var(--color-text); }
.ndl-range { padding: 12px 14px; border-radius: 12px; background: var(--dp-surface2, rgba(127, 168, 163, .07)); border: 1px solid var(--dp-line, var(--ls-line)); }
.ndl-label { font-size: 13px; color: var(--color-text-secondary); }
.ndl-dash { color: var(--color-text-secondary); }
.ndl-stat {
  display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
  font-size: 13px; color: var(--color-text-secondary);
}
.ndl-stat b { color: var(--color-text); }
.ndl-stat .ok { color: #3fae7a; }
.ndl-stat .bad { color: var(--dp-danger, #fb7185); }
.ndl-ops { margin-left: auto; display: flex; gap: 8px; }
.ndl-list {
  display: flex; flex-direction: column; gap: 6px; max-height: 420px; overflow-y: auto;
  padding: 10px 12px; border-radius: 12px;
  background: var(--dp-surface2, rgba(127, 168, 163, .07)); border: 1px solid var(--dp-line, var(--ls-line));
}
.ndl-ch {
  display: flex; align-items: baseline; gap: 10px; font-size: 12.5px;
  padding: 6px 8px; border-radius: 8px; color: var(--color-text);
}
.ndl-ch b { font-weight: 500; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ndl-ch span { flex: none; color: var(--color-text-secondary); font-size: 11.5px; }
.ndl-ch.pay b { color: var(--color-text-secondary); }
.ndl-ch.pay span { color: var(--dp-danger, #fb7185); }
</style>
