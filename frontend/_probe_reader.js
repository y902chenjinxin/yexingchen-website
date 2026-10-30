import { createApp, h } from 'vue'
import { createPinia } from 'pinia'
import NovelReader from '@/components/novel/NovelReader.vue'

const novel = {
  id: 999,
  title: '探针测试书',
  original_filename: 'probe.txt',
  progress_percent: 0,
  progress_chapter: '',
}

const app = createApp({
  render: () => h(NovelReader, { novel }),
})
app.use(createPinia())
app.mount('#probe-root')

// 暴露给 playwright 判定
window.__probeReady = true
