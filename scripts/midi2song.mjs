/**
 * MIDI → 曲谱 JSON 批量转换（v2.46.334）
 *
 * 这套逻辑和网页里「曲库 → 上传 .mid」用的是**同一份代码**
 * （frontend/src/utils/{midi,song}.js），所以本脚本产出什么，
 * 网页上传就产出什么，不会出现"脚本转的能玩、网页传的不能玩"。
 *
 * 用法：
 *   # 转换单个文件 / 整个文件夹
 *   node scripts/midi2song.mjs "D:/Desktop/midi" "D:/Desktop/songs"
 *
 *   # 只做自检（不需要任何素材）
 *   node scripts/midi2song.mjs --selftest
 *
 * ⚠️ 这个仓库是 CJS 环境（frontend/package.json 没有 type:module），
 *    而 src/utils/*.js 是 ESM。直接用 node 跑会报 "Cannot use import statement"。
 *    所以每次都先 esbuild 打一次包：
 *
 *   cd frontend && npx esbuild ../scripts/midi2song.mjs --bundle --platform=node \
 *     --format=esm --outfile=.tmp/m2s.mjs && node .tmp/m2s.mjs --selftest
 */
import fs from 'node:fs'
import path from 'node:path'
import { buildSongFromMidi } from '../frontend/src/utils/song.js'

/* ---------------- 自检用的最小 MIDI 生成器（只在 --selftest 用） ---------------- */

function encVar(n) {
  const out = [n & 0x7f]
  n >>= 7
  while (n > 0) {
    out.unshift((n & 0x7f) | 0x80)
    n >>= 7
  }
  return out
}

function chunk(id, body) {
  const head = [...id].map((c) => c.charCodeAt(0))
  const len = body.length
  return [...head, (len >> 24) & 0xff, (len >> 16) & 0xff, (len >> 8) & 0xff, len & 0xff, ...body]
}

/** 生成一个双轨 MIDI：轨 1 单音旋律（高），轨 2 和弦伴奏（低） */
function buildTestMidi() {
  const division = 480
  const header = chunk('MThd', [0, 1, 0, 2, (division >> 8) & 0xff, division & 0xff])

  const tempo = chunk('MTrk', [0x00, 0xff, 0x51, 0x03, 0x07, 0xa1, 0x20, 0x00, 0xff, 0x2f, 0x00]) // 120bpm

  // 旋律：C4 D4 E4 F4，每个 480 tick；最后跑一个 running status 音符验证解析
  const mel = []
  let last = 0
  const push = (tick, ...bytes) => {
    mel.push(...encVar(tick - last), ...bytes)
    last = tick
  }
  const pitches = [60, 62, 64, 65]
  pitches.forEach((p, i) => {
    const on = i * 480
    const off = on + 460
    push(on, 0x90, p, 0x64)
    push(off, 0x80, p, 0x40)
  })
  // 第五个音用 running status（省略状态字节），考验解析器
  push(2400, 0x90, 67, 0x64)
  push(2880, 0x80, 67, 0x40)
  push(2880, 0xff, 0x2f, 0x00)
  const melody = chunk('MTrk', mel)

  // 伴奏：C 大三和弦（48/52/55），时值 4 拍
  const acc = []
  let l2 = 0
  for (const p of [48, 52, 55]) {
    acc.push(...encVar(0), 0x90, p, 0x50)
    l2 = 0
  }
  acc.push(...encVar(1920), 0x80, 48, 0x40)
  acc.push(...encVar(0), 0x80, 52, 0x40)
  acc.push(...encVar(0), 0x80, 55, 0x40)
  acc.push(...encVar(0), 0xff, 0x2f, 0x00)
  const accomp = chunk('MTrk', acc)

  void l2
  return new Uint8Array([...header, ...tempo, ...melody, ...accomp]).buffer
}

function selftest() {
  const buf = buildTestMidi()
  const song = buildSongFromMidi(buf, { name: '自检曲' })
  const keys = song.notes.map((n) => n.key).join('')
  const want = 'KLQW'   // C4=K D4=L E4=Q F4=W（键位表见 utils/pianoKeys.js）
  const problems = []
  if (song.bpm !== 120) problems.push(`bpm 应为 120，实际 ${song.bpm}`)
  if (song.notes.length !== 5) problems.push(`音符数应为 5，实际 ${song.notes.length}`)
  if (!keys.startsWith(want)) problems.push(`前四个键应为 ${want}，实际 ${keys}`)
  if (song.notes[4]?.key !== 'E') problems.push(`running status 那个音（G4）应映射到 E，实际 ${song.notes[4]?.key}`)
  const times = song.notes.map((n) => n.time)
  const expect = [0, 0.5, 1, 1.5, 2.5]
  for (let i = 0; i < expect.length; i++) {
    if (Math.abs(times[i] - expect[i]) > 0.01) problems.push(`第 ${i + 1} 个音时间应为 ${expect[i]}s，实际 ${times[i]}s`)
  }
  if (problems.length) {
    console.log('❌ 自检失败：')
    problems.forEach((p) => console.log('   · ' + p))
    process.exit(1)
  }
  console.log(`✅ 自检通过：bpm=${song.bpm}，音符 ${song.notes.length} 个，键序 ${keys}，时间 ${times.join(', ')}`)
}

/* ---------------- 批量转换 ---------------- */

function convert(file, outDir) {
  const buf = fs.readFileSync(file)
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength)
  const base = path.basename(file, path.extname(file))
  const song = buildSongFromMidi(ab, { name: base })
  song.songName = base
  const out = path.join(outDir, `${base}.json`)
  fs.writeFileSync(out, JSON.stringify(song, null, 2), 'utf8')
  const kb = (fs.statSync(out).size / 1024).toFixed(1)
  console.log(`✓ ${base}  bpm=${song.bpm}  音符 ${song.notes.length}  时长≈${(song.notes.at(-1).time).toFixed(1)}s  ${kb}KB`)
  return out
}

const args = process.argv.slice(2)
if (args.includes('--selftest')) {
  selftest()
} else {
  const input = args[0]
  const outDir = args[1] || path.join(process.env.USERPROFILE || process.env.HOME || '.', 'Desktop', 'songs')
  if (!input) {
    console.log('用法：node midi2song.mjs <mid 文件或目录> [输出目录]')
    process.exit(1)
  }
  fs.mkdirSync(outDir, { recursive: true })
  const files = []
  const stat = fs.statSync(input)
  if (stat.isDirectory()) {
    for (const f of fs.readdirSync(input)) {
      if (/\.(mid|midi)$/i.test(f)) files.push(path.join(input, f))
    }
  } else {
    files.push(input)
  }
  if (!files.length) {
    console.log('没有找到 .mid / .midi 文件')
    process.exit(1)
  }
  console.log(`输出目录：${outDir}\n`)
  let ok = 0
  for (const f of files) {
    try {
      convert(f, outDir)
      ok++
    } catch (e) {
      console.log(`✗ ${path.basename(f)}：${e.message}`)
    }
  }
  console.log(`\n完成 ${ok}/${files.length}`)
}
