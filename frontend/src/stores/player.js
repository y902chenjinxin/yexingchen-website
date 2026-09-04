import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getBgmChoice, updateBgmChoice } from '@/api/settings'
import { getMusicList } from '@/api/music'

// 单一音频中枢：统一管理「背景 BGM」与「点播曲目」的播放/暂停/进度/音量。
// 规则：背景与点播互斥——点播时暂停背景 BGM，离开点播恢复。
export const usePlayerStore = defineStore('player', () => {
  const audio = new Audio()
  audio.preload = 'auto'

  const mode = ref('idle')            // 'idle' | 'bgm' | 'playlist'
  const curItem = ref(null)           // 当前播放曲目 {id,title,artist,url}
  const bgmChoiceId = ref('default')  // 用户选定的背景曲 (default | id)
  const bgmUrl = ref('')              // 已解析的背景 BGM 流地址
  const isPlaying = ref(false)
  const volume = ref(Number(localStorage.getItem('bgm_volume') ?? 0.3))
  const rejectedOnce = ref(false)

  // 播放条显示：仅点播曲目时展示；背景 BGM 不展示
  const shows = computed(() => mode.value === 'playlist' && !!curItem.value)

  audio.volume = volume.value
  audio.addEventListener('playing', () => { isPlaying.value = true })
  audio.addEventListener('pause', () => { isPlaying.value = false })
  audio.addEventListener('ended', () => {
    isPlaying.value = false
    // 点播自然播完后恢复背景 BGM
    if (mode.value === 'playlist' && bgmUrl.value) resumeBgm()
  })

  // 播放背景 BGM（loop）；浏览器自动播放被拦时，等待首次用户交互再恢复
  function playBgm() {
    if (!bgmUrl.value) return
    mode.value = 'bgm'
    audio.src = bgmUrl.value
    audio.loop = true
    audio.volume = volume.value
    audio.play().then(() => { rejectedOnce.value = false }).catch(() => {
      rejectedOnce.value = true
      const resume = () => playBgm()
      window.removeEventListener('pointerdown', resume)
      window.addEventListener('pointerdown', resume, { once: true })
    })
  }

  // ---------- 曲目 url 解析 ----------
  function resolveUrl(item) {
    if (!item) return ''
    // 列表项的 file_path 后端已返回可播 url；default 曲是 /api/music/default/stream
    if (item.id === 'default' || item.is_default) return '/api/music/default/stream'
    return `/api/music/${item.id}/stream`
  }

  async function fetchMusicLibrary(force = false) {
    if (!force && musicLibrary.value.length) return
    try {
      const res = await getMusicList({ size: 200 })
      const list = res?.data?.list || []
      const def = list.find(it => it.is_default) || {
        id: 'default', title: '玄黄古筝 · 默认背景', artist: '系统', is_default: true
      }
      const uploads = list.filter(it => !it.is_default)
      musicLibrary.value = [def, ...uploads]
    } catch {
      musicLibrary.value = [{ id: 'default', title: '玄黄古筝 · 默认背景', artist: '系统', is_default: true }]
    }
  }
  const musicLibrary = ref([])

  // ---------- 背景 BGM ----------
  async function loadBgmLibrary() {
    await fetchMusicLibrary()
  }

  async function initBgm() {
    await fetchMusicLibrary()
    await refreshBgmChoice()
    playBgm()
  }

  async function refreshBgmChoice() {
    try {
      const res = await getBgmChoice()
      bgmChoiceId.value = res?.data?.bgm_music_id ?? 'default'
    } catch {
      bgmChoiceId.value = 'default'
    }
    // 用实际选择的曲目 url 播放
    const target = musicLibrary.value.find(it => String(it.id) === String(bgmChoiceId.value))
    const url = target ? resolveUrl(target) : '/api/music/default/stream'
    bgmUrl.value = url
    curItem.value = target || { id: 'default', title: '玄黄古筝 · 默认背景', artist: '系统', is_default: true }
    return url
  }

  async function setBackground(item, autoplay = true) {
    await fetchMusicLibrary(true)
    const target = item || musicLibrary.value.find(it => String(it.id) === String(bgmChoiceId.value))
      || musicLibrary.value[0]
    bgmChoiceId.value = String(target.id)
    curItem.value = target
    bgmUrl.value = resolveUrl(target)
    mode.value = 'bgm'
    // 持久化到后端
    try { await updateBgmChoice({ bgm_music_id: String(target.id) }) } catch { /* 静默 */ }
    if (autoplay) playBgm()
  }

  // 切回后台背景（点播结束后恢复）
  function resumeBgm() {
    if (bgmUrl.value) playBgm()
  }

  // ---------- 点播曲目 ----------
  function playItem(item) {
    // 点播：暂停背景，播该曲（仅播一次，不循环）
    const url = resolveUrl(item)
    curItem.value = item
    mode.value = 'playlist'
    audio.src = url
    audio.loop = false
    audio.volume = volume.value
    audio.play().catch(() => {})
  }

  function togglePlay() {
    if (audio.paused) {
      audio.play().catch(() => {})
    } else {
      audio.pause()
    }
  }

  function stopAndHide() {
    audio.pause()
    isPlaying.value = false
    mode.value = 'idle'
  }

  // ---------- 音量 ----------
  function setVolume(v) {
    v = Math.max(0, Math.min(1, v))
    volume.value = v
    audio.volume = v
    localStorage.setItem('bgm_volume', String(v))
  }

  function toggleMute() {
    setVolume(volume.value > 0 ? 0 : 0.3)
  }

  const progress = ref(0)
  const duration = ref(0)
  audio.addEventListener('timeupdate', () => {
    progress.value = audio.currentTime
    duration.value = audio.duration || 0
  })

  function seek(sec) {
    if (Number.isFinite(sec)) audio.currentTime = sec
  }

  function seekByRatio(r) {
    if (audio.duration) audio.currentTime = r * audio.duration
  }

  return {
    audio, mode, curItem, bgmChoiceId, bgmUrl, isPlaying, volume,
    musicLibrary, shows, progress, duration, rejectedOnce,
    initBgm, loadBgmLibrary, refreshBgmChoice, setBackground, resumeBgm,
    playItem, togglePlay, stopAndHide, setVolume, toggleMute, seek, seekByRatio,
    get playing() { return isPlaying.value }
  }
})