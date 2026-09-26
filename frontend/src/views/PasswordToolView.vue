<template>
  <IslandInnerBase type="tool" title="随机密码" subtitle="本地生成 · 即时复制 · 不落库">
    <div class="pw-tool">
      <div class="pw-head">
        <span class="pw-badge">🔒 在浏览器本地生成，不经过服务器、不落库、不上传。</span>
      </div>

      <!-- 结果展示 -->
      <div class="pw-result">
        <code class="pw-value" :class="{ weak: strength.level <= 1 }">{{ password || '—' }}</code>
        <button class="pw-icon-btn" title="重新生成" aria-label="重新生成" @click="generate">↻</button>
        <button class="pw-icon-btn" title="复制" aria-label="复制密码" @click="copy">⧉</button>
      </div>
      <div class="pw-strength">
        <div class="pw-meter">
          <i :style="{ width: strength.percent + '%', background: strength.color }"></i>
        </div>
        <span class="pw-strength-text" :style="{ color: strength.color }">
          {{ strength.label }} · 约 {{ entropy }} bits 熵
        </span>
      </div>

      <!-- 选项 -->
      <div class="pw-options">
        <label class="pw-opt">长度
          <b class="hl">{{ length }}</b>
          <input v-model.number="length" type="range" min="6" max="64" step="1" @input="generate">
        </label>
        <div class="pw-classes">
          <label v-for="c in classes" :key="c.key" class="pw-check">
            <input v-model="c.on" type="checkbox" @change="generate">
            <span>{{ c.label }}</span>
            <code class="pw-sample">{{ c.sample }}</code>
          </label>
          <label class="pw-check">
            <input v-model="excludeSimilar" type="checkbox" @change="generate">
            <span>排除易混淆字符</span>
            <code class="pw-sample">0O1lI|</code>
          </label>
        </div>
        <div v-if="error" class="pw-err">{{ error }}</div>
      </div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import { ElMessage } from 'element-plus'

const classes = ref([
  { key: 'lower', label: '小写字母', sample: 'a-z', on: true, chars: 'abcdefghijklmnopqrstuvwxyz' },
  { key: 'upper', label: '大写字母', sample: 'A-Z', on: true, chars: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' },
  { key: 'digit', label: '数字', sample: '0-9', on: true, chars: '0123456789' },
  { key: 'special', label: '特殊字符', sample: '!@#$', on: true, chars: '!@#$%^&*()-_=+[]{};:,.<>?/~' },
])
const length = ref(16)
const excludeSimilar = ref(false)
const password = ref('')
const error = ref('')

const SIMILAR = new Set([...('0O1lI|')])

const entropy = computed(() => {
  const pool = activePool().length
  return pool ? Math.round(length.value * Math.log2(pool)) : 0
})

const strength = computed(() => {
  const bits = entropy.value
  if (bits >= 100) return { level: 4, label: '极强', color: '#1aa86a', percent: 100 }
  if (bits >= 75) return { level: 3, label: '强', color: '#7fb8a0', percent: 75 }
  if (bits >= 50) return { level: 2, label: '中', color: '#e2b93b', percent: 50 }
  return { level: 1, label: '弱', color: '#e5484d', percent: 25 }
})

function activePool() {
  let pool = ''
  for (const c of classes.value) {
    if (!c.on) continue
    let chars = c.chars
    if (excludeSimilar.value) chars = [...chars].filter(ch => !SIMILAR.has(ch)).join('')
    pool += chars
  }
  return [...new Set(pool)].join('')
}

/** crypto.getRandomValues：拒绝采样避免取模偏差 */
function randomInt(max) {
  const g = window.crypto || window.msCrypto
  const limit = Math.floor(0xffffffff / max) * max
  const buf = new Uint32Array(1)
  let v
  do { g.getRandomValues(buf); v = buf[0] } while (v >= limit)
  return v % max
}

function generate() {
  error.value = ''
  const pool = activePool()
  if (!pool) {
    password.value = ''
    error.value = '至少选择一种字符类型'
    return
  }
  if (length.value < 6 || length.value > 64) {
    error.value = '长度需在 6 ~ 64 之间'
    return
  }
  const arr = Array.from({ length: length.value }, () => pool[randomInt(pool.length)])
  password.value = arr.join('')
}

async function copy() {
  if (!password.value) return
  try {
    await navigator.clipboard.writeText(password.value)
    ElMessage.success('已复制（剪贴板约 30s 后建议自行清空）')
  } catch {
    ElMessage.warning('复制失败，请手动选择复制')
  }
}

onMounted(generate)
</script>

<style scoped>
.pw-head { margin-bottom: 14px; }
.pw-badge {
  display: inline-block; font-size: 12.5px; padding: 8px 14px; border-radius: 10px;
  background: rgba(127, 168, 163, 0.12); color: var(--dp-text2, #45505b); line-height: 1.6;
}
.pw-result {
  display: flex; align-items: center; gap: 10px;
  padding: 16px 18px; border-radius: 14px;
  background: var(--dp-bg2, rgba(0,0,0,.03)); border: 1px solid var(--dp-line, rgba(0,0,0,.08));
}
.pw-value {
  flex: 1; font-family: var(--font-mono, ui-monospace, Menlo, monospace);
  font-size: 17px; letter-spacing: .04em; word-break: break-all; line-height: 1.5;
  color: var(--dp-text, #18202a);
}
.pw-value.weak { color: #e5484d; }
.pw-icon-btn {
  flex: none; width: 38px; height: 38px; border-radius: 10px; font-size: 17px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff);
  color: var(--dp-text2, #45505b); transition: background .15s;
}
.pw-icon-btn:hover { background: rgba(199,169,107,.14); }
.pw-strength { display: flex; align-items: center; gap: 12px; margin-top: 10px; }
.pw-meter {
  flex: 1; height: 6px; border-radius: 999px; overflow: hidden;
  background: var(--dp-bg2, rgba(0,0,0,.06));
}
.pw-meter i { display: block; height: 100%; border-radius: 999px; transition: width .3s; }
.pw-strength-text { font-size: 12.5px; flex: none; }
.pw-options { margin-top: 18px; display: flex; flex-direction: column; gap: 14px; }
.pw-opt { display: flex; align-items: center; gap: 12px; font-size: 13.5px; color: var(--dp-text2, #45505b); }
.pw-opt input[type=range] { flex: 1; max-width: 320px; }
.hl { color: var(--yq-gold, #c7a96b); font-size: 15px; }
.pw-classes { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; }
.pw-check {
  display: flex; align-items: center; gap: 8px; font-size: 13.5px; cursor: pointer;
  padding: 10px 12px; border-radius: 10px;
  background: var(--dp-bg2, rgba(0,0,0,.03)); border: 1px solid var(--dp-line, rgba(0,0,0,.08));
  color: var(--dp-text, #18202a);
}
.pw-check input { accent-color: var(--yq-gold, #c7a96b); }
.pw-sample { margin-left: auto; font-size: 11px; color: var(--dp-text3, #8a8f98); }
.pw-err { color: #e5484d; font-size: 13px; }
</style>
