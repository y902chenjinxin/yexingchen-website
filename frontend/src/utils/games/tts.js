/** 语音报牌（v2.46.28，夜星：「语速偏慢机械音明显，设计下显得真实一点」）：
 *  Web Speech API（speechSynthesis）播中文牌面，如「八万」「三个二带一对五」。
 *
 *  v2.46.28 真实感四件套（原→新）：
 *  - 语速 1.1 → 1.35 ±3% 抖动 —— 慢速最暴露合成痕迹（音素拉长电子感重），
 *    真人报牌是「快而脆」，快语速下衔接瑕疵反而不易察觉；
 *  - 音调 1 恒定 → 0.94~1.10 每句随机 —— 消「每句同一个调」的复读机感；
 *  - 全场一个声 → 按座位固定分配不同高分语音 —— 四个座位四个声，
 *    像四个人在打牌而不是一台机器在念稿（这是「显得真实」最有效的一招）；
 *  - 掼蛋炸弹文案加「炸！」喊声（腾讯棋牌炸弹有专门语音）。
 *
 *  沿用 v2.46.26 的选声打分（优先 Xiaoxiao/Yunxi/Natural 自然音）与
 *  「不要」随机台词池；跟随静音开关；不可用全 try/catch 静默降级。
 */
const MUTE_KEY = 'xuanhuang_game_muted'

let cachedVoices = null
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

/** 打分排序取前 4 个：座位号取模分配，分数相同按系统返回顺序稳定排列 */
function pickVoices() {
  if (voicePicked) return cachedVoices
  voicePicked = true
  try {
    const vs = (window.speechSynthesis?.getVoices?.() || [])
      .map(v => ({ v, s: scoreVoice(v) }))
      .filter(x => x.s >= 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, 4)
    cachedVoices = vs.map(x => x.v)
  } catch { cachedVoices = [] }
  return cachedVoices
}

// 语音列表异步加载：首条播报可能拿不到语音，监听一次刷新缓存
if (typeof window !== 'undefined' && window.speechSynthesis?.addEventListener) {
  try {
    window.speechSynthesis.addEventListener('voiceschanged', () => {
      voicePicked = false
      pickVoices()
    })
  } catch { /* 老引擎忽略 */ }
}

/**
 * 口播一段文本。
 * @param {string} text 口播内容
 * @param {number|null} seat 座位号 —— 有就按座位分配固定语音（一人一声）；
 *   系统只装了一个中文语音时自然退化为全场同声，不影响功能。
 */
export function speak(text, seat = null) {
  if (!text) return
  try {
    if (localStorage.getItem(MUTE_KEY) === '1') return
    const synth = window.speechSynthesis
    if (!synth) return
    synth.cancel()
    const u = new SpeechSynthesisUtterance(String(text))
    u.lang = 'zh-CN'
    u.rate = 1.35 * (1 + (Math.random() * 0.06 - 0.03))   // 快而脆 + ±3% 语速抖动
    u.pitch = 0.94 + Math.random() * 0.16                  // 每句微变调，去复读机感
    u.volume = 0.95
    const vs = pickVoices()
    if (vs.length) u.voice = (seat !== null && seat !== undefined && vs.length > 1)
      ? vs[Math.abs(Number(seat)) % vs.length]
      : vs[0]
    synth.speak(u)
  } catch { /* 无 TTS 环境（部分 WebView）静默 */ }
}

/** 「不要」随机台词池（腾讯棋牌式：真人报牌是一人多台词，不是复读机） */
const PASS_LINES = ['要不起', '不要', '过']
export function speakPass(seat = null) {
  speak(PASS_LINES[Math.floor(Math.random() * PASS_LINES.length)], seat)
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
