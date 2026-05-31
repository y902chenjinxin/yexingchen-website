import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getBgMusic } from '@/api/settings'

export const useSettingsStore = defineStore('settings', () => {
  const bgMusicUrl = ref('')
  const currentBgmId = ref('bamboo_flute') // 默认兰亭序
  const musicPlaying = ref(true) // 默认开启自动播放

  async function fetchBgMusic() {
    try {
      const res = await getBgMusic()
      let url = res.data.bg_music
      // 如果是 /uploads/bgm/xxx.mp3，转换为流式接口（自动检测真实格式）
      const match = url.match(/\/uploads\/bgm\/([^/]+)\.mp3$/)
      if (match) {
        const bgmId = match[1]
        currentBgmId.value = bgmId
        url = `/api/settings/bg_music/stream/${bgmId}`
      }
      bgMusicUrl.value = url
    } catch {
      // 默认使用兰亭序
      currentBgmId.value = 'bamboo_flute'
      bgMusicUrl.value = '/api/settings/bg_music/stream/bamboo_flute'
    }
  }

  async function saveBgMusicId(bgmId) {
    currentBgmId.value = bgmId
    // 可选：通知后端保存选择
  }

  function toggleMusic() {
    musicPlaying.value = !musicPlaying.value
  }

  return { bgMusicUrl, currentBgmId, musicPlaying, fetchBgMusic, toggleMusic, saveBgMusicId }
})