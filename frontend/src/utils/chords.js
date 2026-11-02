/**
 * 和弦推导（v2.46.338）
 *
 * 夜星：「我觉得好难啊，是不是吉他简单一点」—— 算完谱面密度才确认，
 * 难的不是乐器，是「1 个动作只换 1 个音」：兰亭序 4.8 音/秒，一半间隔不到 250ms。
 * 吉他的爽感来自「按一个和弦、扫一下 = 3~4 个音同时响」。
 *
 * 所以这里做的事就是：把音符流聚成「和弦流」，
 * 让一个键 = 一个和弦（3 个音一起响），谱面从 368 个音压到 60 来个和弦。
 *
 * 全部按原曲音高反推，不需要人工标记和弦，任何上传的曲谱都能用。
 */

import { KEY_TO_MIDI, NOTE_NAMES } from './pianoKeys'

const PC_NAME = NOTE_NAMES

/**
 * 取一个音符的实际 MIDI。
 *
 * 曲谱有三种来源，字段不统一（这坑踩过一次：只认 `midi` 会让整个推导返回 0 个和弦，
 * 而界面上看着「和弦谱是空的」，很像推导逻辑写错了）：
 *   · 带 `midi`（脚本转出来的）
 *   · 带 `pitch`（"G4"，sky2song 的产物）
 *   · 只有 `key`（示例曲、手写的谱）
 */
function midiOf(note) {
  if (Number.isFinite(note?.midi)) return note.midi
  const p = String(note?.pitch || '').trim()
  if (p) {
    const m = /^([A-G]#?)(-?\d)$/.exec(p)
    if (m) {
      const pc = NOTE_NAMES.indexOf(m[1])
      if (pc >= 0) return pc + 12 * (Number(m[2]) + 1)
    }
  }
  const k = String(note?.key || '').trim()
  return KEY_TO_MIDI.has(k) ? KEY_TO_MIDI.get(k) : null
}

/** 大三和弦音程 */
const THIRD_MAJOR = 4
/** 小三和弦音程 */
const THIRD_MINOR = 3

/**
 * 键位池：按「双手食指到小指的舒服顺序」排。
 *
 * 不用 1~0：那是黑键（`PianoKeyboard` 已占用），重复绑定会互相打架。
 * 一首歌通常只有 5~8 个不同和弦，前 8 个足够覆盖；
 * 真超过 8 个也不会丢（`KEY_POOL` 有 12 个）。
 */
export const CHORD_KEY_POOL = ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'Q', 'W', 'E']

/**
 * 一个候选和弦在给定音级集合上的匹配度。
 *
 * 打分口径（按经验定的，改之前先想清楚）：
 *   · 根音命中 1.8 —— 根音是判断和弦身份最强的信号
 *   · 三音/五音命中 1.0
 *   · 集合里有音**不在**这个和弦内 −0.55 —— 惩罚「装不下」的和弦，
 *     否则 C 大调的歌每一段都会被判成 C（因为它最"包容"）
 */
function scoreOf(pcs, root, third) {
  const tones = [root, (root + third) % 12, (root + 7) % 12]
  let s = 0
  for (const [pc, w] of pcs) {
    if (pc === root) s += w * 1.8
    else if (tones.includes(pc)) s += w * 1.0
    else s -= w * 0.55
  }
  return s
}

/** 把一串音符按「时间窗 + 停顿」切成若干片，每片推出一个和弦 */
function sliceWindows(list, winSec, gapBreak) {
  const out = []
  let cur = []
  let t0 = 0
  for (const n of list) {
    const prev = cur[cur.length - 1]
    if (cur.length && (n.time - t0 >= winSec || n.time - prev.time > gapBreak)) {
      out.push(cur)
      cur = []
    }
    if (!cur.length) t0 = n.time
    cur.push(n)
  }
  if (cur.length) out.push(cur)
  return out
}

/** 一个时间窗内：统计音级权重，选出最匹配的和弦 */
function bestChord(bucket) {
  const counts = new Map()
  let sum = 0
  for (const n of bucket) {
    const m = n.midi
    if (!Number.isFinite(m)) continue
    const pc = ((m % 12) + 12) % 12
    counts.set(pc, (counts.get(pc) || 0) + 1)
    sum += m
  }
  if (!counts.size) return null

  const pcs = [...counts.entries()]
  let best = null
  for (let root = 0; root < 12; root++) {
    // 根音必须真的在这段里出现过 —— 这一条能排除 90% 的怪和弦
    // （否则 F# 大三和弦可能在某段"零命中"却因为不被惩罚而胜出）
    if (!counts.has(root)) continue
    for (const third of [THIRD_MAJOR, THIRD_MINOR]) {
      const s = scoreOf(pcs, root, third)
      if (!best || s > best.score) best = { root, third, score: s }
    }
  }
  if (!best) return null

  const avg = sum / bucket.length
  return {
    root: best.root,
    minor: best.third === THIRD_MINOR,
    name: PC_NAME[best.root] + (best.third === THIRD_MINOR ? 'm' : ''),
    avgMidi: avg,
    weight: bucket.length,
  }
}

/**
 * 和弦的实际音高：三和弦 3 个音 + 一个低八度根音当"左手"。
 *
 * 低八度根音为什么音量给 0.55：不加它和弦听起来飘，
 * 跟三音一样响又会糊成一团（尤其钢琴采样低频本来就厚）。
 */
function voicingOf(root, minor, avgMidi) {
  // 让根音落在「这段旋律的平均音高」附近，而不是固定 C3
  let rootMidi = root + 12 * Math.floor((avgMidi - root) / 12)
  if (rootMidi - avgMidi > 6) rootMidi -= 12

  const third = minor ? THIRD_MINOR : THIRD_MAJOR
  const midis = [
    { midi: rootMidi, vel: 0.78 },
    { midi: rootMidi + third, vel: 0.7 },
    { midi: rootMidi + 7, vel: 0.7 },
  ]
  // C3(48) 是采样下限，再低就没声音了，直接不给低八度
  if (rootMidi - 12 >= 48) midis.unshift({ midi: rootMidi - 12, vel: 0.55 })
  return midis
}

/**
 * 主入口：音符流 → 和弦流。
 *
 * @param {Array<{time:number, midi?:number, key?:string}>} notes 曲谱音符（需按时间升序）
 * @param {{winSec?:number, gapBreak?:number, maxKeys?:number}} opts
 * @returns {{chords:Array, keyMap:Object, baseShift:number}} keyMap: 键 → {name, midis}
 */
export function deriveChords(notes, opts = {}) {
  const winSec = opts.winSec ?? 2.2
  const gapBreak = opts.gapBreak ?? 0.9
  const maxKeys = opts.maxKeys ?? CHORD_KEY_POOL.length

  if (!Array.isArray(notes) || !notes.length) return { chords: [], keyMap: {}, skipped: 0 }

  const list = notes
    .filter((n) => Number.isFinite(n?.time))
    .map((n) => ({ ...n, midi: midiOf(n) }))
    .filter((n) => Number.isFinite(n.midi))
    .sort((a, b) => a.time - b.time)
  if (!list.length) return { chords: [], keyMap: {}, skipped: 0 }

  // 1) 切片 → 每片一个和弦
  const raw = []
  for (const bucket of sliceWindows(list, winSec, gapBreak)) {
    const c = bestChord(bucket)
    if (!c) continue
    const t = bucket[0].time
    // 相邻同一和弦合并：否则「C C C C」会连着占四个格子，谱面看着像坏掉了
    const last = raw[raw.length - 1]
    if (last && last.root === c.root && last.minor === c.minor) {
      last.end = bucket[bucket.length - 1].time
      last.weight += c.weight
      continue
    }
    raw.push({ ...c, time: t, end: bucket[bucket.length - 1].time })
  }
  if (!raw.length) return { chords: [], keyMap: {}, skipped: 0 }

  // 2) 分配键位：**先让键名和和弦名对上**，剩下的按频率补
  //
  // 为什么不是纯按频率：纯频率会出现「F 和弦要按 G 键」「Am 要按 S 键」，
  // 看着谱子找键时脑子里要绕一道弯。实测兰亭序 8 个和弦里能有 6 个对上首字母
  // （F→F、G→G、Am→A、Em→E、Dm→D…），剩下 C / D / E 才落到别的键。
  // 代价是 C（最高频）可能拿不到最好的位置 —— 对"按对才前进"的玩法来说，
  // 少绕弯比手速重要，所以这个取舍是有意的。
  const freq = new Map()
  for (const c of raw) freq.set(c.name, (freq.get(c.name) || 0) + c.weight)
  const byFreq = [...freq.entries()].sort((a, b) => b[1] - a[1]).map(([n]) => n)

  const used = new Set()
  const keyOf = new Map()
  for (const name of byFreq) {
    const initial = name[0].toUpperCase()
    if (CHORD_KEY_POOL.includes(initial) && !used.has(initial)) {
      keyOf.set(name, initial)
      used.add(initial)
    }
  }
  for (const name of byFreq) {
    if (keyOf.has(name)) continue
    if (keyOf.size >= maxKeys) break
    const k = CHORD_KEY_POOL.find((x) => !used.has(x))
    if (!k) break
    keyOf.set(name, k)
    used.add(k)
  }

  // 3) 补音高、写键位；超出键位池的（极少）挂到已用键里最接近的那个，不丢音
  const chords = []
  for (const c of raw) {
    const key = keyOf.get(c.name) || CHORD_KEY_POOL[0]
    chords.push({
      time: c.time,
      end: c.end,
      root: c.root,
      minor: c.minor,
      name: c.name,
      key,
      midis: voicingOf(c.root, c.minor, c.avgMidi),
    })
  }

  const keyMap = {}
  for (const c of chords) {
    if (!keyMap[c.key]) keyMap[c.key] = { name: c.name, midis: c.midis }
  }

  return { chords, keyMap, chordCount: byFreq.length }
}
