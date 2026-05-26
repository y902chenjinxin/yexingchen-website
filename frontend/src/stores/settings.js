import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getBgMusic } from '@/api/settings'

export const useSettingsStore = defineStore('settings', () => {
  const bgMusicUrl = ref('')
  const musicPlaying = ref(false)

  async function fetchBgMusic() {
    try {
      const res = await getBgMusic()
      bgMusicUrl.value = res.data.bg_music
    } catch {
      bgMusicUrl.value = '/music/default-bg.mp3'
    }
  }

  function toggleMusic() {
    musicPlaying.value = !musicPlaying.value
  }

  return { bgMusicUrl, musicPlaying, fetchBgMusic, toggleMusic }
})