<template>
  <div ref="host" class="ps">
    <div class="ps-inner">
    <p v-if="!phrases.length" class="ps-empty">这份曲谱是空的</p>

    <div v-for="(line, li) in phrases" :key="li" class="ps-line">
      <button
        class="ps-line-no"
        type="button"
        :title="`从第 ${li + 1} 句开始`"
        @click="$emit('pick', line.start)"
      >{{ li + 1 }}</button>

      <div class="ps-notes">
        <button
          v-for="n in line.items"
          :key="n.i"
          type="button"
          class="ps-note"
          :class="{ on: n.i === active, done: n.i < active }"
          :title="`${n.pitch} · 按 ${n.key}`"
          @click="$emit('pick', n.i)"
        >
          <span class="ps-deg">
            <i v-if="n.oct > 0" class="ps-dot ps-dot--up" />
            <b><em v-if="n.acc">{{ n.acc }}</em>{{ n.deg }}</b>
            <i v-if="n.oct < 0" class="ps-dot ps-dot--down" />
          </span>
          <span class="ps-key">{{ n.key }}</span>
        </button>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 简谱视图（v2.46.336）
 *
 * 夜星要的是「明确的曲谱 + 不赶时间 + 弹错也行」，不是节奏游戏。
 * 所以这里把音符排成**一句一行**的简谱，自己看着慢慢按，没有时间轴逼你。
 *
 * 断句不是按小节（光遇稿没有可靠小节信息），而是按**时间停顿**：
 * 相邻音的间隔超过中位间隔的 2.2 倍，就当一句说完。流行歌的换气和乐句
 * 基本都落在这种停顿上，读起来比"每 4 拍硬切"自然。
 */
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { solfege, KEY_TO_MIDI } from '@/utils/pianoKeys'

const props = defineProps({
  notes: { type: Array, default: () => [] },
  active: { type: Number, default: -1 },
})
defineEmits(['pick'])

const host = ref(null)

/** 每个音预计算简谱显示 */
const items = computed(() => props.notes.map((n, i) => {
  // pitch 形如 "C4" / "C#4"；统一转 MIDI 再算简谱，避免两套解析
  const m = /^([A-G])(#?)(-?\d+)$/.exec(n.pitch || '')
  let midi = null
  if (m) {
    const base = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 }[m[1]]
    midi = (Number(m[3]) + 1) * 12 + base + (m[2] ? 1 : 0)
  }
  // 没写 pitch 的曲谱（例如示例曲）就退回按键反查，别显示成问号
  if (midi == null) midi = KEY_TO_MIDI.get(n.key) ?? null
  const s = midi == null ? { deg: '?', acc: '', oct: 0 } : solfege(midi)
  return { i, key: n.key, pitch: n.pitch || '', deg: s.deg, acc: s.acc, oct: s.oct, t: n.time }
}))

/** 一句一行：按停顿断句，同时给行长封顶，避免出现一条几屏长的行 */
const phrases = computed(() => {
  const list = items.value
  if (!list.length) return []
  const gaps = []
  for (let i = 1; i < list.length; i++) gaps.push(list[i].t - list[i - 1].t)
  const sorted = [...gaps].sort((a, b) => a - b)
  const median = sorted[Math.floor(sorted.length / 2)] || 0.4
  const brk = Math.max(0.75, median * 2.2)

  const out = []
  let cur = []
  for (let i = 0; i < list.length; i++) {
    cur.push(list[i])
    const gap = i + 1 < list.length ? list[i + 1].t - list[i].t : Infinity
    if (gap > brk || cur.length >= 8 || i === list.length - 1) {
      out.push({ start: cur[0].i, items: cur })
      cur = []
    }
  }
  return out
})

/** 当前音滚到可视区中间（不抢用户手动滚动：只在超出视口时滚） */
watch(() => props.active, async (i) => {
  if (i < 0) return
  await nextTick()
  const el = host.value?.querySelector('.ps-note.on')
  if (!el) return
  const box = host.value.getBoundingClientRect()
  const r = el.getBoundingClientRect()
  if (r.top < box.top + 40 || r.bottom > box.bottom - 40) {
    el.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }
})

onMounted(() => {
  const first = host.value?.querySelector('.ps-note.on')
  if (first) first.scrollIntoView({ block: 'center' })
})
</script>

<style scoped>
.ps {
  height: 100%;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 6px 4px 14px;
  scrollbar-width: thin;
  display: flex; flex-direction: column;
}
/* 内容少（只有两三个乐句）时整体居中，别把谱子吊在顶上留一大片黑 */
.ps-inner { margin-block: auto; width: 100%; }
.ps-empty { padding: 30px; text-align: center; color: rgba(242, 237, 228, .45); font-size: 13px; }

.ps-line {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 7px 0;
}
.ps-line + .ps-line { border-top: 1px dashed rgba(255, 255, 255, .07); }
.ps-line-no {
  flex: none;
  width: 22px; height: 22px; margin-top: 4px;
  border-radius: 6px; cursor: pointer;
  border: 1px solid rgba(255, 255, 255, .12);
  background: transparent;
  color: rgba(242, 237, 228, .42);
  font-size: 11px; line-height: 1;
}
.ps-line-no:hover { color: #ffe1a0; border-color: rgba(255, 225, 160, .5); }

.ps-notes { display: flex; flex-wrap: wrap; gap: 6px; }

.ps-note {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  min-width: 44px; padding: 6px 9px 5px;
  border-radius: 9px; cursor: pointer;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, .045);
  color: rgba(242, 237, 228, .72);
  transition: background-color .16s ease, color .16s ease, transform .16s ease;
}
.ps-note:hover { background: rgba(255, 255, 255, .1); color: #fff; }
/* 已经弹过的一句：压暗，视线自然落到当前音上 */
.ps-note.done { opacity: .38; }
/* 当前建议按的音：鎏金高亮 + 轻微抬起。**只是建议**，按别的键照样出声 */
.ps-note.on {
  background: linear-gradient(180deg, #ffe9b8, #eec463);
  color: #33230a;
  border-color: #fff2cf;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px -8px rgba(255, 205, 120, .9);
}

.ps-deg { position: relative; font-size: 23px; font-weight: 800; line-height: 1.1; }
.ps-deg b { font-weight: 800; }
.ps-deg em { font-style: normal; font-size: 15px; margin-right: 1px; opacity: .8; }
/* 简谱的高低八度点 */
.ps-dot {
  position: absolute; left: 50%; width: 4px; height: 4px; margin-left: -2px;
  border-radius: 50%; background: currentColor;
}
.ps-dot--up { top: -7px; }
.ps-dot--down { bottom: -6px; }

.ps-key { font-size: 11.5px; line-height: 1; opacity: .6; letter-spacing: .04em; }
</style>
