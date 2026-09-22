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
  /* ---------- 播放模式（仅在 playlist 模式下生效） ----------
   *  list    : 列表循环 —— 按顺序播完全部后回到第一首继续循环
   *  single  : 单曲循环 —— 当前曲目结束后重播这一首
   *  shuffle : 随机播放 —— 从队列中随机抽下一首（已播过的短期不再抽，避免反复）
   *  once    : 单曲一次 —— 播完即止，回到 BGM
   * 持久化到 localStorage，便于多端保持
   */
  const PLAY_MODES = ['list', 'single', 'shuffle', 'once']
  const storedPlayMode = localStorage.getItem('xh_play_mode')
  const playMode = ref(PLAY_MODES.includes(storedPlayMode) ? storedPlayMode : 'list')
  /* 播放队列：点播时由调用方传入（通常是 MusicView 当前列表） */
  const queue = ref([])               // [{ id, title, artist, ... }]
  const queueIndex = ref(-1)
  /* shuffle 防重复：记录最近 8 首已播过的 id */
  const shuffleRecent = ref([])
  // BGM 总开关：关闭时彻底停播且不再自动拉起（含自动播放被拦后的恢复句柄）；
  // 状态持久化到 localStorage，下次进站保持用户上次的选择。
  // 默认开启：仅显式关闭过（存 '0'）才停；未设置过统一播放背景音乐，
  // 避免"背景音乐莫名消失"（用户以为丢失）。
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
    // 点播结束：根据播放模式决定下一步
    if (mode.value === 'playlist') {
      handleTrackEnded()
    }
  })
  audio.addEventListener('error', () => {
    isPlaying.value = false
  })


  // 点播曲目：硬停背景，播该曲（loop 由播放模式决定）
  // queueList: 调用方传入当前可选列表（如 MusicView 当前页/搜索结果）；
  //            不传则只播这一首（行为退化为「单曲一次」）
  function playItem(item, queueList = null) {
    if (!item) return
    curItem.value = item
    mode.value = 'playlist'
    // 建立队列
    if (Array.isArray(queueList) && queueList.length) {
      queue.value = queueList.slice()
      // 优先按 id 精确匹配；id 类型不一（数字 / 字符串 'default'）故统一转字符串
      const targetId = String(item.id)
      const idx = queue.value.findIndex(q => String(q.id) === targetId)
      queueIndex.value = idx >= 0 ? idx : 0
    } else {
      queue.value = [item]
      queueIndex.value = 0
    }
    shuffleRecent.value = []
    startCurrent()
  }

  // 实际启动当前 queueIndex 的曲目（不切换队列/索引）。
  // 关键：同步更新 curItem，否则切歌后播放框标题 / 表格高亮仍停留在上一首
  function startCurrent() {
    const item = queue.value[queueIndex.value]
    if (!item) return
    curItem.value = item
    const url = resolveUrl(item)
    hardStop()
    audio.loop = playMode.value === 'single'   // 单曲循环：交给 audio.loop
    audio.volume = volume.value
    if (url) {
      audio.src = url
      audio.load()
    }
    audio.play().catch(() => {})
  }

  // 记录最近播放（用于 shuffle 短期去重）
  function pushRecent(id) {
    const key = String(id)
    shuffleRecent.value = [key, ...shuffleRecent.value.filter(x => x !== key)].slice(0, 8)
  }

  // 选下一首（不含单曲循环那一支；shuffle 时排除最近 8 首）
  function pickNextIndex() {
    const n = queue.value.length
    if (!n) return -1
    if (n === 1) return 0
    if (playMode.value === 'shuffle') {
      const recent = new Set(shuffleRecent.value)
      const candidates = []
      for (let i = 0; i < n; i++) {
        if (i === queueIndex.value) continue
        if (recent.has(String(queue.value[i].id))) continue
        candidates.push(i)
      }
      const pool = candidates.length ? candidates : queue.map((_, i) => i).filter(i => i !== queueIndex.value)
      return pool[Math.floor(Math.random() * pool.length)]
    }
    // 列表循环：到末尾回到 0
    return (queueIndex.value + 1) % n
  }

  function pickPrevIndex() {
    const n = queue.value.length
    if (!n) return -1
    if (n === 1) return 0
    if (playMode.value === 'shuffle') return pickNextIndex()  // shuffle 下上首=再随机一首
    return (queueIndex.value - 1 + n) % n
  }

  function next() {
    if (mode.value !== 'playlist' || !queue.value.length) return
    const idx = pickNextIndex()
    if (idx < 0) return
    queueIndex.value = idx
    pushRecent(queue.value[idx].id)
    startCurrent()
  }

  function prev() {
    // 习惯做法：超过 3 秒按 prev 回到曲首；否则才真正切上一首
    if (audio.currentTime > 3) {
      audio.currentTime = 0
      return
    }
    if (mode.value !== 'playlist' || !queue.value.length) return
    const idx = pickPrevIndex()
    if (idx < 0) return
    queueIndex.value = idx
    pushRecent(queue.value[idx].id)
    startCurrent()
  }

  // 曲目自然结束：根据播放模式决定下一步
  function handleTrackEnded() {
    if (playMode.value === 'single') {
      // audio.loop=true 已经会自己重播；兜底再启动一次
      audio.currentTime = 0
      audio.play().catch(() => {})
      return
    }
    if (playMode.value === 'once') {
      // 播完即止：回到 BGM
      mode.value = 'idle'
      curItem.value = null
      queue.value = []
      queueIndex.value = -1
      playBgm()
      return
    }
    // list / shuffle 都走 next()
    const n = queue.value.length
    if (!n) {
      mode.value = 'idle'
      playBgm()
      return
    }
    next()
  }

  // 切换播放模式：list → single → shuffle → once → list
  function cyclePlayMode() {
    const i = PLAY_MODES.indexOf(playMode.value)
    playMode.value = PLAY_MODES[(i + 1) % PLAY_MODES.length]
    localStorage.setItem('xh_play_mode', playMode.value)
    // 同步 audio.loop
    audio.loop = playMode.value === 'single'
  }

  function setPlayMode(m) {
    if (!PLAY_MODES.includes(m)) return
    playMode.value = m
    localStorage.setItem('xh_play_mode', m)
    audio.loop = m === 'single'
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
    curItem.value = null
    queue.value = []
    queueIndex.value = -1
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
    /* 播放模式 / 队列 */
    playMode, queue, queueIndex, PLAY_MODES,
    next, prev, cyclePlayMode, setPlayMode,
    get playing() { return isPlaying.value },
  }
})
