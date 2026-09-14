import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * 音频播放控制核心：管理单一 <audio> 实例，处理「点播 / 暂停 / 进度 / 音量」。
 * 不感知「BGM」业务语义——BGM 库与选曲由 useBgmLibraryStore 管理（它调用本 store 触发播放）。
 */
export const usePlayerStore = defineStore('player', () => {
  const audio = new Audio()
  audio.preload = 'auto'

  const mode = ref('idle')            // 'idle' | 'bgm' | 'playlist'
  const curItem = ref(null)           // 当前播放曲目
  const isPlaying = ref(false)
  const volume = ref(Number(localStorage.getItem('bgm_volume') ?? 0.3))
  const rejectedOnce = ref(false)
  const shows = computed(() => mode.value === 'playlist' && !!curItem.value)

  audio.volume = volume.value

  // 硬停：清空 src 并 load() 强制中止旧音频的网络流，避免切换时新老两条流重叠
  function hardStop() {
    try {
      audio.pause()
      audio.src = ''
      audio.removeAttribute('src')
      audio.load()
    } catch { /* 忽略瞬时错误 */ }
  }

  // 切换音源前先硬停旧流，确保任意时刻只有一条音频流存活
  function switchSource(url, loop) {
    hardStop()
    audio.loop = loop
    if (url) {
      audio.src = url
      audio.load()
    }
  }

  // 解析播放 URL：default 曲 / 上传曲目 / 外部链接
  function resolveUrl(item) {
    if (!item) return ''
    if (item.id === 'default' || item.is_default) return '/api/music/default/stream'
    return `/api/music/${item.id}/stream`
  }

  // 播放序号：仅最后一次触发的播放生效，丢弃旧的过期回调，杜绝竞态叠音
  let playSeq = 0

  // 自动播放被浏览器拦截时的恢复句柄：注册一次性 pointerdown，用户首次点击页面即自动拉起 BGM
  let resumeHandler = null

  audio.addEventListener('playing', () => { isPlaying.value = true })
  audio.addEventListener('pause', () => { isPlaying.value = false })
  audio.addEventListener('ended', () => {
    isPlaying.value = false
    // 点播结束：自动恢复背景 BGM
    if (mode.value === 'playlist') {
      mode.value = 'idle'
      playBgm()
    }
  })
  audio.addEventListener('error', () => {
    isPlaying.value = false
  })

  // 自动播放被拦后：注册一次性 pointerdown，用户首次点击页面即恢复播放 BGM（借用了用户手势）
  function armResume() {
    if (audio.paused) {
      audio.play().then(() => { rejectedOnce.value = false }).catch(() => {
        if (resumeHandler) window.removeEventListener('pointerdown', resumeHandler)
        resumeHandler = () => playBgm()
        window.addEventListener('pointerdown', resumeHandler, { once: true })
      })
    }
  }


  // 点播曲目：硬停背景，播该曲（仅播一次，不循环）
  function playItem(item) {
    const url = resolveUrl(item)
    curItem.value = item
    mode.value = 'playlist'
    hardStop()
    audio.loop = false
    audio.volume = volume.value
    if (url) {
      audio.src = url
      audio.load()
    }
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
    hardStop()
    isPlaying.value = false
    mode.value = 'idle'
    if (bgmUrl.value) playBgm()
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

  // ---------- 进度 ----------
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

  // 内部维护 BGM 流地址；由 useBgmLibraryStore 同步
  const bgmUrl = ref('')
  function setBgmUrl(url) { bgmUrl.value = url || '' }
  function playBgm(url) {
    if (url) bgmUrl.value = url
    if (!bgmUrl.value) return
    const seq = ++playSeq
    curItem.value = curItem.value || { id: 'default', title: '玄黄古筝 · 默认背景', artist: '系统', is_default: true }
    mode.value = 'bgm'
    switchSource(bgmUrl.value, true)
    audio.volume = volume.value
    if (seq === playSeq) {
      audio.play().then(() => {
        if (seq === playSeq) rejectedOnce.value = false
      }).catch(() => {
        rejectedOnce.value = true
        armResume()
      })
    }
  }
  return {
    audio, mode, curItem, isPlaying, volume, shows, progress, duration, rejectedOnce, bgmUrl,
    hardStop, switchSource, resolveUrl, armResume, playBgm, setBgmUrl,
    playItem, togglePlay, stopAndHide, setVolume, toggleMute,
    seek, seekByRatio,
    get playing() { return isPlaying.value },
  }
})
