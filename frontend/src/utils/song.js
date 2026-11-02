/**
 * 曲谱规范化（v2.46.334）
 *
 * MIDI → 本站曲谱 JSON：
 *   { songName, bpm, notes: [{ time, key, pitch, dur }] }
 *
 * 关键判断：**从多轨里挑出「主旋律」**。流行曲 MIDI 一般是
 *   轨 1 主旋律 / 轨 2 钢琴伴奏（和弦） / 轨 3 贝斯 / 轨 4 鼓。
 * 直接全量合并会让下落轨道同时出现七八个音，根本没法弹。
 *
 * 挑法（打分，不靠"第几条轨"）：
 *   · 音符越多越像旋律（伴奏一小节才几个和弦）
 *   · 越"单音"越像旋律（和弦轨同时按 3~4 个音）
 *   · 音高越高越像旋律（旋律基本在伴奏上面）
 * 三个因子相乘，取最高分 —— 对绝大多数流行 MIDI 都成立。
 */
import { parseMidi, makeTickToSec } from './midi'
import { midiToKey, midiName, RANGE } from './pianoKeys'

/** 打乱速度：把同一条轨的两两重叠比例算出来（0 = 纯单音，1 = 全是和弦） */
function overlapRatio(notes) {
  if (notes.length < 3) return 0
  let overlapped = 0
  for (let i = 1; i < notes.length; i++) {
    if (notes[i].tick < notes[i - 1].tick + notes[i - 1].dur) overlapped++
  }
  return overlapped / notes.length
}

function trackScore(notes) {
  if (!notes.length) return -1
  const mono = 1 - overlapRatio(notes)
  const avg = notes.reduce((s, n) => s + n.midi, 0) / notes.length
  return notes.length * (0.35 + 0.65 * mono) * (1 + (avg - 60) / 100)
}

/** 从解析结果里挑主旋律轨；返回按时间排序的音符 */
function pickMelody(parsed) {
  const cands = parsed.tracks
    .map((t) => ({ notes: t.notes.filter((n) => n.ch !== 9), score: 0 }))   // 9 = 鼓
    .filter((t) => t.notes.length >= 4)
  if (!cands.length) return []
  for (const c of cands) c.score = trackScore(c.notes)
  cands.sort((a, b) => b.score - a.score)
  return [...cands[0].notes].sort((a, b) => a.tick - b.tick)
}

/**
 * @param {ArrayBuffer} arrayBuffer .mid 内容
 * @param {{name?:string, artist?:string, maxNotes?:number}} opts
 */
export function buildSongFromMidi(arrayBuffer, opts = {}) {
  const parsed = parseMidi(arrayBuffer)
  const melody = pickMelody(parsed)
  if (!melody.length) throw new Error('这个 MIDI 里没有找到旋律轨')

  const usList = (parsed.tempos.length ? parsed.tempos : [{ usPerQuarter: 500000 }])
    .map((t) => t.usPerQuarter)
    .sort((a, b) => a - b)
  const bpm = Math.round(60e6 / usList[Math.floor(usList.length / 2)])
  const tickToSec = makeTickToSec(parsed.division, parsed.tempos)

  // 量化到 16 分音符：MIDI 里通常有 5~20ms 的人手偏差，不量化下落位置会参差不齐
  const step = 60 / Math.max(40, Math.min(220, bpm)) / 4
  const raw = melody
    .map((n) => ({
      t: Math.round(tickToSec(n.tick) / step) * step,
      midi: n.midi,
      dur: Math.max(step, Math.round(tickToSec(n.dur) / step) * step),
    }))
    .filter((n) => Number.isFinite(n.t))

  // 同一时刻的音合成和弦：保留多个键，但去掉重复键
  const byTime = new Map()
  for (const n of raw) {
    const k = n.t.toFixed(3)
    if (!byTime.has(k)) byTime.set(k, [])
    byTime.get(k).push(n)
  }

  const notes = []
  for (const [k, group] of [...byTime.entries()].sort((a, b) => Number(a[0]) - Number(b[0]))) {
    const used = new Set()
    for (const n of group.sort((a, b) => a.midi - b.midi)) {
      // 超出音域的整段没用，midiToKey 会按八度折叠回来（八度平移不改调性）
      const key = midiToKey(n.midi)
      if (!key || used.has(key)) continue
      used.add(key)
      notes.push({
        time: Math.round(Number(k) * 1000) / 1000,
        key,
        pitch: midiName(n.midi),
        dur: Math.round(n.dur * 1000) / 1000,
      })
    }
    if (notes.length > (opts.maxNotes || 4000)) break
  }
  if (!notes.length) throw new Error('旋律里的音都落在可弹音域之外')

  return {
    songName: opts.name || '',
    artist: opts.artist || '',
    bpm,
    notes,
    meta: {
      source: 'midi',
      trackNotes: melody.length,
      range: [Math.min(...raw.map((n) => n.midi)), Math.max(...raw.map((n) => n.midi))],
      generatedAt: new Date().toISOString(),
    },
  }
}

/** 上传 JSON 时的校验：只认本站结构，别让坏数据把演奏页搞崩 */
export function validateSong(obj) {
  if (!obj || typeof obj !== 'object') return '不是合法的 JSON 对象'
  if (!Array.isArray(obj.notes) || !obj.notes.length) return '缺少 notes 数组'
  if (obj.notes.length > 6000) return '音符超过 6000 个，太大了'
  for (let i = 0; i < Math.min(obj.notes.length, 50); i++) {
    const n = obj.notes[i]
    if (typeof n?.time !== 'number' || !Number.isFinite(n.time)) return `第 ${i + 1} 个音符缺少 time`
    if (typeof n?.key !== 'string' || !n.key) return `第 ${i + 1} 个音符缺少 key`
  }
  return ''
}

/** 曲长（秒） */
export function songDuration(song) {
  if (!song?.notes?.length) return 0
  return Math.max(...song.notes.map((n) => n.time + (n.dur || 0)))
}

export { RANGE }
