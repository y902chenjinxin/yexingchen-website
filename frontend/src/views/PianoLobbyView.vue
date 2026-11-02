<template>
  <IslandInnerBase type="tool" title="音乐造物主" subtitle="不懂乐理也能弹出整首歌 · 键盘按下即发声">
    <div class="pl">
      <!-- 手机端不做：这里只提示，进去也弹不了（没有物理键盘，18 键在 390px 上按不准） -->
      <div v-if="narrow" class="pl-tip glass">
        <b>请到电脑上体验</b>
        <p>演奏需要实体键盘（<kbd>A~L</kbd> / <kbd>Q~O</kbd> / <kbd>1~0</kbd>），手机上没有足够的按键区域。曲库可以在这里管理。</p>
        <button class="pl-btn" type="button" @click="$router.push('/tool/songs')">打开曲库管理</button>
      </div>

      <template v-else>
        <!-- ===== 大厅：乐器卡片 ===== -->
        <section v-if="step === 'hall'" class="pl-hall">
          <button class="pl-inst glass" type="button" @click="step = 'songs'">
            <span class="pl-inst-art" aria-hidden="true">
              <i v-for="i in 14" :key="i" class="pl-inst-key" :style="{ '--i': i }" />
              <i v-for="b in blackPos" :key="'b' + b" class="pl-inst-bkey" :style="{ '--x': b }" />
            </span>
            <span class="pl-inst-body">
              <b class="pl-inst-name">钢琴</b>
              <span class="pl-inst-desc">采样三角钢琴 · 28 键 · 24 音复音</span>
              <span class="pl-inst-go">进入 →</span>
            </span>
          </button>

          <p class="pl-note">
            先在「曲库」里放几首歌，再回来挑一首弹。音符会从上方落下来，
            落到底线时按下对应的字母就行 —— 按错不扣分，漏了也不打断。
          </p>

          <button class="pl-btn ghost" type="button" @click="$router.push('/tool/songs')">
            管理曲库（上传 MIDI / JSON）
          </button>
        </section>

        <!-- ===== 选曲 ===== -->
        <section v-else class="pl-songs">
          <div class="pl-bar">
            <button class="pl-back" type="button" @click="step = 'hall'">← 乐器</button>
            <input v-model="kw" class="pl-search" type="search" placeholder="搜索曲名 / 歌手" />
            <button class="pl-btn ghost sm" type="button" @click="$router.push('/tool/songs')">曲库管理</button>
          </div>

          <div v-if="loading" class="pl-empty">正在读取曲库…</div>

          <div v-else-if="!songs.length" class="pl-empty">
            <p>曲库还是空的</p>
            <button class="pl-btn" type="button" @click="$router.push('/tool/songs')">去上传第一首</button>
          </div>

          <ul v-else class="pl-list">
            <li v-for="s in filtered" :key="s.id" class="pl-item glass" @click="play(s)">
              <span class="pl-item-art" aria-hidden="true"><AppIcon icon="🎹" :size="20" /></span>
              <span class="pl-item-main">
                <b>{{ s.title }}</b>
                <span class="pl-item-meta">
                  <em v-if="s.artist">{{ s.artist }}</em>
                  <em>{{ s.bpm }} BPM</em>
                  <em>{{ s.note_count }} 音</em>
                  <em>{{ fmtDur(s.duration) }}</em>
                </span>
              </span>
              <button class="pl-item-play" type="button" @click.stop="play(s)">演奏</button>
            </li>
            <li v-if="!filtered.length" class="pl-empty small">没有匹配的曲目</li>
          </ul>
        </section>
      </template>
    </div>
  </IslandInnerBase>
</template>

<script setup>
/**
 * 音乐造物主 · 大厅 + 选曲（v2.46.334）
 *
 * 三段式里前两段合并在一个内页（大厅 ↔ 选曲用 step 切换，不跳路由）：
 *   · 大厅只有一样东西可选（钢琴），单独做成一个路由反而多两次跳转；
 *   · 选曲要能搜索、能看时长，放内页有侧栏与返回，比全屏好用；
 *   · 真正需要沉浸的只有演奏页，它有自己的全屏路由。
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import { getSongs } from '@/api/songs'

const router = useRouter()

const step = ref('hall')          // hall | songs
const songs = ref([])
const loading = ref(false)
const kw = ref('')

/** 黑键在 14 个白键之间的位置（百分比，纯粹为了画那个小图示） */
const blackPos = [1, 2, 4, 5, 6, 8, 9, 11, 12, 13].map((i) => (i * (100 / 14)).toFixed(3) + '%')

const narrow = ref(false)
let mq = null
const onMq = (e) => { narrow.value = e.matches }

const filtered = computed(() => {
  const q = kw.value.trim().toLowerCase()
  if (!q) return songs.value
  return songs.value.filter((s) =>
    (s.title || '').toLowerCase().includes(q) || (s.artist || '').toLowerCase().includes(q))
})

function fmtDur(sec) {
  const s = Math.max(0, Math.round(sec || 0))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

function play(s) {
  router.push(`/piano/${s.id}`)
}

async function load() {
  loading.value = true
  try {
    const res = await getSongs()
    songs.value = res?.data?.items || []
  } catch {
    songs.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  mq = window.matchMedia('(max-width: 900px)')
  narrow.value = mq.matches
  mq.addEventListener('change', onMq)
  if (!narrow.value) load()
})
onBeforeUnmount(() => mq?.removeEventListener('change', onMq))
</script>

<style scoped>
.pl {
  --pl-card: var(--color-bg-glass, rgba(255, 255, 255, .06));
  --pl-line: var(--glass-border, color-mix(in srgb, var(--ls-text) 14%, transparent));
  --pl-ink: var(--ls-text);
  --pl-dim: var(--ls-text-3);
  max-width: 720px;
  margin: 0 auto;
  padding-bottom: 24px;
}

.pl-tip { padding: 22px; border-radius: 16px; border: 1px solid var(--pl-line); background: var(--pl-card); }
.pl-tip b { font-size: 16px; color: var(--pl-ink); }
.pl-tip p { margin: 8px 0 16px; font-size: 13px; line-height: 1.8; color: var(--pl-dim); }
.pl-tip kbd {
  padding: 1px 6px; border-radius: 5px; font-family: inherit; font-size: 12px;
  border: 1px solid var(--pl-line); background: color-mix(in srgb, var(--ls-text) 8%, transparent);
}

/* ---------- 大厅 ---------- */
.pl-hall { display: flex; flex-direction: column; gap: 16px; }
.pl-inst {
  display: flex; align-items: center; gap: 20px; width: 100%;
  padding: 20px; border-radius: 18px; cursor: pointer; text-align: left;
  border: 1px solid var(--pl-line);
  background: var(--pl-card);
  -webkit-backdrop-filter: var(--glass-blur, blur(16px) saturate(160%));
  backdrop-filter: var(--glass-blur, blur(16px) saturate(160%));
  transition: transform .16s ease, border-color .16s ease, box-shadow .2s ease;
}
.pl-inst:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--color-accent) 55%, transparent);
  box-shadow: 0 16px 34px -22px color-mix(in srgb, var(--color-accent) 90%, transparent);
}
.pl-inst:active { transform: translateY(0) scale(.995); }
.pl-inst-art {
  position: relative; flex: none; width: 132px; height: 78px;
  border-radius: 8px; overflow: hidden;
  background: linear-gradient(180deg, #2a2622, #14120f);
  box-shadow: inset 0 -8px 14px -10px #000;
}
.pl-inst-key {
  position: absolute; top: 0; bottom: 0; width: calc(100% / 14);
  left: calc((var(--i) - 1) * (100% / 14));
  background: linear-gradient(180deg, #fdfcf9, #e8e1d3);
  border-right: 1px solid rgba(0, 0, 0, .18);
  border-radius: 0 0 3px 3px;
}
.pl-inst-bkey {
  position: absolute; top: 0; height: 60%; width: 5.2%;
  left: calc(var(--x) - 2.6%);
  background: linear-gradient(180deg, #3a3733, #0d0c0b);
  border-radius: 0 0 3px 3px;
}
.pl-inst-body { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
.pl-inst-name { font-size: 19px; font-weight: 800; color: var(--pl-ink); letter-spacing: .02em; }
.pl-inst-desc { font-size: 12.5px; color: var(--pl-dim); }
.pl-inst-go {
  margin-top: 4px; font-size: 12.5px; font-weight: 700;
  color: var(--color-accent);
}
.pl-note { margin: 0; font-size: 12.5px; line-height: 1.9; color: var(--pl-dim); }

/* ---------- 选曲 ---------- */
.pl-songs { display: flex; flex-direction: column; gap: 12px; }
.pl-bar { display: flex; align-items: center; gap: 10px; }
.pl-back {
  flex: none; height: 34px; padding: 0 12px; border-radius: 10px; cursor: pointer;
  border: 1px solid var(--pl-line); background: transparent; color: var(--pl-dim); font-size: 13px;
}
.pl-back:hover { color: var(--pl-ink); }
.pl-search {
  flex: 1; min-width: 0; height: 38px; padding: 0 14px; border-radius: 11px;
  border: 1px solid var(--pl-line); background: color-mix(in srgb, var(--ls-text) 6%, transparent);
  color: var(--pl-ink); font-size: 14px; outline: none;
}
.pl-search:focus { border-color: var(--color-accent); }

.pl-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.pl-item {
  display: flex; align-items: center; gap: 14px; padding: 12px 14px;
  border-radius: 14px; border: 1px solid var(--pl-line); cursor: pointer;
  transition: border-color .16s ease, transform .16s ease, background-color .16s ease;
}
.pl-item:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--color-accent) 50%, transparent);
  background: color-mix(in srgb, var(--color-accent) 8%, transparent);
}
.pl-item-art {
  flex: none; width: 38px; height: 38px; border-radius: 11px;
  display: grid; place-items: center;
  background: color-mix(in srgb, var(--ls-text) 8%, transparent);
}
.pl-item-main { display: flex; flex-direction: column; gap: 4px; min-width: 0; flex: 1; }
.pl-item-main b { font-size: 14.5px; color: var(--pl-ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pl-item-meta { display: flex; gap: 10px; font-size: 11.5px; color: var(--pl-dim); }
.pl-item-meta em { font-style: normal; }
.pl-item-play {
  flex: none; height: 30px; padding: 0 14px; border-radius: 9px; cursor: pointer;
  border: 1px solid color-mix(in srgb, var(--color-accent) 60%, transparent);
  background: transparent; color: var(--color-accent); font-size: 13px; font-weight: 700;
}
.pl-item-play:hover { background: var(--color-accent); color: #2c1d04; }

.pl-empty {
  padding: 40px 16px; text-align: center; font-size: 13.5px; color: var(--pl-dim);
  display: flex; flex-direction: column; align-items: center; gap: 14px;
}
.pl-empty.small { padding: 18px; font-size: 12.5px; }

.pl-btn {
  padding: 10px 20px; border-radius: 11px; cursor: pointer; font-size: 13.5px; font-weight: 600;
  border: 1px solid var(--pl-line); background: transparent; color: var(--pl-ink);
}
.pl-btn:hover { background: color-mix(in srgb, var(--ls-text) 8%, transparent); }
.pl-btn.sm { height: 34px; padding: 0 12px; font-size: 12.5px; }
.pl-btn.ghost { align-self: flex-start; }
</style>
