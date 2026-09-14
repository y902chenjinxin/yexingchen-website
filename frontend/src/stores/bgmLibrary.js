import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getBgmChoice, updateBgmChoice } from '@/api/settings'
import { getMusicList } from '@/api/music'
import { usePlayerStore } from './player'

/**
 * BGM 库与用户偏好：负责「加载音乐库」「选 BGM 曲」「切换 BGM 源」。
 * 播放控制（play/pause/seek/volume）由 usePlayerStore 负责。
 */
export const useBgmLibraryStore = defineStore('bgmLibrary', () => {
  const player = usePlayerStore()

  const musicLibrary = ref([])            // [{ id, title, artist, is_default }]
  const bgmChoiceId = ref('default')        // 用户选定的 BGM id（'default' | music id）
  const bgmUrl = ref('')                    // 已解析的 BGM 流地址

  // ---------- 库加载 ----------
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
      musicLibrary.value = [{
        id: 'default', title: '玄黄古筝 · 默认背景', artist: '系统', is_default: true,
      }]
    }
  }

  async function loadBgmLibrary() {
    await fetchMusicLibrary()
  }

  // ---------- 选 BGM / 自动播放 ----------
  async function refreshBgmChoice() {
    try {
      const res = await getBgmChoice()
      bgmChoiceId.value = res?.data?.bgm_music_id ?? 'default'
    } catch {
      bgmChoiceId.value = 'default'
    }
    const target = musicLibrary.value.find(
      it => String(it.id) === String(bgmChoiceId.value),
    )
    bgmUrl.value = target ? player.resolveUrl(target) : '/api/music/default/stream'
    return bgmUrl.value
  }

  async function initBgm() {
    // 先用默认曲尽快发起播放（贴近首帧/登录手势），避免被自动播放策略彻底拦死；
    // 被拦则由 player 武装持久恢复句柄，任意首次点击即自动拉起。
    if (!player.bgmUrl) player.playBgm('/api/music/default/stream')
    await fetchMusicLibrary()
    await refreshBgmChoice()
    // 偏好源就绪后再用最终地址触发一次（自动播放允许则无缝切到用户所选；被拦则沿用恢复句柄）
    player.playBgm(bgmUrl.value)
  }

  async function setBackground(item, autoplay = true) {
    // 先立即停掉当前音轨，避免下方 await 期间旧歌继续播放与换曲后叠加
    player.hardStop()
    await fetchMusicLibrary(true)
    const target = item
      || musicLibrary.value.find(it => String(it.id) === String(bgmChoiceId.value))
      || musicLibrary.value[0]
    bgmChoiceId.value = String(target.id)
    bgmUrl.value = player.resolveUrl(target)
    player.setBgmUrl(bgmUrl.value)
    // 触发播放（依赖 player 内部 curItem/mode 同步）
    player.playBgm(bgmUrl.value)
    try { await updateBgmChoice({ bgm_music_id: String(target.id) }) } catch { /* 静默 */ }
    return target
  }

  return {
    musicLibrary, bgmChoiceId, bgmUrl,
    fetchMusicLibrary, loadBgmLibrary, refreshBgmChoice, initBgm, setBackground,
  }
})
