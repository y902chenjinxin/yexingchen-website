/**
 * 钢琴键位表（v2.46.334）
 *
 * 一个"指哪打哪"的固定布局，演奏页、曲谱转换器、曲库管理三处共用同一份，
 * 任何一边改了这里，另外两边自动跟着变 —— 不要在任何地方再写一遍 midi 数字。
 *
 * 音域：C3(48) ~ F5(77)，正好 18 个白键 + 10 个黑键。
 *
 *  白键  低八度  A  S  D  F  G  H  J   K  L     = C3 D3 E3 F3 G3 A3 B3 C4 D4
 *        高八度  Q  W  E  R  T  Y  U   I  O     = E4 F4 G4 A4 B4 C5 D5 E5 F5
 *  黑键  1 2 3 4 5   = C#3 D#3 F#3 G#3 A#3
 *        6 7 8 9 0   = C#4 D#4 F#4 G#4 A#4
 *
 * ⚠️ 夜星定的是「数字键 1~7 做黑键」，但两个八度共有 10 个黑键，1~7 只够一组半。
 *    这里扩到 1~0（十个数字键），刚好两整组，且不影响字母区的手感。
 *    未覆盖的只有 C#5 / D#5（最高那半个八度），转换器遇到会把那个音降八度折回来
 *    —— 八度平移不改调性，所以听起来仍是原调。
 */

export const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

/** 白键：[按键字母, MIDI 音高]，按音高升序 */
export const WHITE_KEYS = [
  ['A', 48], ['S', 50], ['D', 52], ['F', 53], ['G', 55], ['H', 57], ['J', 59],
  ['K', 60], ['L', 62],
  ['Q', 64], ['W', 65], ['E', 67], ['R', 69], ['T', 71], ['Y', 72], ['U', 74], ['I', 76], ['O', 77],
]

/** 黑键：[按键字符, MIDI 音高]，数字键 1~0 对应两组升降音 */
export const BLACK_KEYS = [
  ['1', 49], ['2', 51], ['3', 54], ['4', 56], ['5', 58],
  ['6', 61], ['7', 63], ['8', 66], ['9', 68], ['0', 70],
]

/** MIDI → 按键字母（找不到就按八度折叠，最多折 3 次） */
const BY_MIDI = new Map([...WHITE_KEYS, ...BLACK_KEYS].map(([k, m]) => [m, k]))
export function midiToKey(midi) {
  let m = midi
  for (let i = 0; i < 4; i++) {
    const hit = BY_MIDI.get(m)
    if (hit) return hit
    m -= 12
  }
  for (let i = 0; i < 4; i++) {
    m = midi + 12 * (i + 1)
    const hit = BY_MIDI.get(m)
    if (hit) return hit
  }
  return null
}

export const KEY_TO_MIDI = new Map([...WHITE_KEYS, ...BLACK_KEYS].map(([k, m]) => [k, m]))

/**
 * 物理键盘事件 → MIDI 音高。
 *
 * 用 `event.code` 而不是 `event.key`：
 *   · 中文输入法开着时 `key` 可能是 'Process'；
 *   · 按住 Shift 时 '1' 会变成 '!'；
 *   · 不同键盘布局（法语 AZERTY）字母位置全变，code 才是物理位置。
 */
export function codeToMidi(code) {
  if (!code) return null
  if (code.startsWith('Key')) {
    const letter = code.slice(3)
    const hit = KEY_TO_MIDI.get(letter)
    return hit ?? null
  }
  if (code.startsWith('Digit')) {
    const digit = code.slice(5)
    const hit = KEY_TO_MIDI.get(digit)
    return hit ?? null
  }
  // 主键盘数字区以外的（小键盘 Numpad1）不映射，避免误判
  return null
}

/** 音名（给 UI 显示音高用） */
export function midiName(midi) {
  return NOTE_NAMES[((midi % 12) + 12) % 12] + (Math.floor(midi / 12) - 1)
}

/** 音域范围，导入时用来判断是否需要整体移调 */
export const RANGE = { min: 48, max: 77 }

/**
 * 白键在黑键之间的排布：用于算每个白键的横向位置。
 * 返回白键序号（0..17），黑键返回 null。
 */
export const WHITE_INDEX = new Map(WHITE_KEYS.map(([k], i) => [k, i]))

/**
 * 按总宽度算出每个键的横向位置（白键等分，黑键骑在两个白键之间）。
 *
 * 演奏页的下落轨道和键盘必须用**同一次计算**，否则音符会飘在键的右边半个格 —— 
 * 这类错位在开发时看不出（差 20px 而已），玩家按下去会觉得"我明明按对了"。
 *
 * @param {number} width 键盘总宽（px）
 * @returns {{whiteW:number, blackW:number, pos:Map<string,{x:number,w:number,black:boolean}>}}
 */
export function keyLayout(width) {
  const whiteW = width / WHITE_KEYS.length
  const blackW = whiteW * 0.62
  const pos = new Map()
  WHITE_KEYS.forEach(([k], i) => {
    pos.set(k, { x: i * whiteW, w: whiteW, black: false })
  })
  const whiteMidiIndex = new Map(WHITE_KEYS.map(([, m], i) => [m, i]))
  for (const [k, m] of BLACK_KEYS) {
    // 黑键永远骑在「下方白键」的右边缘上：C#3 骑在 C3 上
    const i = whiteMidiIndex.get(m - 1)
    if (i == null) continue
    pos.set(k, { x: (i + 1) * whiteW - blackW / 2, w: blackW, black: true })
  }
  return { whiteW, blackW, pos }
}

/**
 * 简谱表示（v2.46.336）
 *
 * MIDI → { deg: '1'..'7', acc: ''|'#', oct: -1|0|1 }
 *   · deg 用唱名（C=1 D=2 E=3 F=4 G=5 A=6 B=7），黑键加 # 前缀（#1 = C#）
 *   · oct 是相对 C4 的八度偏移：<0 下面点、>0 上面点（简谱的通行写法）
 */
const SOLFEGE = { 0: '1', 2: '2', 4: '3', 5: '4', 7: '5', 9: '6', 11: '7' }
export function solfege(midi) {
  const pc = ((midi % 12) + 12) % 12
  const oct = Math.floor(midi / 12) - 5      // C4(60) → 0
  const natural = SOLFEGE[pc]
  if (natural) return { deg: natural, acc: '', oct }
  // 黑键：取下方音的升号写法（#1 / #2 / #4 / #5 / #6）
  const lower = Object.keys(SOLFEGE).map(Number).filter((k) => k < pc).sort((a, b) => b - a)[0]
  return { deg: SOLFEGE[lower], acc: '#', oct }
}
