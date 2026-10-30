<template>
  <!-- 阅读器路由页（v2.46.207）
       之前阅读器只是 NovelView 里的一个 v-if 覆盖层，不参与路由 ——
       手机上按系统返回键走的是浏览器历史，会直接退出整个 /novel 页面，
       而 body.nrd-open 把侧栏隐藏了，退回的页面就成了"空白且回不去"。

       改成独立路由后：系统返回键 = 路由后退 = 回到 /novel 列表，符合直觉。 -->
  <!-- 🔴 必须有真实单根元素（v2.46.219 修空白页）。
       之前是三个 v-if 分支并列 = fragment，而 <NovelReader> 本身的根又是 <Teleport>。
       App.vue 的路由 <transition mode="out-in"> 拿不到真实 DOM 元素时，
       离开钩子永不结束 → 新页面永远不进入 → 点返回后整块内容区空白（侧栏正常）。
       Vue 的 transition 要求子组件是「单一真实元素」，Teleport / fragment 都不满足。 -->
  <div class="nrv-root">
    <NovelReader v-if="novel" :novel="novel" @close="close" />
    <div v-else-if="loading" class="nrd-loading-page">正在打开…</div>
    <div v-else class="nrd-loading-page">
      <p>{{ error || '这本书找不到了' }}</p>
      <button type="button" @click="close">返回书架</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import NovelReader from '@/components/novel/NovelReader.vue'
import { prefetchToc, prefetchChapter, guessChapterIndex } from '@/utils/novelPrefetch'

const route = useRoute()
const router = useRouter()
const novel = ref(null)
const loading = ref(true)
const error = ref('')

function close() {
  // 有历史就后退（保留列表的筛选/页码状态），否则回列表
  if (window.history.length > 1) router.back()
  else router.replace({ name: 'Novel' })
}

onMounted(async () => {
  const id = Number(route.params.id)
  if (!id) { error.value = '缺少书籍 ID'; loading.value = false; return }
  // v2.46.294：目录与详情同时发（目录 1000+ 章约 30KB，和详情无依赖），
  // Reader 挂载时直接取，省掉一次串行往返。
  prefetchToc(id)
  // 首章也一起发：本地进度里存着章节下标，不用等目录回来才知道读哪章
  prefetchChapter(id, guessChapterIndex(id))
  try {
    const tk = localStorage.getItem('token') || ''
    const res = await fetch(`/api/novels/${id}`, { headers: { Authorization: `Bearer ${tk}` } })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const j = await res.json()
    const d = j?.data || j
    if (!d || !d.id) throw new Error('空数据')
    novel.value = d
  } catch (e) {
    error.value = `打开失败：${e?.message || '未知错误'}`
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  // 兜底：无论怎么离开这一页，都把沉浸态清干净
  document.body.classList.remove('nrd-open')
})
</script>

<style scoped>
.nrd-loading-page {
  min-height: 60vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  font-size: 14px;
  color: var(--color-text-3, #8b98a8);
}
.nrd-loading-page button {
  padding: 9px 18px;
  border-radius: 9px;
  border: 1px solid currentColor;
  background: transparent;
  color: inherit;
  font-size: 13px;
  cursor: pointer;
}
</style>
