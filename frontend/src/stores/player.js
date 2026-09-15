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
  // BGM 总开关：关闭时彻底停播且不再自动拉起（含自动播放被拦后的恢复句柄）；
  // 状态持久化到 localStorage，下次进站保持用户上次的选择。
  const bgmEnabled = ref(localStorage.getItem('bgm_enabled') !== '0')
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

  // 自动播放被浏览器拦截时的恢复句柄：在用户任意一次指针按下（pointerdown）时拉起 BGM。
  // 采用持久监听（非 once），若某次点击仍被拦则保留句柄，直到真正出声成功为止。
  let resumeHandler = null
  function armResume() {
    if (resumeHandler) return
    resumeHandler = () => {
      // 总开关关闭：立刻撤销句柄，杜绝「关掉后随便点一下又响起来」
      if (!bgmEnabled.value) { disarmResume(); return }
      const seq = ++playSeq
      if (!bgmUrl.value) return                 // 源地址尚未就绪，保留句柄等待
      mode.value = 'bgm'
      switchSource(bgmUrl.value, true)
      audio.volume = volume.value
      if (seq === playSeq) {
        audio.play().then(() => {
          if (seq === playSeq) { rejectedOnce.value = false; disarmResume() }
        }).catch(() => {                       // 仍被拦，保留句柄供下一次点按恢复
        })
      }
    }
    window.addEventListener('pointerdown', resumeHandler)
  }
  function disarmResume() {
    if (resumeHandler) { window.removeEventListener('pointerdown', resumeHandler); resumeHandler = null }
  }

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

  // ---------- BGM 总开关 ----------
  // 关闭：撤销自动恢复句柄 + 彻底停播并释放网络流（仅作用于 BGM，不影响点播中的曲目）
  // 开启：按当前偏好源立即恢复播放（被浏览器拦截时自动武装恢复句柄）
  function setBgmEnabled(on) {
    bgmEnabled.value = !!on
    localStorage.setItem('bgm_enabled', bgmEnabled.value ? '1' : '0')
    if (!bgmEnabled.value) {
      disarmResume()
      if (mode.value === 'bgm') {
        hardStop()
        isPlaying.value = false
        mode.value = 'idle'
        curItem.value = null
      }
      return
    }
    playBgm()
  }

  function toggleBgm() {
    setBgmEnabled(!bgmEnabled.value)
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
    if (!bgmEnabled.value) return                // 总开关关闭：任何来源的自动播放请求一律拦下
    if (url) bgmUrl.value = url
    if (!bgmUrl.value) return
    const seq = ++playSeq
    mode.value = 'bgm'
    switchSource(bgmUrl.value, true)
    audio.volume = volume.value
    if (seq === playSeq) {
      audio.play().then(() => {
        if (seq === playSeq) { rejectedOnce.value = false; disarmResume() }
      }).catch(() => {
        rejectedOnce.value = true
        armResume()
      })
    }
  }
  return {
    audio, mode, curItem, isPlaying, volume, shows, progress, duration, rejectedOnce, bgmUrl,
    bgmEnabled,
    hardStop, switchSource, resolveUrl, armResume, disarmResume, playBgm, setBgmUrl,
    playItem, togglePlay, stopAndHide, setVolume, toggleMute,
    setBgmEnabled, toggleBgm,
    seek, seekByRatio,
    get playing() { return isPlaying.value },
  }
})
