/** 掼蛋「报牌」口播文案（v2.46.262）。
 *
 *  夜星：「只有出牌音效，没有具体牌的内容，如 3个3带1对2这种，需要加下。」
 *  这段逻辑原来长在 2D 板（GuandanBoard.vue）里，3D 板没有 —— 抽出来给两边共用，
 *  以后再有其他渲染层（观战 / 回放）也能直接接。
 *
 *  要点：
 *  - 逢人配（百搭）不单独报，数量并入主组：「三个二」而不是「两个二加一个配」
 *  - 大小王各自成组、各自报「大王 / 小王」，不参与数字排序
 *  - 炸弹带一个「炸！」的喊声（腾讯棋牌那种），其余牌型只报牌面或牌型名
 */
import * as G from './guandan.js'

const TTS_CN = { 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九', 10: '十', 11: 'J', 12: 'Q', 13: 'K', 14: 'A' }
const TTS_COUNT = { 1: '', 2: '一对', 3: '三个', 4: '四个', 5: '五个', 6: '六个' }

/** 单张牌的点数口播：joker → 大王/小王，其余 → 中文/字母点数 */
export function ttsRank(c) {
  if (!c) return ''
  if (c.joker) return c.joker === 'big' ? '大王' : '小王'
  return TTS_CN[c.rank] || String(c.rank)
}

/**
 * 一手牌的播报文案。
 * @param {Array} cards 出的牌
 * @param {object} pat  服务端/本地识别出的牌型 { type }
 * @param {number} roundLevel 当前级牌（判断逢人配用）
 * @returns {string} 如「三个三，带对二」「炸！四个六」「顺子」
 */
export function describePlay(cards, pat, roundLevel) {
  const t = pat?.type
  if (!t || !cards || !cards.length) return ''
  const groups = new Map()
  let wildN = 0
  for (const c of cards) {
    if (G.isWild(c, roundLevel)) { wildN += 1; continue }
    const k = c.joker ? `j${c.joker}` : c.rank
    if (!groups.has(k)) groups.set(k, [])
    groups.get(k).push(c)
  }
  const gs = [...groups.values()].sort((a, b) => b.length - a.length)
  const main = gs[0] || []
  const mainN = main.length + (gs.length ? 0 : wildN)   // 全百搭时并给主组
  const head = main[0] || cards[0]
  const mainTxt = `${TTS_COUNT[Math.min(mainN, 6)] || ''}${ttsRank(head)}`

  if (t === 'single') return mainTxt || '单张'
  if (t === 'pair') return `对${ttsRank(head)}`
  if (t === 'triple') return `三个${ttsRank(head)}`
  if (t === 'triple2') {
    const kick = gs[1]
    return `三个${ttsRank(head)}，带对${kick ? ttsRank(kick[0]) : ''}`
  }
  if (t === 'bomb') return `炸！${TTS_COUNT[Math.min(cards.length, 6)] || ''}${ttsRank(head)}`
  return G.PATTERN_NAME[t] || ''
}
