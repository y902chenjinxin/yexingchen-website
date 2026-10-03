/**
 * 掼蛋 / 四川麻将 规则引擎单测（v2.43 棋牌三件套）。
 *
 * 两个引擎都是纯 JS、无 Vue 依赖，直接 import 即可断言。
 * 覆盖：牌堆完整性、牌型识别、比大小、升级；和牌判定、番种、听牌、向听、AI 选打、杠与危险度。
 */
import { describe, it, expect } from 'vitest'
import {
  buildDeck as gdDeck, deal, isWild, cardValue, detectPattern, canBeat,
  upgradeFor, nextLevel, levelText, PATTERN_NAME,
} from '@/utils/games/guandan'
import {
  buildDeck as mjDeck, counts, isStandardHu, isSevenPairs, isFlush, isAllTriplets,
  isAllEyes, hasMissing, canHu, scoreHu, tingTiles, shanten, aiDiscard,
  findAnkongs, findBugangs, dangerOf,
} from '@/utils/games/mahjong'

/* ---------------- 造牌工具 ---------------- */

const C = (suit, rank, id = 0) => ({ id, suit, rank, joker: null })
const J = (kind, id = 0) => ({ id, suit: '', rank: 0, joker: kind })

let seq = 0
/** hand(['m',1,2], ['s',9,1]) → 万1×2 + 条9×1 */
function hand(...specs) {
  const out = []
  for (const [suit, rank, n] of specs) {
    for (let i = 0; i < n; i++) out.push({ id: seq++, suit, rank })
  }
  return out
}
const T = (suit, rank) => ({ id: seq++, suit, rank })

/* ================= 掼蛋 ================= */

describe('掼蛋 · 牌堆与基础', () => {
  it('两副牌共 108 张（含 4 张王）', () => {
    const deck = gdDeck()
    expect(deck.length).toBe(108)
    expect(deck.filter(c => c.joker).length).toBe(4)
    expect(new Set(deck.map(c => c.id)).size).toBe(108)
  })

  it('发牌四家各 27 张且互不重复', () => {
    const hands = deal(2)
    expect(hands).toHaveLength(4)
    hands.forEach(h => expect(h).toHaveLength(27))
    expect(new Set(hands.flat().map(c => c.id)).size).toBe(108)
  })

  it('级牌文本：2..A，超出为 A+', () => {
    expect(levelText(2)).toBe('2')
    expect(levelText(11)).toBe('J')
    expect(levelText(14)).toBe('A')
    expect(levelText(15)).toBe('A+')
  })

  it('逢人配只认红桃级牌', () => {
    expect(isWild(C('♥', 2), 2)).toBe(true)
    expect(isWild(C('♥', 5), 2)).toBe(false)
    expect(isWild(C('♠', 2), 2)).toBe(false)
    expect(isWild(J('big'), 2)).toBe(false)
  })

  it('牌值：大王 17 > 小王 16 > 级牌 15 > 点数', () => {
    expect(cardValue(J('big'), 2)).toBe(17)
    expect(cardValue(J('small'), 2)).toBe(16)
    expect(cardValue(C('♠', 2), 2)).toBe(15)
    expect(cardValue(C('♠', 9), 2)).toBe(9)
  })
})

describe('掼蛋 · 牌型识别', () => {
  const p = (cards) => detectPattern(cards, 2)

  it('单张 / 对子 / 三张 / 三带二', () => {
    expect(p([C('♠', 5)]).type).toBe('single')
    expect(p([C('♠', 7), C('♦', 7)]).type).toBe('pair')
    expect(p([C('♠', 9), C('♦', 9), C('♣', 9)]).type).toBe('triple')
    const t2 = p([C('♠', 9), C('♦', 9), C('♣', 9), C('♠', 5), C('♦', 5)])
    expect(t2.type).toBe('triple2')
    expect(t2.key).toBe(9)
  })

  it('顺子（5 张连号，花色不限）', () => {
    const st = p([C('♠', 5), C('♥', 6), C('♣', 7), C('♦', 8), C('♠', 9)])
    expect(st.type).toBe('straight')
    expect(st.key).toBe(9)
  })

  it('同花顺优先于顺子，按炸弹计', () => {
    const fb = p([C('♠', 5), C('♠', 6), C('♠', 7), C('♠', 8), C('♠', 9)])
    expect(fb.type).toBe('flushbomb')
    expect(fb.bombLevel).toBeGreaterThan(0)
  })

  it('三连对 / 钢板', () => {
    expect(p([C('♠', 5), C('♦', 5), C('♠', 6), C('♦', 6), C('♠', 7), C('♦', 7)]).type).toBe('tube')
    const pl = p([C('♠', 8), C('♦', 8), C('♣', 8), C('♠', 9), C('♦', 9), C('♣', 9)])
    expect(pl.type).toBe('plate')
    expect(pl.key).toBe(9)
  })

  it('炸弹按张数记 bombLevel，四大天王最高', () => {
    const b4 = p([C('♠', 10), C('♦', 10), C('♣', 10), C('♥', 10)])
    expect(b4.type).toBe('bomb')
    expect(b4.bombLevel).toBe(4)
    const rocket = p([J('small'), J('small'), J('big'), J('big')])
    expect(rocket.type).toBe('rocket')
    expect(rocket.bombLevel).toBe(99)
  })

  it('双王对子合法，非法组合返回 null', () => {
    expect(p([J('small'), J('small')]).type).toBe('pair')
    expect(p([C('♠', 5), C('♦', 6)])).toBeNull()
    expect(p([C('♠', 5), C('♦', 5), C('♣', 6)])).toBeNull()
  })

  it('牌型名表齐全', () => {
    expect(Object.keys(PATTERN_NAME)).toHaveLength(10)
  })
})

describe('掼蛋 · 比大小与升级', () => {
  const P = (cards) => detectPattern(cards, 2)
  const bomb4x10 = P([C('♠', 10), C('♦', 10), C('♣', 10), C('♥', 10)])
  const bomb5x10 = P([C('♠', 10), C('♦', 10), C('♣', 10), C('♥', 10), C('♠', 10)])
  const bomb4x3 = P([C('♠', 3), C('♦', 3), C('♣', 3), C('♥', 3)])
  const straight9 = P([C('♠', 5), C('♥', 6), C('♣', 7), C('♦', 8), C('♠', 9)])
  const straight10 = P([C('♠', 6), C('♥', 7), C('♣', 8), C('♦', 9), C('♠', 10)])
  const rocket = P([J('small'), J('small'), J('big'), J('big')])
  const pair7 = P([C('♠', 7), C('♦', 7)])

  it('起牌（target 为空）任何合法牌型都能出', () => {
    expect(canBeat(pair7, null)).toBe(true)
    expect(canBeat(null, pair7)).toBe(false)
  })

  it('炸弹压普通牌型；大炸压小炸；小炸压不过大炸', () => {
    expect(canBeat(bomb4x10, straight9)).toBe(true)
    expect(canBeat(bomb5x10, bomb4x10)).toBe(true)
    expect(canBeat(bomb4x3, bomb4x10)).toBe(false)
  })

  it('普通牌型须同型同长且点数更大', () => {
    expect(canBeat(straight10, straight9)).toBe(true)
    expect(canBeat(straight9, straight10)).toBe(false)
    expect(canBeat(pair7, straight9)).toBe(false)
  })

  it('四大天王压一切，且不被任何牌压', () => {
    expect(canBeat(rocket, bomb5x10)).toBe(true)
    expect(canBeat(bomb5x10, rocket)).toBe(false)
  })

  it('升级：双上 3 / 一三 2 / 一四 1', () => {
    expect(upgradeFor([0, 2, 1, 3])).toBe(3)
    expect(upgradeFor([0, 1, 2, 3])).toBe(2)
    expect(upgradeFor([0, 1, 3, 2])).toBe(1)
  })

  it('升级封顶在 A+（15）', () => {
    expect(nextLevel(2, 3)).toBe(5)
    expect(nextLevel(13, 3)).toBe(15)
    expect(nextLevel(14, 1)).toBe(15)
  })
})

/* ================= 四川麻将 ================= */

describe('麻将 · 牌堆与和牌判定', () => {
  it('万/条/筒各 1-9 共四种，合计 108 张', () => {
    const deck = mjDeck()
    expect(deck.length).toBe(108)
    expect(deck.every(t => ['m', 's', 'p'].includes(t.suit))).toBe(true)
    expect(deck.every(t => t.rank >= 1 && t.rank <= 9)).toBe(true)
  })

  it('标准型：4 面子 + 1 将可胡', () => {
    const h = hand(['m', 1, 2], ['m', 2, 2], ['m', 3, 2], ['m', 4, 1],
      ['m', 5, 1], ['m', 6, 1], ['m', 7, 1], ['m', 8, 1], ['m', 9, 3])
    expect(h).toHaveLength(14)
    expect(isStandardHu(counts(h), 0)).toBe(true)
    expect(canHu(h, 0, '')).toBe(true)
  })

  it('差一张不算胡', () => {
    const h = hand(['m', 1, 2], ['m', 2, 2], ['m', 3, 2], ['m', 4, 1],
      ['m', 5, 1], ['m', 6, 1], ['m', 7, 1], ['m', 8, 1], ['m', 9, 2])
    expect(canHu(h, 0, '')).toBe(false)
  })

  it('缺门没打完不能胡', () => {
    const h = hand(['m', 1, 2], ['m', 2, 2], ['m', 3, 2], ['m', 4, 1],
      ['m', 5, 1], ['m', 6, 1], ['m', 7, 1], ['m', 8, 1], ['m', 9, 3])
    expect(hasMissing(counts(h), 'm')).toBe(true)
    expect(canHu(h, 0, 'm')).toBe(false)
  })

  it('七对 / 清一色 / 对对胡 / 将将胡 判定', () => {
    const seven = hand(['m', 1, 2], ['m', 2, 2], ['s', 3, 2], ['s', 4, 2], ['p', 5, 2], ['p', 6, 2], ['m', 7, 2])
    expect(isSevenPairs(counts(seven)).ok).toBe(true)

    const flush = hand(['m', 1, 2], ['m', 2, 2], ['m', 3, 2], ['m', 4, 1],
      ['m', 5, 1], ['m', 6, 1], ['m', 7, 1], ['m', 8, 1], ['m', 9, 3])
    expect(isFlush(counts(flush))).toBe(true)

    const triplets = hand(['m', 1, 3], ['s', 2, 3], ['p', 3, 3], ['m', 4, 3], ['s', 5, 2])
    expect(isAllTriplets(counts(triplets))).toBe(true)
    expect(isFlush(counts(triplets))).toBe(false)

    const eyes = hand(['m', 2, 3], ['m', 5, 3], ['m', 8, 3], ['s', 2, 3], ['s', 5, 2])
    expect(isAllEyes(counts(eyes))).toBe(true)
  })
})

describe('麻将 · 番种', () => {
  const namesOf = (h, melds = [], flags = {}) => scoreHu(h, melds, flags).names

  it('清一色平胡', () => {
    const h = hand(['m', 1, 2], ['m', 2, 2], ['m', 3, 2], ['m', 4, 1],
      ['m', 5, 1], ['m', 6, 1], ['m', 7, 1], ['m', 8, 1], ['m', 9, 3])
    const r = scoreHu(h)
    expect(r.names).toContain('清一色')
    expect(r.fan).toBeGreaterThanOrEqual(4)
  })

  it('七对（4 番）与龙七对（8 番）', () => {
    const seven = hand(['m', 1, 2], ['m', 2, 2], ['s', 3, 2], ['s', 4, 2], ['p', 5, 2], ['p', 6, 2], ['m', 7, 2])
    expect(scoreHu(seven).fan).toBe(4)
    expect(namesOf(seven)).toContain('七对')

    const dragon = hand(['m', 1, 4], ['m', 2, 2], ['s', 3, 2], ['s', 4, 2], ['p', 5, 2], ['p', 6, 2])
    expect(namesOf(dragon)).toContain('龙七对')
    expect(scoreHu(dragon).fan).toBeGreaterThanOrEqual(8)
  })

  it('对对胡 / 将将胡 / 金钩钓', () => {
    const triplets = hand(['m', 1, 3], ['s', 2, 3], ['p', 3, 3], ['m', 4, 3], ['s', 5, 2])
    expect(namesOf(triplets)).toContain('对对胡')

    const eyes = hand(['m', 2, 3], ['m', 5, 3], ['m', 8, 3], ['s', 2, 3], ['s', 5, 2])
    expect(namesOf(eyes)).toContain('将将胡')

    const melds = ['m1', 'm2', 'm3', 'm4'].map((_, i) => ({ type: 'pong', tile: T('m', i + 1) }))
    expect(namesOf(hand(['m', 5, 2]), melds)).toContain('金钩钓')
  })

  it('杠上花 / 抢杠胡 / 海底捞月 加番', () => {
    const h = hand(['m', 1, 2], ['m', 2, 2], ['m', 3, 2], ['m', 4, 1],
      ['m', 5, 1], ['m', 6, 1], ['m', 7, 1], ['m', 8, 1], ['m', 9, 3])
    const base = scoreHu(h).fan
    expect(scoreHu(h, [], { gangFlower: true }).fan).toBe(base + 1)
    expect(namesOf(h, [], { qiangGang: true })).toContain('抢杠胡')
    expect(namesOf(h, [], { haidi: true })).toContain('海底捞月')
  })
})

describe('麻将 · 听牌 / 向听 / AI', () => {
  const ready13 = hand(['m', 1, 2], ['m', 2, 2], ['m', 3, 2], ['m', 4, 1],
    ['m', 5, 1], ['m', 6, 1], ['m', 7, 1], ['m', 8, 1], ['m', 9, 2])

  it('听牌张包含 9 万（补成 99 将）', () => {
    const t = tingTiles(ready13, 0, '')
    expect(t.some(x => x.suit === 'm' && x.rank === 9)).toBe(true)
  })

  it('手牌有缺门时听牌为空', () => {
    expect(tingTiles(ready13, 0, 'm')).toHaveLength(0)
  })

  it('13 张一向听手牌向听数为 0', () => {
    expect(shanten(ready13, 0)).toBe(0)
  })

  it('AI 优先打缺门牌', () => {
    const h = hand(['s', 9, 1], ['m', 1, 1], ['m', 2, 1])
    const d = aiDiscard(h, 0, 's')
    expect(d.suit).toBe('s')
    expect(d.rank).toBe(9)
  })

  it('暗杠 / 补杠 识别', () => {
    const h = hand(['m', 1, 4], ['m', 2, 1])
    expect(findAnkongs(h)).toHaveLength(1)
    expect(findAnkongs(h)[0]).toMatchObject({ suit: 'm', rank: 1 })

    const pong = [{ type: 'pong', tile: T('m', 3) }]
    const h2 = hand(['m', 3, 1], ['m', 5, 1])
    expect(findBugangs(h2, pong)).toHaveLength(1)
    expect(findBugangs(hand(['m', 5, 1]), pong)).toHaveLength(0)
  })

  it('危险度：现三张即安全，生张中张更危险', () => {
    const t = T('m', 5)
    expect(dangerOf(t, [], [])).toBeGreaterThan(0)
    expect(dangerOf(t, [T('m', 5), T('m', 5), T('m', 5)], [])).toBe(0)
    const edge = T('m', 9)
    expect(dangerOf(t, [], [])).toBeGreaterThan(dangerOf(edge, [], []))
  })
})
