/** 四川麻将 · 胡牌即结束 规则引擎（v2.46.17）。
 *
 * 纯 JS，无 Vue 依赖：牌堆 / 和牌判定 / 听牌计算 / 向听数 / 番种 / AI 决策。
 *
 * 规则口径（与 PRD 一致）：
 * - 万(m) / 条(s) / 筒(p) 各 1–9 每种 4 张，共 108 张；**另加字牌**：
 *   箭牌（红中/发财/白板，v2.46.15 起）+ 风牌（东南西北，v2.46.17 起）各 4 张，
 *   共 136 张。字牌只能刻/对，**不成顺子**。
 * - **无定缺**（v2.46.17 起，夜星要求「单纯的胡牌规则」）：开局庄家直接起手摸牌，
 *   没有缺门限制；庄家轮换 —— 上一局胡牌者下局坐庄先出（本地由牌桌层处理）。
 * - 和牌型：4 组面子（顺子/刻子）+ 1 对将；或 7 对（含龙七对）。
 * - **胡牌即结束**（v2.46.10 起，不再是血战到底）：任一家胡牌（自摸或点炮）本局立即收摊，
 *   其余人不补摸补打；一炮只取**一家**胡（放炮者下家起逆时针就近优先），不存在一炮多响。
 * - 番种：平胡1 / 对对胡2 / 清一色4 / 七对4 / 龙七对8 / 将将胡4 / 金钩钓4；
 *   杠上花·杠上炮·抢杠胡·海底捞月 各 +1；每根（4 张相同，含杠）+1。
 */

export const SUITS = ['m', 's', 'p', 'z']
export const SUIT_NAME = { m: '万', s: '条', p: '筒', z: '字' }
/** 字牌的显示名（tileText / 胡牌提示用）：箭牌 1-3 + 风牌 4-7（风牌已退役，仅老局渲染兜底） */
export const HONOR_NAME = { 1: '红中', 2: '发财', 3: '白板', 4: '东风', 5: '南风', 6: '西风', 7: '北风' }
/** 每门花色的牌种数：数字牌 1–9，字牌只有 中/發/白 3 种
 *  （v2.46.24：东南西北风牌整副移除，夜星要求；与后端引擎同步） */
export const RANKS = { m: 9, s: 9, p: 9, z: 3 }
export const RANK_TEXT = { 1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九' }
/** 显示用：一筒 / 三条 / 五万；牌面数字优先，副标写花色 */
export const SUIT_GLYPH = { m: '萬', s: '條', p: '筒' }

/** 36 个点位 → 索引：m=0..8, s=9..17, p=18..26, z=27..29（30..35 留空恒为 0） */
export function idxOf(suit, rank) {
  return SUITS.indexOf(suit) * 9 + (rank - 1)
}
export function tileOf(i) {
  return { suit: SUITS[Math.floor(i / 9)], rank: (i % 9) + 1 }
}

export function buildDeck() {
  const tiles = []
  let id = 0
  for (const suit of SUITS) {
    for (let rank = 1; rank <= RANKS[suit]; rank++) {
      for (let k = 0; k < 4; k++) tiles.push({ id: id++, suit, rank })
    }
  }
  return tiles
}

export function shuffle(arr, rnd = Math.random) {
  const a = arr.slice()
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1))
    const t = a[i]; a[i] = a[j]; a[j] = t
  }
  return a
}

export function sortHand(hand) {
  return hand.slice().sort((a, b) => idxOf(a.suit, a.rank) - idxOf(b.suit, b.rank))
}

/* ---------------- 开牌仪式（v2.46.42，与后端 app/games/mahjong.py 镜像） ----------------
 * 120 张 = 4 边 × 15 墩 × 2 摞。玩家轮转逆时针（庄→下家），摸墙沿桌顺时针；
 * 环序（庄家视角）：本门 → 上家(左) → 对家 → 下家(右)；每边 15 墩，
 * 摸墙从该边右端（墩主自己的右手侧）进、向左端走。 */
export const MJ_STACKS = 15
export const MJ_RING = [0, 3, 2, 1]        // 相对庄的边序：0=本门 3=上家 2=对家 1=下家
export const MJ_OPEN_SIDE_NAME = ['本门', '下家', '对家', '上家']
export const MJ_WALL_AFTER_DEAL = 67       // 仪式发完（52 手牌 + 庄第 14 张）后墙里剩的牌数

export function openingPlan(d1, d2) {
  const total = d1 + d2
  const openRel = (total - 1) % 4          // 5/9 本门 6/10 下家 7/11 对家 8/12 上家
  const openIdx = Math.min(d1, d2)         // 小点数：跳过 min 墩，从第 min+1 墩起摸
  const breakStack = MJ_RING.indexOf(openRel) * MJ_STACKS + openIdx
  let stacks = []
  for (let i = 0; i < 4 * MJ_STACKS; i++) stacks.push(i)
  stacks = stacks.slice(breakStack).concat(stacks.slice(0, breakStack))
  return { total, openRel, openIdx, stacks }
}

export function dealOpening(deck, dealer, d1, d2) {
  const plan = openingPlan(d1, d2)
  const seq = []
  for (const s of plan.stacks) seq.push(deck[2 * s], deck[2 * s + 1])   // 每墩上张先摸
  const hands = [[], [], [], []]
  let p = 0
  for (let r = 0; r < 3; r++) {
    for (let off = 0; off < 4; off++) {
      hands[(dealer + off) % 4] = hands[(dealer + off) % 4].concat(seq.slice(p, p + 4))
      p += 4
    }
  }
  hands[dealer].push(seq[48])                                  // 跳牌：第 1 墩上张
  for (let off = 1; off <= 3; off++) hands[(dealer + off) % 4].push(seq[48 + 2 * off])
  const lastDraw = seq[56]                                     // 第 5 墩上张 = 庄家第 14 张
  const wall = [seq[49], seq[51], seq[53], seq[55], seq[57]].concat(seq.slice(58))
  return { ...plan, hands, lastDraw, wall }
}

/** 牌墙可视化：摸墙墩序第 k 墩剩余张数（2/1/0），left = 当前墙余牌数。
 *  仪式发掉 53 张后：前 24 墩空、第 25~29 墩各剩 1 张（零头）、其后满 2 张；
 *  之后每摸 1 张按零头→满墩顺序消耗。 */
export function stackRemain(k, left) {
  const d = Math.max(0, MJ_WALL_AFTER_DEAL - left)
  if (k < 24) return 0
  if (k < 29) return (k - 24) < d ? 0 : 1
  const g = d - 5
  if (g <= 0) return 2
  const full = Math.floor(g / 2)
  const idx = k - 29
  if (idx < full) return 0
  if (idx === full && g % 2) return 1
  return 2
}
/** 手牌 → 36 长度计数数组 */
export function counts(tiles) {
  const c = new Array(36).fill(0)
  for (const t of tiles) c[idxOf(t.suit, t.rank)]++
  return c
}

/* ---------------- 和牌判定 ---------------- */

/** 递归拆面子：need = 还需多少组面子（顺子或刻子）。
 *  字牌（i>=27）只有刻子，没有顺子。 */
function trySets(c, need) {
  if (need === 0) return c.every(x => x === 0)
  let i = 0
  while (i < 36 && c[i] === 0) i++
  if (i === 36) return false
  if (c[i] >= 3) {
    c[i] -= 3
    if (trySets(c, need - 1)) { c[i] += 3; return true }
    c[i] += 3
  }
  const rank = i % 9
  if (i < 27 && rank <= 6 && c[i + 1] > 0 && c[i + 2] > 0) {
    c[i]--; c[i + 1]--; c[i + 2]--
    if (trySets(c, need - 1)) { c[i]++; c[i + 1]++; c[i + 2]++; return true }
    c[i]++; c[i + 1]++; c[i + 2]++
  }
  return false
}

/** 标准型（4 面子 + 1 将）：concealed 张数须为 3n+2，melds 为已亮出的面子数 */
export function isStandardHu(c, meldCount) {
  const need = 4 - meldCount
  for (let i = 0; i < 36; i++) {
    if (c[i] >= 2) {
      c[i] -= 2
      const ok = trySets(c, need)
      c[i] += 2
      if (ok) return true
    }
  }
  return false
}

/** 七对：14 张全对（杠算两对）；返回 { ok, quads } */
export function isSevenPairs(c) {
  let pairs = 0, quads = 0
  for (let i = 0; i < 36; i++) {
    const n = c[i]
    if (n === 0) continue
    if (n % 2 !== 0) return { ok: false, quads: 0 }
    pairs += n / 2
    if (n === 4) quads++
  }
  return { ok: pairs === 7, quads }
}

/** 是否清一色（只有一门；纯字牌也算「字一色」，走同一番） */
export function isFlush(c) {
  const used = new Set()
  for (let i = 0; i < 36; i++) if (c[i] > 0) used.add(Math.floor(i / 9))
  return used.size === 1
}

/** 是否对对胡（全刻子，无顺子） */
export function isAllTriplets(c) {
  // 将牌 1 对 + 其余全刻子
  for (let i = 0; i < 36; i++) {
    if (c[i] >= 2) {
      const copy = c.slice()
      copy[i] -= 2
      let ok = true
      for (let j = 0; j < 36; j++) {
        if (copy[j] === 0) continue
        if (copy[j] === 3) continue
        ok = false; break
      }
      if (ok) return true
    }
  }
  return false
}

/** 是否将将胡（全部是 2/5/8；字牌不算） */
export function isAllEyes(c) {
  for (let i = 0; i < 36; i++) {
    if (c[i] === 0) continue
    if (i >= 27) return false
    const rank = (i % 9) + 1
    if (![2, 5, 8].includes(rank)) return false
  }
  return true
}

/**
 * 和牌判定。``missing`` 参数保留仅为兼容旧调用点（v2.46.17 起无缺门概念，恒忽略）。
 * @param {Array} hand 暗手牌（含刚摸/刚吃到的那张）
 * @param {number} meldCount 已亮出的面子数（碰/杠）
 * @param {string} [missing] 已废弃，忽略
 * @param {boolean} sevenPairsOK 是否允许七对（暗杠会破坏七对，故 meldCount>0 时不可）
 */
export function canHu(hand, meldCount, missing, sevenPairsOK = true) {
  const c = counts(hand)
  if (isStandardHu(c, meldCount)) return true
  if (sevenPairsOK && meldCount === 0 && hand.length === 14 && isSevenPairs(c).ok) return true
  return false
}

/* ---------------- 番种计算 ---------------- */

/**
 * @param {Array} hand 暗手牌（含和牌张）
 * @param {Array} melds [{ type:'pong'|'kong'|'ankong'|'bugang', tile }]
 * @param {Object} flags { gangFlower, gangPao, qiangGang, haidi, zimo }
 * @returns {{ fan:number, names:string[] }}
 */
export function scoreHu(hand, melds = [], flags = {}) {
  const all = hand.slice()
  for (const m of melds) all.push(m.tile)
  const c = counts(all)
  const names = []
  let fan = 1
  names.push('平胡')

  const seven = melds.length === 0 && hand.length === 14 ? isSevenPairs(c) : { ok: false, quads: 0 }
  if (seven.ok) {
    fan = seven.quads > 0 ? 8 : 4
    names.length = 0
    names.push(seven.quads > 0 ? '龙七对' : '七对')
  } else if (isAllTriplets(c)) {
    fan = 2; names.length = 0; names.push('对对胡')
  }

  if (isAllEyes(c)) { fan = Math.max(fan, 4); names.push('将将胡') }
  if (isFlush(c)) { fan = Math.max(fan, 4); names.push('清一色') }
  // 金钩钓：手上只剩 1 张（其余全亮出）
  if (melds.length === 4 && hand.length === 2) { fan = Math.max(fan, 4); names.push('金钩钓') }

  // 根：4 张相同（含杠）
  let gen = 0
  for (let i = 0; i < 36; i++) if (c[i] === 4) gen++
  if (gen > 0) { fan += gen; names.push(`根×${gen}`) }

  if (flags.gangFlower) { fan += 1; names.push('杠上花') }
  if (flags.gangPao) { fan += 1; names.push('杠上炮') }
  if (flags.qiangGang) { fan += 1; names.push('抢杠胡') }
  if (flags.haidi) { fan += 1; names.push('海底捞月') }

  return { fan, names }
}

/* ---------------- 听牌 / 向听 ---------------- */

/** 13 张（或 3n+1）手牌听哪些牌 → [{suit,rank}]（missing 参数废弃，恒忽略） */
export function tingTiles(hand, meldCount) {
  const out = []
  if (hand.length % 3 !== 1) return out
  for (const suit of SUITS) {
    for (let rank = 1; rank <= RANKS[suit]; rank++) {
      const probe = { id: -1, suit, rank }
      const test = hand.concat([probe])
      if (canHu(test, meldCount)) out.push({ suit, rank })
    }
  }
  return out
}

/** 向听数：-1=已和，0=听牌，越大越远。用于 AI 选打与危险度评估。 */
export function shanten(hand, meldCount = 0) {
  const c = counts(hand)
  const need = 4 - meldCount
  let best = 8

  const eyes = [-1]
  for (let i = 0; i < 36; i++) if (c[i] >= 2) eyes.push(i)

  for (const e of eyes) {
    const copy = c.slice()
    if (e >= 0) copy[e] -= 2
    let sets = 0
    for (let i = 0; i < 36; i++) while (copy[i] >= 3) { copy[i] -= 3; sets++ }
    // 顺子只在数字牌里成立（i<27）；字牌没有任何顺子搭法
    for (let i = 0; i < 27; i++) {
      const rank = i % 9
      while (rank <= 6 && copy[i] > 0 && copy[i + 1] > 0 && copy[i + 2] > 0) {
        copy[i]--; copy[i + 1]--; copy[i + 2]--; sets++
      }
    }
    let partials = 0
    const rest = copy.slice()
    for (let i = 0; i < 36; i++) {
      while (rest[i] >= 2 && sets + partials < need) { rest[i] -= 2; partials++ }
    }
    for (let i = 0; i < 27; i++) {
      const rank = i % 9
      while (rank <= 7 && rest[i] > 0 && rest[i + 1] > 0 && sets + partials < need) {
        rest[i]--; rest[i + 1]--; partials++
      }
    }
    for (let i = 0; i < 27; i++) {
      const rank = i % 9
      while (rank <= 6 && rest[i] > 0 && rest[i + 2] > 0 && sets + partials < need) {
        rest[i]--; rest[i + 2]--; partials++
      }
    }
    const m = Math.min(sets, need)
    const p = Math.min(partials, need - m)
    const s = (need - m) * 2 - p - (e >= 0 ? 1 : 0)
    if (s < best) best = s
  }

  // 七对向听（仅门清时才有意义）
  if (meldCount === 0) {
    let pairs = 0, kinds = 0
    for (let i = 0; i < 36; i++) { if (c[i] > 0) kinds++; pairs += Math.floor(c[i] / 2) }
    const sp = 6 - pairs + Math.max(0, 7 - kinds)
    if (sp < best) best = sp
  }
  return best
}

/** 已和牌时向听为负，统一成「听牌数 / 进张数」评估 */
export function usefulCount(hand, meldCount) {
  const t = tingTiles(hand, meldCount)
  return t.length
}

/* ---------------- AI 决策 ---------------- */

/** 缺门牌优先打；其次打孤张、边张。字牌没有相邻搭牌，只有刻/对价值。 */
function tileScore(c, i) {
  const rank = (i % 9) + 1
  let s = 0
  if (c[i] >= 3) s += 6
  else if (c[i] === 2) s += 4
  if (i >= 27) {
    if (c[i] === 1) s -= 1   // 孤张字牌没有顺子搭法，价值最低
    return s
  }
  if (rank >= 3 && rank <= 7) s += 2
  if (c[i + 1] > 0 || c[i - 1] > 0) s += 1
  if (i % 9 <= 7 && c[i + 1] > 0) s += 1
  if (i % 9 >= 1 && c[i - 1] > 0) s += 1
  return s
}

/** 单张危险度（v2.46.31，0~12）：现物 0；字牌看可见数；数牌越中张越危险。 */
function tileDanger(t, safe, visible, own) {
  const i = idxOf(t.suit, t.rank)
  if (safe && safe.has(i)) return 0
  const vis = (visible && visible[i] ? visible[i] : 0) + own[i]
  if (i >= 27) {
    if (vis >= 3) return 1
    if (vis === 2) return 4
    return 9        // 孤字牌可能被单钓/碰
  }
  const rank = (i % 9) + 1
  let base = rank === 1 || rank === 9 ? 5 : (rank === 2 || rank === 8 ? 8 : 12)
  if (vis >= 2) base -= 4
  else if (vis === 1) base -= 2
  return Math.max(2, base)
}

/**
 * AI 打哪张。``missing`` 参数废弃（v2.46.17 无缺门），保留仅为兼容旧签名。
 * @param {Array} hand 当前暗手牌（3n+2，刚摸完）
 * @param {number} meldCount
 * @param {string} [missing] 已废弃，忽略
 * @param {Object} ctx { level, threat, safe:Set<idx>, visible:Array<number> }
 *   v2.46.31 防守：threat=有对手听牌时，按危险度扣分——自己已听牌保持进攻（×0.3）、
 *   一向听权衡（×3）、两向听开外优先安全牌（×8）
 * @returns {Object} 要打出的牌
 */
export function aiDiscard(hand, meldCount, ctx = {}) {
  const c = counts(hand)
  const weak = ctx.level === 'weak'
  // 弱 AI：直接打孤张
  if (weak) {
    let worst = null, worstScore = Infinity
    for (const t of hand) {
      const s = tileScore(c, idxOf(t.suit, t.rank))
      if (s < worstScore) { worstScore = s; worst = t }
    }
    return worst || hand[0]
  }
  // 正常 AI：逐张试打，看向听是否最优（进张数多者优先）+ 威胁时叠加危险度
  let bestTile = hand[0], bestKey = -Infinity
  const seen = new Set()
  const shNow = ctx.threat ? shanten(hand, meldCount) : 0
  const dangerW = ctx.threat ? (shNow === 0 ? 0 : (shNow === 1 ? 3 : 8)) : 0
  for (const t of hand) {
    const k = `${t.suit}${t.rank}`
    if (seen.has(k)) continue
    seen.add(k)
    const rest = hand.filter(x => x.id !== t.id)
    const sh = shanten(rest, meldCount)
    const u = usefulCount(rest, meldCount)
    const s = tileScore(c, idxOf(t.suit, t.rank))
    const danger = ctx.threat ? tileDanger(t, ctx.safe, ctx.visible, c) : 0
    const key = -sh * 100 + u * 3 + s - Math.round(danger * dangerW * 0.3)
    if (key > bestKey) { bestKey = key; bestTile = t }
  }
  return bestTile
}

/** AI 是否碰：对子多/向听改善才碰 */
export function aiWantPong(hand, tile, meldCount, missing, ctx = {}) {
  const c = counts(hand)
  const same = c[idxOf(tile.suit, tile.rank)]
  if (same < 2) return false
  if (ctx.level === 'weak') return Math.random() < 0.55
  const before = shanten(hand, meldCount)
  const after = shanten(hand.filter(t => !(t.suit === tile.suit && t.rank === tile.rank)).slice(2), meldCount + 1)
  return after < before || same >= 3
}

/** AI 是否杠 */
export function aiWantKong(hand, tile, meldCount, missing, ctx = {}) {
  const c = counts(hand)
  if (c[idxOf(tile.suit, tile.rank)] < 3) return false
  if (ctx.level === 'weak') return Math.random() < 0.5
  return true
}

/**
 * 吃牌组合（v2.46.24，与后端 chi_combos 同口径）：上家弃牌 t，手里有同花色连张即可吃
 * （万/条/筒，字牌不吃）。返回所有组合（每项是与弃牌相连的两张手牌）。
 */
export function chiCombos(hand, tile) {
  if (tile.suit === 'z') return []
  const r = tile.rank
  const c = counts(hand)
  const out = []
  for (const [a, b] of [[r - 2, r - 1], [r - 1, r + 1], [r + 1, r + 2]]) {
    if (a < 1 || b > 9) continue
    if (c[idxOf(tile.suit, a)] > 0 && c[idxOf(tile.suit, b)] > 0) {
      const pa = hand.find(x => x.suit === tile.suit && x.rank === a)
      const pb = hand.find(x => x.suit === tile.suit && x.rank === b && x.id !== pa.id)
      out.push([pa, pb])
    }
  }
  return out
}

/** AI 是否吃：吃完整体向听数前进才吃（保守策略，与后端一致） */
export function aiWantChi(hand, tile, meldCount, missing, ctx = {}) {
  const combos = chiCombos(hand, tile)
  if (!combos.length) return false
  if (ctx.level === 'weak') return Math.random() < 0.5
  const before = shanten(hand, meldCount)
  const rest = hand.filter(t => t.id !== combos[0][0].id && t.id !== combos[0][1].id)
  return shanten(rest, meldCount + 1) < before
}

/** AI 是否胡：见胡就胡（胡牌即结束，一胡就是本局赢家） */
export function aiWantHu(hand, meldCount) {
  return canHu(hand, meldCount)
}

/** 找出手牌里所有可暗杠的点位 */
export function findAnkongs(hand) {
  const c = counts(hand)
  const out = []
  for (let i = 0; i < 36; i++) if (c[i] === 4) out.push(tileOf(i))
  return out
}

/** 找出可补杠的点位（已碰过的牌又摸到第 4 张） */
export function findBugangs(hand, melds) {
  const c = counts(hand)
  const out = []
  for (const m of melds) {
    if (m.type !== 'pong') continue
    if (c[idxOf(m.tile.suit, m.tile.rank)] >= 1) out.push(m.tile)
  }
  return out
}

/** 舍牌危险度（0=安全 → 越大越危险）：仅做启发式，供提示用 */
export function dangerOf(tile, discards, meldsByPlayer) {
  const key = `${tile.suit}${tile.rank}`
  let d = 0
  // 已现过 3 张以上 → 安全（别人用不上）
  const shown = discards.filter(t => `${t.suit}${t.rank}` === key).length
  if (shown >= 3) return 0
  d += shown * 1.5
  // 生张中张更危险
  const rank = tile.rank
  if (rank >= 4 && rank <= 6) d += 2
  else if (rank === 3 || rank === 7) d += 1
  // 有人副露多 → 更危险
  const meldTotal = (meldsByPlayer || []).reduce((a, b) => a + b, 0)
  d += Math.min(3, meldTotal * 0.25)
  return d
}
