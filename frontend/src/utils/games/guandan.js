/** 掼蛋规则引擎（v2.43）。
 *
 * 纯 JS，无 Vue 依赖：牌堆 / 牌型识别 / 比大小 / AI 选牌 / 升级计算。
 * 两副牌共 108 张（含 4 张王），4 人各 27 张，座位 0/2 一队、1/3 一队。
 *
 * 牌值：大王 17 > 小王 16 > 级牌 15 > 其余按点数 2..14(A)。
 * 逢人配：红桃级牌是百搭，可当除王以外的任意一张牌（凑对、三、顺、连对、钢板、炸弹、同花顺）。
 *
 * 简化点（与标准掼蛋的差异，均在此声明）：
 * 1. 不做进贡/还贡，直接由上一局头游起牌。
 * 2. 炸弹张数上限取 8（两副牌同点最多 8 张）。
 * 3. 「打过 A」即整场获胜，不再要求恰好赢 A 局。
 * 4. 顺子/连对/钢板里的 A 可作 1（A2345）也可作 14（10JQKA），按序列归一。
 */

export const SUITS = ['♠', '♥', '♣', '♦']
export const RANK_TEXT = {
  2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9',
  10: '10', 11: 'J', 12: 'Q', 13: 'K', 14: 'A',
}
export const JOKER_SMALL = 16
export const JOKER_BIG = 17
export const TEAM_OF = { 0: 0, 1: 1, 2: 0, 3: 1 }
export const MAX_LEVEL = 14   // A
export const MIN_LEVEL = 2

/** 座位相对关系：0=你(下) 1=右家 2=对家(上) 3=左家 */
export const SEAT_NAME = { 0: '你', 1: '右家', 2: '对家', 3: '左家' }

export function levelText(l) {
  if (l > MAX_LEVEL) return 'A+'
  return RANK_TEXT[l] || String(l)
}

export function buildDeck() {
  const cards = []
  let id = 0
  for (let d = 0; d < 2; d++) {
    for (const s of SUITS) {
      for (let r = 2; r <= 14; r++) cards.push({ id: id++, suit: s, rank: r, joker: null })
    }
    cards.push({ id: id++, suit: '', rank: 0, joker: 'small' })
    cards.push({ id: id++, suit: '', rank: 0, joker: 'big' })
  }
  return cards
}

export function shuffle(arr, rnd = Math.random) {
  const a = arr.slice()
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1))
    const t = a[i]; a[i] = a[j]; a[j] = t
  }
  return a
}

export function isWild(card, level) {
  return !card.joker && card.suit === '♥' && card.rank === level
}

/** 单张比大小的数值：大王17 / 小王16 / 级牌15 / 其余点数 */
export function cardValue(card, level) {
  if (card.joker) return card.joker === 'big' ? JOKER_BIG : JOKER_SMALL
  return card.rank === level ? 15 : card.rank
}

/** 分组用的点数键：王用 16/17，其余用点数（级牌仍是自身点数，便于凑顺子） */
export function rankKey(card) {
  if (card.joker) return card.joker === 'big' ? JOKER_BIG : JOKER_SMALL
  return card.rank
}

function keyOfRank(rk, level) {
  if (rk >= 16) return rk
  return rk === level ? 15 : rk
}

function mk(type, len, key, bombLevel, cards) {
  return { type, len, key, bombLevel, cards }
}

export const PATTERN_NAME = {
  single: '单张', pair: '对子', triple: '三张', triple2: '三带二',
  straight: '顺子', tube: '三连对', plate: '钢板',
  bomb: '炸弹', flushbomb: '同花顺', rocket: '四大天王',
}

/* ---------------- 序列工具 ---------------- */

/** a=1 → [A,2,3,4,5]（A 作 1）；a=10 → [10,J,Q,K,A] */
function seqRanks(a, len) {
  const out = []
  for (let i = 0; i < len; i++) {
    const r = a + i
    out.push(r === 1 ? 14 : r)
  }
  return out
}

function tryStraight(rest, W, sameSuit) {
  if (!rest.length) return null
  if (rest.some(c => c.joker)) return null
  const ranks = rest.map(c => c.rank)
  if (new Set(ranks).size !== ranks.length) return null
  if (sameSuit && new Set(rest.map(c => c.suit)).size > 1) return null
  for (let a = 1; a <= 10; a++) {
    const seq = seqRanks(a, 5)
    if (rest.every(c => seq.includes(c.rank))) {
      if (5 - rest.length === W) return { top: seq[4] }
    }
  }
  return null
}

function tryTriple2(rest, W, level) {
  if (rest.some(c => c.joker)) {
    const jokers = rest.filter(c => c.joker)
    const others = rest.filter(c => !c.joker)
    if (jokers.length === 2 && jokers[0].joker === jokers[1].joker) {
      if (others.length + W === 3 && (others.length === 0 || new Set(others.map(c => c.rank)).size === 1)) {
        const rk = others.length ? others[0].rank : level
        return { key: keyOfRank(rk, level) }
      }
    }
    return null
  }
  const cnt = {}
  for (const c of rest) cnt[c.rank] = (cnt[c.rank] || 0) + 1
  const ranks = Object.keys(cnt).map(Number)
  for (const tr of ranks) {
    for (const pr of ranks) {
      if (tr === pr) continue
      const ct = cnt[tr], cp = cnt[pr]
      if (ct > 3 || cp > 2) continue
      if (ct + cp !== rest.length) continue
      const need = Math.max(0, 3 - ct) + Math.max(0, 2 - cp)
      if (need !== W) continue
      return { key: keyOfRank(tr, level) }
    }
  }
  return null
}

function tryTube(rest, W) {
  if (!rest.length || rest.some(c => c.joker)) return null
  const cnt = {}
  for (const c of rest) cnt[c.rank] = (cnt[c.rank] || 0) + 1
  for (let a = 1; a <= 12; a++) {
    const seq = seqRanks(a, 3)
    let need = 0, used = 0, ok = true
    for (const r of seq) {
      const c = cnt[r] || 0
      if (c > 2) { ok = false; break }
      need += Math.max(0, 2 - c)
      used += Math.min(2, c)
    }
    if (!ok || used !== rest.length || need !== W) continue
    return { key: seq[2] }
  }
  return null
}

function tryPlate(rest, W) {
  if (!rest.length || rest.some(c => c.joker)) return null
  const cnt = {}
  for (const c of rest) cnt[c.rank] = (cnt[c.rank] || 0) + 1
  for (let a = 1; a <= 13; a++) {
    const seq = seqRanks(a, 2)
    let need = 0, used = 0, ok = true
    for (const r of seq) {
      const c = cnt[r] || 0
      if (c > 3) { ok = false; break }
      need += Math.max(0, 3 - c)
      used += Math.min(3, c)
    }
    if (!ok || used !== rest.length || need !== W) continue
    return { key: seq[1] }
  }
  return null
}

/* ---------------- 牌型识别 ---------------- */

export function detectPattern(cards, level) {
  const n = cards.length
  if (!n) return null
  const wilds = cards.filter(c => isWild(c, level))
  const rest = cards.filter(c => !isWild(c, level))
  const W = wilds.length

  if (n === 1) return mk('single', 1, cardValue(cards[0], level), 0, cards)

  // 四大天王：两副牌的全部 4 张王
  if (n === 4 && W === 0 && rest.every(c => c.joker)) return mk('rocket', 4, 0, 99, cards)

  // 同点数：对 / 三 / 炸
  const rks = rest.map(rankKey)
  const uniq = new Set(rks)
  if (rest.length === 0 || uniq.size === 1) {
    const isJokerGroup = rest.length > 0 && rest[0].joker
    if (isJokerGroup) {
      if (n === 2 && rest.length === 2 && rest[0].joker === rest[1].joker) {
        return mk('pair', 2, keyOfRank(rks[0], level), 0, cards)
      }
      return null
    }
    const rk = rest.length ? rks[0] : level
    const key = keyOfRank(rk, level)
    if (n === 2) return mk('pair', 2, key, 0, cards)
    if (n === 3) return mk('triple', 3, key, 0, cards)
    if (n >= 4 && n <= 8) return mk('bomb', n, key, n, cards)
    return null
  }

  if (n === 5) {
    const fl = tryStraight(rest, W, true)
    if (fl && rest.length > 0) return mk('flushbomb', 5, fl.top, 5.5, cards)
    const st = tryStraight(rest, W, false)
    if (st) return mk('straight', 5, st.top, 0, cards)
    const t2 = tryTriple2(rest, W, level)
    if (t2) return mk('triple2', 5, t2.key, 0, cards)
    return null
  }

  if (n === 6) {
    const tb = tryTube(rest, W)
    if (tb) return mk('tube', 6, tb.key, 0, cards)
    const pl = tryPlate(rest, W)
    if (pl) return mk('plate', 6, pl.key, 0, cards)
    return null
  }

  return null
}

/** cand 能否压过 target（target 为 null 表示起牌，任何合法牌型都行） */
export function canBeat(cand, target) {
  if (!cand) return false
  if (!target) return true
  if (cand.type === 'rocket') return true
  if (target.type === 'rocket') return false
  const cb = cand.bombLevel || 0
  const tb = target.bombLevel || 0
  if (cb && tb) return cb !== tb ? cb > tb : cand.key > target.key
  if (cb) return true
  if (tb) return false
  if (cand.type !== target.type || cand.len !== target.len) return false
  return cand.key > target.key
}

/* ---------------- 手牌工具 ---------------- */

export function sortHand(hand, level) {
  return hand.slice().sort((a, b) => {
    const d = cardValue(b, level) - cardValue(a, level)
    if (d) return d
    return SUITS.indexOf(a.suit) - SUITS.indexOf(b.suit)
  })
}

export function deal(level, rnd = Math.random) {
  const deck = shuffle(buildDeck(), rnd)
  return [0, 1, 2, 3].map(i => sortHand(deck.slice(i * 27, (i + 1) * 27), level))
}

/* ---------------- AI 候选生成 ---------------- */

function buildSeq(hand, level, ranks, perRank) {
  const used = new Set()
  const out = []
  let needWilds = 0
  for (const r of ranks) {
    const pool = hand.filter(c => !used.has(c.id) && !isWild(c, level) && c.rank === r)
    const take = Math.min(perRank, pool.length)
    for (let i = 0; i < take; i++) { used.add(pool[i].id); out.push(pool[i]) }
    needWilds += perRank - take
  }
  if (needWilds > 0) {
    const w = hand.filter(c => isWild(c, level) && !used.has(c.id)).slice(0, needWilds)
    if (w.length < needWilds) return null
    for (const c of w) { used.add(c.id); out.push(c) }
  }
  return out
}

function buildFlush(hand, level, suit, ranks) {
  const used = new Set()
  const out = []
  let needWilds = 0
  for (const r of ranks) {
    const c = hand.find(x => !used.has(x.id) && !isWild(x, level) && x.suit === suit && x.rank === r)
    if (c) { used.add(c.id); out.push(c) } else needWilds++
  }
  if (needWilds > 0) {
    const w = hand.filter(x => isWild(x, level) && !used.has(x.id)).slice(0, needWilds)
    if (w.length < needWilds) return null
    for (const c of w) { used.add(c.id); out.push(c) }
  }
  return out
}

/** 枚举手牌里所有「像样的」候选出牌（不求全，够 AI 用）。 */
export function genCandidates(hand, level) {
  const out = []
  const wilds = hand.filter(c => isWild(c, level))
  const nonWild = hand.filter(c => !isWild(c, level))
  const W = wilds.length

  for (const c of hand) out.push([c])

  const byRank = new Map()
  for (const c of nonWild) {
    const k = rankKey(c)
    if (!byRank.has(k)) byRank.set(k, [])
    byRank.get(k).push(c)
  }

  for (const [rk, arr] of byRank) {
    const canWild = rk < 16 ? W : 0
    const max = arr.length + canWild
    for (const size of [2, 3]) {
      if (max < size) continue
      const take = Math.min(arr.length, size)
      out.push(arr.slice(0, take).concat(wilds.slice(0, size - take)))
    }
    for (let size = 4; size <= max; size++) {
      const take = Math.min(arr.length, size)
      out.push(arr.slice(0, take).concat(wilds.slice(0, size - take)))
    }
  }

  // 四大天王
  const bigs = nonWild.filter(c => c.joker === 'big')
  const smalls = nonWild.filter(c => c.joker === 'small')
  if (bigs.length >= 2 && smalls.length >= 2) out.push([...bigs.slice(0, 2), ...smalls.slice(0, 2)])

  // 顺子 / 同花顺
  for (let a = 1; a <= 10; a++) {
    const seq = seqRanks(a, 5)
    const st = buildSeq(hand, level, seq, 1)
    if (st && st.length === 5) out.push(st)
    for (const s of SUITS) {
      const fl = buildFlush(hand, level, s, seq)
      if (fl && fl.length === 5) out.push(fl)
    }
  }
  // 三连对
  for (let a = 1; a <= 12; a++) {
    const t = buildSeq(hand, level, seqRanks(a, 3), 2)
    if (t && t.length === 6) out.push(t)
  }
  // 钢板
  for (let a = 1; a <= 13; a++) {
    const p = buildSeq(hand, level, seqRanks(a, 2), 3)
    if (p && p.length === 6) out.push(p)
  }

  return out
}

/**
 * 枚举 5 张连续牌的候选组合，**按牌型大小降序**（大的在前）。
 *
 * 「同花顺 / 顺子」按钮的轮换顺序就吃这个顺序：夜星要的是
 * 「6~9 张同花默认先汇总**最大**的同花顺，再点才依次换小的」，
 * 所以这里从 a=10 往 a=1 扫，同 key 去重。
 * 逢人配（红桃级牌）由 buildFlush / buildSeq 就地补位 —— 大的一组先被枚举到，
 * 天然优先拿到逢人配，即「红心牌默认配给大的同花顺」。
 *
 * @param {boolean} sameSuit true=只连同花顺（5 张同花色）；
 *                           false=普通顺子（花色不限；整组同花的会被 detectPattern 判成
 *                           同花顺，这里剔除，避免与同花顺那组重复）
 */
function seqCombos(hand, level, sameSuit) {
  const out = []
  const seen = new Set()
  for (let a = 10; a >= 1; a--) {
    const seq = seqRanks(a, 5)
    const groups = sameSuit
      ? SUITS.map(s => buildFlush(hand, level, s, seq))
      : [buildSeq(hand, level, seq, 1)]
    for (const cs of groups) {
      if (!cs || cs.length !== 5) continue
      const pat = detectPattern(cs, level)
      if (!pat) continue
      if (sameSuit ? pat.type !== 'flushbomb' : pat.type !== 'straight') continue
      const key = cs.map(c => c.id).sort((x, y) => x - y).join(',')
      if (seen.has(key)) continue
      seen.add(key)
      out.push({ cards: cs, key: pat.key })
    }
  }
  out.sort((x, y) => y.key - x.key)
  return out.map(x => x.cards)
}

/**
 * 手牌里所有「同花顺」组合（逢人配可补位），供「同花顺」按钮轮换归集。
 * 按牌型大小 **从大到小**（第一次点给的就是最大的一组）。
 */
export function findFlushBombs(hand, level) {
  return seqCombos(hand, level, true)
}

/**
 * 「顺子」按钮的候选：**同花顺优先，其次普通顺子**（夜星：「优先级为同花顺>顺子」）。
 * 同花顺一组从大到小排在前面，普通顺子去重后接在后面。
 */
export function findSeqGroups(hand, level) {
  const flushes = seqCombos(hand, level, true)
  const seen = new Set(flushes.map(cs => cs.map(c => c.id).sort((x, y) => x - y).join(',')))
  const straights = seqCombos(hand, level, false).filter((cs) => {
    const k = cs.map(c => c.id).sort((x, y) => x - y).join(',')
    if (seen.has(k)) return false
    seen.add(k)
    return true
  })
  return [...flushes, ...straights]
}

/* ---------------- AI 出牌 ---------------- */

/**
 * @param {Array} hand 手牌
 * @param {Object|null} target 需要压过的牌型（null=起牌）
 * @param {number} level 主级牌
 * @param {Object} ctx { lastIsTeammate:boolean }
 * @returns {Array} 要出的牌；[] 表示「不要」
 */
export function aiChoose(hand, target, level, ctx = {}) {
  const cands = genCandidates(hand, level)
  const seen = new Set()
  const plays = []
  for (const cs of cands) {
    const key = cs.map(c => c.id).sort((a, b) => a - b).join(',')
    if (seen.has(key)) continue
    seen.add(key)
    const p = detectPattern(cs, level)
    if (p) plays.push({ cs, p })
  }
  if (!plays.length) return []

  // 能一把走完就走完
  const fin = plays.find(x => x.cs.length === hand.length)
  if (fin && (!target || canBeat(fin.p, target))) return fin.cs

  if (!target) {
    const nonBomb = plays.filter(x => !x.p.bombLevel)
    const pool = nonBomb.length ? nonBomb : plays
    pool.sort((a, b) => (b.cs.length - a.cs.length) || (a.p.key - b.p.key))
    return pool[0].cs
  }

  const beats = plays.filter(x => canBeat(x.p, target))
  if (!beats.length) return []
  // 队友领出、自己还有牌 → 让队友走
  if (ctx.lastIsTeammate) return []

  beats.sort((a, b) =>
    ((a.p.bombLevel || 0) - (b.p.bombLevel || 0)) ||
    (a.p.key - b.p.key) ||
    (a.cs.length - b.cs.length))
  return beats[0].cs
}

/* ---------------- 升级 ---------------- */

/** 一局名次 → 升几级：双上 3 / 一三 2 / 一四 1 */
export function upgradeFor(finishOrder) {
  const first = finishOrder[0]
  const team = TEAM_OF[first]
  const partner = team === 0 ? (first === 0 ? 2 : 0) : (first === 1 ? 3 : 1)
  const pos = finishOrder.indexOf(partner)
  if (pos === 1) return 3
  if (pos === 2) return 2
  return 1
}

export function nextLevel(l, up) {
  return Math.min(MAX_LEVEL + 1, l + up)
}
