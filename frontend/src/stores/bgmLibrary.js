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

  const musicLibrary = ref([])            // [{ id, title, artist }]
  const bgmChoiceId = ref('')               // 用户选定的 BGM id；'' = 未选择（不再替用户默认选一首）
  const bgmUrl = ref('')                    // 已解析的 BGM 流地址

  // ---------- 库加载 ----------
  // 内置古筝现在是音乐库里的一条**真实记录**（迁移 z6a7b8c9d0e1 播种），
  // 不再由列表接口合成，所以这里也不再给它开小灶。
  async function fetchMusicLibrary(force = false) {
    if (!force && musicLibrary.value.length) return
    try {
      const res = await getMusicList({ size: 200 })
      musicLibrary.value = res?.data?.list || []
    } catch {
      musicLibrary.value = []
    }
  }

  async function loadBgmLibrary() {
    await fetchMusicLibrary()
  }

  // ---------- 选 BGM / 自动播放 ----------
  async function refreshBgmChoice() {
    try {
      const res = await getBgmChoice()
      bgmChoiceId.value = res?.data?.bgm_music_id ?? ''
    } catch {
      bgmChoiceId.value = ''
    }
    const target = musicLibrary.value.find(
      it => String(it.id) === String(bgmChoiceId.value),
    )
    // 没选过（或所选曲已被删）就没有可播地址 —— 不再回落到「内置默认曲」
    bgmUrl.value = target ? player.resolveUrl(target) : ''
    return bgmUrl.value
  }

  /**
   * 初始化：只加载音乐库 + 恢复「上次选的是哪首」，**绝不自动起播**。
   *
   * 需求是「记住选择，但进站不自动响」，所以要同时守住两件事：
   *   1. 不调用 playBgm()
   *   2. 不武装 player 的 pointerdown 恢复句柄 —— 否则进站后随便点一下就响，
   *      那只是换了个时机的自动播放
   * 真正起播只发生在用户的显式动作上：顶栏开关 / 曲目下拉选曲 / 播放条播放键。
   */
  async function initBgm() {
    await fetchMusicLibrary()
    await refreshBgmChoice()
    player.setBgmUrl(bgmUrl.value)
  }

  /**
   * 切换背景曲。
   * @param item     目标曲目；传 null 表示「从当前库里重新挑一首」
   * @param autoplay 是否立即起播。删除当前背景曲时传 false——只重新指向新曲，
   *                 不该因为一次删除操作突然放起音乐。
   */
  async function setBackground(item, autoplay = true) {
    // 先立即停掉当前音轨，避免下方 await 期间旧歌继续播放与换曲后叠加
    player.hardStop()
    await fetchMusicLibrary(true)

    // 传 null 表示「重新解析当前选择」——当前曲有可能已经被删了
    const target = item
      || musicLibrary.value.find(it => String(it.id) === String(bgmChoiceId.value))
    if (!target) {
      // 选择已失效且没有候补：归零，不再自动挑一首顶上
      bgmChoiceId.value = ''
      bgmUrl.value = ''
      player.setBgmUrl('')
      try { await updateBgmChoice({ bgm_music_id: '' }) } catch { /* 静默 */ }
      return null
    }

    bgmChoiceId.value = String(target.id)
    bgmUrl.value = player.resolveUrl(target)
    player.setBgmUrl(bgmUrl.value)
    // 触发播放（依赖 player 内部 curItem/mode 同步）
    if (autoplay) player.playBgm(bgmUrl.value)
    try { await updateBgmChoice({ bgm_music_id: String(target.id) }) } catch { /* 静默 */ }
    return target
  }

  return {
    musicLibrary, bgmChoiceId, bgmUrl,
    fetchMusicLibrary, loadBgmLibrary, refreshBgmChoice, initBgm, setBackground,
  }
})
