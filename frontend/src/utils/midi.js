/**
 * 极简 MIDI 解析器（v2.46.334）
 *
 * 只做我们需要的事：从 .mid 里取出「每个音的开始时刻、音高、时长」。
 * 不依赖任何库（@tonejs/midi 要 40KB，为这个功能不值）。
 *
 * 支持：format 0 / 1、running status、多轨、tempo 变化（0x51）、
 *       note on/off（含 velocity=0 视作 off）。
 * 不支持：format 2（极少见）、SMPTE 时间码（用不到）。
 *
 * ⚠️ running status 必须支持：大量 .mid 从 Cubase/FL 导出时会把重复的状态字节省掉，
 *    不处理的话第二个音开始就全部解析错位，表现为「只有前两个音对，后面全是噪音」。
 */

/** 读变长整数（MIDI 的 delta time 编码） */
function readVarLen(dv, state) {
  let v = 0
  for (let i = 0; i < 4; i++) {
    const b = dv.getUint8(state.p++)
    v = (v << 7) | (b & 0x7f)
    if (!(b & 0x80)) break
  }
  return v
}

function readStr(dv, state, n) {
  let s = ''
  for (let i = 0; i < n; i++) s += String.fromCharCode(dv.getUint8(state.p + i))
  state.p += n
  return s
}

/**
 * @param {ArrayBuffer} buf
 * @returns {{format:number, division:number, tracks:Array, tempos:Array}}
 */
export function parseMidi(buf) {
  const dv = new DataView(buf)
  const state = { p: 0 }

  if (readStr(dv, state, 4) !== 'MThd') throw new Error('不是 MIDI 文件（缺少 MThd）')
  const headLen = dv.getUint32(state.p); state.p += 4
  const format = dv.getUint16(state.p); state.p += 2
  const ntrks = dv.getUint16(state.p); state.p += 2
  const division = dv.getUint16(state.p); state.p += 2
  state.p += headLen - 6   // 头部可能有多余字节

  if (division & 0x8000) throw new Error('不支持 SMPTE 时间码的 MIDI')

  const tracks = []
  const tempos = []        // [{tick, usPerQuarter}]
  let guard = 0

  while (state.p < dv.byteLength - 7 && tracks.length < ntrks && guard++ < 200) {
    const id = readStr(dv, state, 4)
    const size = dv.getUint32(state.p); state.p += 4
    const end = state.p + size
    if (id !== 'MTrk') { state.p = end; continue }

    const notes = []
    const open = new Map()   // `${ch}:${midi}` → {tick, vel}
    let tick = 0
    let running = 0

    while (state.p < end) {
      tick += readVarLen(dv, state)
      let status = dv.getUint8(state.p)

      if (status === 0xff) {
        state.p++
        const type = dv.getUint8(state.p); state.p++
        const len = readVarLen(dv, state)
        if (type === 0x51 && len === 3) {
          const us = (dv.getUint8(state.p) << 16) | (dv.getUint8(state.p + 1) << 8) | dv.getUint8(state.p + 2)
          tempos.push({ tick, usPerQuarter: us })
        }
        state.p += len
        if (type === 0x2f) break
        continue
      }
      if (status === 0xf0 || status === 0xf7) {
        state.p++
        const len = readVarLen(dv, state)
        state.p += len
        continue
      }

      if (status & 0x80) {
        state.p++
        running = status
      } else {
        status = running          // running status：沿用上一个状态字节
        if (!status) { state.p++; continue }
      }

      const type = status & 0xf0
      const ch = status & 0x0f

      if (type === 0x90 || type === 0x80) {
        const midi = dv.getUint8(state.p)
        const vel = dv.getUint8(state.p + 1)
        state.p += 2
        const k = `${ch}:${midi}`
        if (type === 0x90 && vel > 0) {
          // 同音重复按下：把上一个先收掉（钢琴不可能同时发同一个音两次）
          const prev = open.get(k)
          if (prev) notes.push({ tick: prev.tick, midi, dur: tick - prev.tick, vel: prev.vel, ch })
          open.set(k, { tick, vel })
        } else {
          const prev = open.get(k)
          if (prev) {
            notes.push({ tick: prev.tick, midi, dur: Math.max(1, tick - prev.tick), vel: prev.vel, ch })
            open.delete(k)
          }
        }
      } else if (type === 0xc0 || type === 0xd0) {
        state.p += 1
      } else {
        state.p += 2
      }
    }

    // 轨尾还没松开的音，给一个默认时长（否则会整段丢失）
    if (open.size) {
      for (const [k, v] of open) {
        notes.push({ tick: v.tick, midi: Number(k.split(':')[1]), dur: Math.max(1, tick - v.tick), vel: v.vel, ch: Number(k.split(':')[0]) })
      }
    }

    tracks.push({ notes })
    state.p = end
  }

  return { format, division, tracks, tempos }
}

/**
 * tick → 秒。按 tempo 分段积分：曲中变速的 MIDI 直接除固定 BPM 会整段错位。
 * @returns {(tick:number)=>number}
 */
export function makeTickToSec(division, tempos) {
  const list = (tempos.length ? [...tempos] : [{ tick: 0, usPerQuarter: 500000 }])
    .sort((a, b) => a.tick - b.tick)
  const segs = []
  let acc = 0
  for (let i = 0; i < list.length; i++) {
    const t = list[i]
    const next = list[i + 1]?.tick ?? Infinity
    const secPerTick = t.usPerQuarter / 1e6 / division
    segs.push({ from: t.tick, to: next, at: acc, secPerTick })
    if (next !== Infinity) acc += (next - t.tick) * secPerTick
  }
  return (tick) => {
    for (let i = segs.length - 1; i >= 0; i--) {
      if (tick >= segs[i].from) return segs[i].at + (tick - segs[i].from) * segs[i].secPerTick
    }
    return tick * segs[0].secPerTick
  }
}
