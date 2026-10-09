/** 语音报牌（v2.46.24，夜星：「不是音效，而是实际报实际出的牌的内容」）：
 *  Web Speech API（speechSynthesis）播中文牌面，如「八万」「三个二带一对五」。
 *  - 跟随 sfx.js 的静音开关（同一个 localStorage 键），静音时不播；
 *  - 引擎不可用 / 无中文语音时静默降级（try/catch 全包，绝不影响对局）；
 *  - 新播报打断上一条（cancel 后 speak），避免连打时播报堆积。
 */
const MUTE_KEY = 'xuanhuang_game_muted'

let cachedVoice = null
let voicePicked = false

function pickVoice() {
  if (voicePicked) return cachedVoice
  voicePicked = true
  try {
    const vs = window.speechSynthesis?.getVoices?.() || []
    // 优先 zh-CN 本地语音（延迟低），退而求其次任何 zh 语音
    cachedVoice = vs.find(v => v.lang?.toLowerCase() === 'zh-cn')
      || vs.find(v => v.lang?.toLowerCase().startsWith('zh')) || null
  } catch { cachedVoice = null }
  return cachedVoice
}

// 语音列表异步加载：首条播报可能拿不到语音，监听一次刷新缓存
if (typeof window !== 'undefined' && window.speechSynthesis?.addEventListener) {
  try {
    window.speechSynthesis.addEventListener('voiceschanged', () => {
      voicePicked = false
      pickVoice()
    })
  } catch { /* 老引擎忽略 */ }
}

export function speak(text) {
  if (!text) return
  try {
    if (localStorage.getItem(MUTE_KEY) === '1') return
    const synth = window.speechSynthesis
    if (!synth) return
    synth.cancel()
    const u = new SpeechSynthesisUtterance(String(text))
    u.lang = 'zh-CN'
    u.rate = 1.2          // 稍快：对局节奏里报牌要跟手
    u.pitch = 1
    u.volume = 0.9
    const v = pickVoice()
    if (v) u.voice = v
    synth.speak(u)
  } catch { /* 无 TTS 环境（部分 WebView）静默 */ }
}

/** 麻将牌面 → 口播文本：「八万」「红中」。直接复用各组件的 tileText 亦可，
 *  这里提供数字转中文的规范写法（「8万」TTS 会读「八万」，但「1条」可能读「一条」
 *  或「幺条」不确定，统一转成中文数字更稳）。 */
const CN_NUM = { 1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九' }
const SUIT_CN = { m: '万', s: '条', p: '筒' }
const HONOR_CN = { 1: '红中', 2: '发财', 3: '白板', 4: '东风', 5: '南风', 6: '西风', 7: '北风' }

export function tileSpeech(t) {
  if (!t) return ''
  if (t.suit === 'z') return HONOR_CN[t.rank] || `${t.rank}字`
  return `${CN_NUM[t.rank] || t.rank}${SUIT_CN[t.suit] || t.suit}`
}
