<template>
  <IslandInnerBase type="tool" title="人脉图谱" subtitle="通讯录关系可视化 · 本地布局">
    <div class="map-tool">
      <div class="mt-head">
        <span class="mt-badge">数据来自「家人通讯录」（{{ nodes.length }} 人），布局与绘制全在本机完成。</span>
      </div>

      <div class="mt-canvas-wrap">
        <canvas ref="cvEl" width="900" height="620" class="mt-canvas" @pointerdown="onDown" @pointermove="onMove" @pointerup="onUp"></canvas>
        <div v-if="!nodes.length && !loading" class="mt-empty">通讯录还是空的 —— 先去添加几位家人。</div>
      </div>

      <div v-if="selected" class="mt-detail glass-card">
        <b>{{ selected.name }}</b>
        <span class="mt-rel">{{ selected.relation || '未标注关系' }}</span>
        <span v-if="selected.phone">📞 {{ selected.phone }}</span>
        <span v-if="selected.birthday">🎂 {{ selected.birthday }}</span>
        <span v-if="selected.address">📍 {{ selected.address }}</span>
        <button class="mt-close" @click="selected = null">关闭</button>
      </div>
      <div class="mt-hint">拖动节点可重新布局 · 点击节点查看详情 · 连线 = 同关系分类</div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import api from '@/api/index'

const cvEl = ref(null)
const nodes = reactive([])
const selected = ref(null)
const loading = ref(true)

let rafId = 0
let dragNode = null

async function load() {
  try {
    // 拦截器 return response.data → {code,msg,data}
    const body = await api.get('/contacts', { params: { size: 500 } })
    const list = body?.data?.list || body?.data || []
    buildGraph(Array.isArray(list) ? list : [])
  } catch { /* 静默 */ } finally { loading.value = false }
}

function buildGraph(list) {
  nodes.length = 0
  const W = 900, H = 620
  const byRelation = {}
  list.forEach((p) => {
    const rel = (p.relation || '').trim() || '其他'
    if (!byRelation[rel]) byRelation[rel] = []
    byRelation[rel].push(p)
  })
  const rels = Object.keys(byRelation)
  rels.forEach((rel, ri) => {
    const angle = (ri / rels.length) * Math.PI * 2
    const cx = W / 2 + Math.cos(angle) * 240
    const cy = H / 2 + Math.sin(angle) * 200
    byRelation[rel].forEach((p, pi) => {
      const a = (pi / byRelation[rel].length) * Math.PI * 2
      nodes.push({
        id: p.id, name: p.name, relation: rel, phone: p.phone,
        birthday: p.birthday, address: p.address,
        x: cx + Math.cos(a) * 60, y: cy + Math.sin(a) * 50,
        vx: 0, vy: 0, r: 22,
      })
    })
  })
  start()
}

function start() {
  cancelAnimationFrame(rafId)
  const step = () => {
    physics()
    draw()
    rafId = requestAnimationFrame(step)
  }
  step()
}

function physics() {
  // 斥力（节点间）
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i], b = nodes[j]
      const dx = b.x - a.x, dy = b.y - a.y
      const d2 = dx * dx + dy * dy || 1
      const d = Math.sqrt(d2)
      if (d < 90) {
        const f = (90 - d) / d * 0.6
        a.vx -= dx * f; a.vy -= dy * f
        b.vx += dx * f; b.vy += dy * f
      }
    }
  }
  // 同关系聚拢 + 向心
  for (const n of nodes) {
    const same = nodes.filter(m => m.relation === n.relation && m !== n)
    if (same.length) {
      const cx = same.reduce((s, m) => s + m.x, 0) / same.length
      const cy = same.reduce((s, m) => s + m.y, 0) / same.length
      n.vx += (cx - n.x) * 0.02
      n.vy += (cy - n.y) * 0.02
    }
    n.vx += (450 - n.x) * 0.0015
    n.vy += (310 - n.y) * 0.0015
    if (n !== dragNode) { n.x += n.vx; n.y += n.vy }
    n.vx *= 0.85; n.vy *= 0.85
    n.x = Math.max(30, Math.min(870, n.x))
    n.y = Math.max(30, Math.min(590, n.y))
  }
}

function draw() {
  const cv = cvEl.value
  if (!cv) return
  const ctx = cv.getContext('2d')
  ctx.clearRect(0, 0, 900, 620)

  // 同关系之间的连线
  ctx.strokeStyle = 'rgba(127,168,163,.25)'
  ctx.lineWidth = 1
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      if (nodes[i].relation === nodes[j].relation) {
        ctx.beginPath()
        ctx.moveTo(nodes[i].x, nodes[i].y)
        ctx.lineTo(nodes[j].x, nodes[j].y)
        ctx.stroke()
      }
    }
  }

  // 节点
  const palette = ['#c7a96b', '#7fa8a3', '#a97142', '#8e6a9e', '#5f8fb4', '#b06a5e']
  const relColor = {}
  nodes.forEach(n => {
    if (!relColor[n.relation]) relColor[n.relation] = palette[Object.keys(relColor).length % palette.length]
  })
  for (const n of nodes) {
    ctx.beginPath()
    ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2)
    ctx.fillStyle = n === selected.value ? 'rgba(199,169,107,.95)' : relColor[n.relation]
    ctx.fill()
    ctx.fillStyle = '#fff'
    ctx.font = '600 13px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(n.name.slice(0, 3), n.x, n.y + 4.5)
  }
  // 关系中心标注
  for (const [rel, color] of Object.entries(relColor)) {
    const group = nodes.filter(n => n.relation === rel)
    const cx = group.reduce((s, n) => s + n.x, 0) / group.length
    const cy = group.reduce((s, n) => s + n.y, 0) / group.length
    ctx.fillStyle = color
    ctx.font = '700 13px sans-serif'
    ctx.fillText(rel, cx, cy - group[0].r - 10)
  }
}

function pick(e) {
  const rect = cvEl.value.getBoundingClientRect()
  const x = (e.clientX - rect.left) * (900 / rect.width)
  const y = (e.clientY - rect.top) * (620 / rect.height)
  return nodes.find(n => (n.x - x) ** 2 + (n.y - y) ** 2 <= n.r ** 2 + 40)
}
function onDown(e) {
  dragNode = pick(e) || null
  if (dragNode) { selected.value = dragNode; cvEl.value.setPointerCapture(e.pointerId) }
  else selected.value = null
}
function onMove(e) {
  if (!dragNode) return
  const rect = cvEl.value.getBoundingClientRect()
  dragNode.x = (e.clientX - rect.left) * (900 / rect.width)
  dragNode.y = (e.clientY - rect.top) * (620 / rect.height)
}
function onUp() { dragNode = null }

onMounted(load)
onBeforeUnmount(() => cancelAnimationFrame(rafId))
</script>

<style scoped>
.mt-head { margin-bottom: 12px; }
.mt-badge {
  display: inline-block; font-size: 12.5px; padding: 8px 14px; border-radius: 10px;
  background: rgba(127, 168, 163, 0.12); color: var(--dp-text2, #45505b); line-height: 1.6;
}
.mt-canvas-wrap { position: relative; }
.mt-canvas {
  width: 100%; max-width: 900px; border-radius: 14px; touch-action: none;
  border: 1px solid var(--dp-line, rgba(0,0,0,.08)); background:
    radial-gradient(circle at 30% 20%, rgba(127,168,163,.06), transparent 50%),
    var(--dp-bg2, rgba(0,0,0,.02));
}
.mt-empty { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: var(--dp-text3, #8a8f98); font-size: 13.5px; }
.mt-detail {
  margin-top: 14px; padding: 14px 18px; display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  font-size: 14px; color: var(--dp-text, #18202a);
}
.mt-rel { color: var(--yq-gold, #c7a96b); font-weight: 600; }
.mt-close {
  margin-left: auto; padding: 5px 14px; border-radius: 8px; font-size: 12px; cursor: pointer;
  border: 1px solid var(--dp-line, rgba(0,0,0,.14)); background: var(--dp-surface, #fff); color: var(--dp-text2, #45505b);
}
.mt-hint { margin-top: 10px; font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
</style>
