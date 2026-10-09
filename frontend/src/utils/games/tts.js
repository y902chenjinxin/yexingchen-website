/** 语音报牌（v2.46.26，夜星：①「不要」没合成音 ②合成音怪异，参考腾讯棋牌优化）：
 *  Web Speech API（speechSynthesis）播中文牌面，如「八万」「三个二带一对五」。
 *  腾讯棋牌是真人多台词录音，合成音做不到，优化三板斧：
 *  - 选声打分：优先 Windows/macOS 的在线自然音（Xiaoxiao/Yunxi/Natural），
 *    而不是默认机械音（Huihui/Kangkang），这是「怪异」的最大来源；
 *  - 文案口语化：组件侧用「对五」而非「一对五」，逗号断句让引擎自然停顿；
 *  - 「不要」随机台词池（要不起/不要/过），像真人报牌不是复读机。
 *  跟随 sfx.js 的静音开关（同一个 localStorage 键）；不可用全 try/catch 静默降级。
 */
const MUTE_KEY = 'xuanhuang_game_muted'

let cachedVoice = null
let voicePicked = false

/** 给候选语音打分：zh 语音起步，自然音/线上音加分，非 zh 直接淘汰 */
function scoreVoice(v) {
  const lang = (v.lang || '').toLowerCase()
  if (lang === 'zh-cn') var base = 10
  else if (lang.startsWith('zh')) base = 5
  else return -1
  const name = v.name || ''
  let s = base
  // Microsoft 在线自然音（Xiaoxiao/Yunxi/Yunyang…）是中文 TTS 质量第一梯队
  if (/xiaoxiao|yunxi|yunyang|xiaoyi|yunfeng|xiaochen|yunhao|xiaomo/i.test(name)) s += 8
  if (/natural/i.test(name)) s += 6
  if (v.localService) s += 2
  // 降权已知的机械音（Windows 老默认）
  if (/huihui|kangkang|tingting|yaoyao/i.test(name)) s -= 2
  return s
}

function pickVoice() {
  if (voicePicked) return cachedVoice
  voicePicked = true
  try {
    const vs = window.speechSynthesis?.getVoices?.() || []
    let best = null
    let bestScore = -1
    for (const v of vs) {
      const s = scoreVoice(v)
      if (s > bestScore) { bestScore = s; best = v }
    }
    cachedVoice = bestScore >= 0 ? best : null
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
    u.rate = 1.1          // 1.2 压音节发赶，1.1 接近真人报牌语速
    u.pitch = 1
    u.volume = 0.9
    const v = pickVoice()
    if (v) u.voice = v
    synth.speak(u)
  } catch { /* 无 TTS 环境（部分 WebView）静默 */ }
}

/** 「不要」随机台词池（腾讯棋牌式：真人报牌是一人多台词，不是复读机） */
const PASS_LINES = ['要不起', '不要', '过']
export function speakPass() {
  speak(PASS_LINES[Math.floor(Math.random() * PASS_LINES.length)])
}

/** 麻将牌面 → 口播文本：「八万」「红中」。直接复用各组件的 tileText 亦可，
 *  这里提供数字转中文的规范写法（「8万」TTS 会读「八万」，但「1条」可能读「一条」
 *  或「幺条」不确定，统一转成中文数字更稳）。 */
const CN_NUM = { 1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九' }
const SUIT_CN = { m: '万', s: '条', p: '筒' }
const HONOR_CN = { 1: '红中', 2: '发财', 3: '白板' }

export function tileSpeech(t) {
  if (!t) return ''
  if (t.suit === 'z') return HONOR_CN[t.rank] || `${t.rank}字`
  return `${CN_NUM[t.rank] || t.rank}${SUIT_CN[t.suit] || t.suit}`
}
