import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getBgMusic, updateBgMusic } from '@/api/settings'

export const useSettingsStore = defineStore('settings', () => {
  const bgMusicUrl = ref('')
  const currentBgmId = ref('')
  const musicPlaying = ref(false)

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
      bgMusicUrl.value = '/music/default-bg.mp3'
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