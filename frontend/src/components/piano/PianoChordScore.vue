<template>
  <div ref="host" class="cs" :style="sizeVars">
    <div class="cs-inner">
      <p v-if="!chords.length" class="cs-empty">
        这段旋律音太少，推不出和弦（换「看谱弹」吧）
      </p>

      <div v-for="(line, li) in lines" :key="li" class="cs-line">
        <button
          class="cs-line-no"
          type="button"
          :title="`从第 ${line.start + 1} 个和弦开始`"
          @click="$emit('pick', line.start)"
        >{{ li + 1 }}</button>

        <div class="cs-cells">
          <button
            v-for="c in line.items"
            :key="c.i"
            type="button"
            class="cs-cell"
            :class="{ on: c.i === active, done: c.i < active, 'bar-end': c.barEnd }"
            :title="`${c.name} · 按 ${c.key} 键（一次响 ${c.tones} 个音）`"
            @click="$emit('pick', c.i)"
          >
            <span class="cs-name">{{ c.name }}</span>
            <span class="cs-key">{{ c.key }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 和弦谱视图（v2.46.338）
 *
 * 夜星：「我觉得好难啊，是不是吉他简单一点」—— 难的不是乐器，是
 * 「1 个动作只换 1 个音」（兰亭序 4.8 音/秒）。吉他之所以显得容易，
 * 是因为「按一个和弦、扫一下 = 3~4 个音同时响」。
 *
 * 所以这里把和弦流摊成谱：一个格子 = 一个和弦 = 一个键。
 * 按下去三四个音一起响，节奏由自己掌控，按错只是不前进。
 */
import { computed, nextTick, onMounted, ref, watch } from 'vue'

const props = defineProps({
  chords: { type: Array, default: () => [] },
  active: { type: Number, default: -1 },
})
defineEmits(['pick'])

const host = ref(null)

/**
 * 每行 6 个格子。
 *
 * 为什么是 6 而不是 8：和弦名比单个数字宽（"Am" / "Dm"），
 * 1440 宽下每格约 170px 正好；8 个会把字压小、还要缩键位字母。
 * 每行 4 个的第 4 格后加一条细线当「小节」的视觉锚点（真正的拍号我们没有）。
 */
const PER_LINE = 6
const BAR_EVERY = 4

const lines = computed(() => {
  const out = []
  for (let i = 0; i < props.chords.length; i += PER_LINE) {
    const items = props.chords.slice(i, i + PER_LINE).map((c, k) => ({
      i: i + k,
      name: c.name,
      key: c.key,
      tones: c.midis?.length || 3,
      barEnd: (k + 1) % BAR_EVERY === 0 && k < PER_LINE - 1,
    }))
    out.push({ start: i, items })
  }
  return out
})

/**
 * 格子尺寸跟着行数走。
 *
 * 为什么不用固定值：短曲（小星星 9 个和弦 = 2 行）固定 82px 时，
 * 整片谱子在 500px 高的舞台里缩成中间一条，上下各一大片黑，看着像没加载完。
 * 行数少就放大格子（占住视觉重量），行数多就回到紧凑尺寸（保证一屏能看 5~6 行）。
 */
const sizeVars = computed(() => {
  const n = lines.value.length
  if (n <= 2) return { '--cs-minh': '124px', '--cs-fs': '38px', '--cs-key-fs': '13px' }
  if (n <= 3) return { '--cs-minh': '100px', '--cs-fs': '34px', '--cs-key-fs': '12.5px' }
  return { '--cs-minh': '82px', '--cs-fs': '31px', '--cs-key-fs': '12px' }
})

/** 当前和弦滚进视口（只在看不见时才滚，不抢手动翻页） */
watch(() => props.active, async (i) => {
  if (i < 0) return
  await nextTick()
  const el = host.value?.querySelector('.cs-cell.on')
  if (!el) return
  const box = host.value.getBoundingClientRect()
  const r = el.getBoundingClientRect()
  if (r.top < box.top + 40 || r.bottom > box.bottom - 40) {
    el.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }
})

onMounted(() => {
  const first = host.value?.querySelector('.cs-cell.on')
  if (first) first.scrollIntoView({ block: 'center' })
})
</script>

<style scoped>
.cs {
  height: 100%;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 6px 4px 14px;
  scrollbar-width: thin;
  display: flex; flex-direction: column;
}
/* 内容少时居中；居中放内层（给滚动容器 justify-content:center 会裁掉顶部） */
.cs-inner { margin-block: auto; width: 100%; }
.cs-empty { padding: 30px; text-align: center; color: rgba(242, 237, 228, .45); font-size: 13px; }

.cs-line { display: flex; align-items: stretch; gap: 12px; padding: 9px 0; }
.cs-line + .cs-line { border-top: 1px dashed rgba(255, 255, 255, .07); }

.cs-line-no {
  flex: none; align-self: center;
  width: 22px; height: 22px;
  border-radius: 6px; cursor: pointer;
  border: 1px solid rgba(255, 255, 255, .12);
  background: transparent;
  color: rgba(242, 237, 228, .42);
  font-size: 11px; line-height: 1;
}
.cs-line-no:hover { color: #ffe1a0; border-color: rgba(255, 225, 160, .5); }

.cs-cells {
  flex: 1 1 auto; min-width: 0;
  /* 🔴 用 grid 不用 flex：flex + `flex:1 1 0` 会让**最后一行不满时**把剩下的格子
     均分铺满（9 个和弦 = 第一行 6 个 + 第二行 3 个，那 3 个各占 1/3 屏，宽得像三张海报）。
     grid 固定 6 列，空位就空着，每格宽度始终与上一行一致。 */
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 9px;
}

.cs-cell {
  position: relative;
  min-width: 0; min-height: var(--cs-minh, 82px);
  justify-content: center;
  display: flex; flex-direction: column; align-items: center; gap: 3px;
  padding: 10px 8px 8px;
  border-radius: 11px; cursor: pointer;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, .045);
  color: rgba(242, 237, 228, .78);
  transition: background-color .16s ease, color .16s ease, transform .16s ease;
}
.cs-cell:hover { background: rgba(255, 255, 255, .1); color: #fff; }
/* 弹过的压暗，视线自然落到当前格 */
.cs-cell.done { opacity: .36; }
/* 每 4 格一道细线，当「小节」的视觉锚点（真拍号我们没有，只是别让一行糊成一片）。
   🔴 线画在 ::after 上、不占布局（不要用 margin-right：那会把这一格挤窄 9px，
   一行里出现一个窄格，边界不齐很难看）。gap 是 9px，所以中线在 -5px。 */
.cs-cell.bar-end::after {
  content: '';
  position: absolute;
  right: -5px; top: 14%; bottom: 14%;
  width: 1px;
  background: rgba(255, 255, 255, .2);
}

/* 当前该按的和弦：鎏金实心 + 抬起。只是"建议"，按别的和弦键照样响 */
.cs-cell.on {
  background: linear-gradient(180deg, #ffe9b8, #eec463);
  color: #33230a;
  border-color: #fff2cf;
  transform: translateY(-2px);
  box-shadow: 0 8px 18px -9px rgba(255, 205, 120, .95);
}

.cs-name {
  font-size: var(--cs-fs, 31px); font-weight: 800; line-height: 1.1;
  letter-spacing: .01em; font-variant-numeric: tabular-nums;
}
.cs-key {
  font-size: var(--cs-key-fs, 12px); line-height: 1; opacity: .6; letter-spacing: .06em;
  padding: 3px 8px; border-radius: 6px;
  border: 1px solid currentColor;
}
.cs-cell.on .cs-key { opacity: .7; }
</style>
