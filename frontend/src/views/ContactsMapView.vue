<template>
  <IslandInnerBase type="tool" title="人脉图谱" subtitle="通讯录亲缘关系图 · 本地布局">
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

      <div class="mt-legend">
        <span class="mt-lg"><i class="mt-line self"></i>本人直系（父母 / 兄弟姐妹 / 子女）</span>
        <span class="mt-lg"><i class="mt-line spouse"></i>配偶一侧（岳家 / 婆家）</span>
        <span class="mt-lg"><i class="mt-line dash"></i>朋友 / 未归类</span>
      </div>
      <div class="mt-hint">拖动节点可重新布局 · 点击节点查看详情</div>
    </div>
  </IslandInnerBase>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import IslandInnerBase from '@/views/islands/IslandInnerBase.vue'
import api from '@/api/index'

const W = 900, H = 620

/**
 * 关系 → 角色。
 * 通讯录的 `relation` 是自由文本：下拉里的预设选项（父亲/母亲/爷爷…）与实际在用的
 * 口语化写法（老婆/丈母娘/大姨姐/小舅子）都要认，所以映射表写得比较全。
 */
const ROLE_BY_RELATION = {
  自己: 'self', 本人: 'self', 我: 'self',
  老婆: 'spouse', 妻子: 'spouse', 太太: 'spouse', 夫人: 'spouse', 爱人: 'spouse',
  老公: 'spouse', 丈夫: 'spouse', 配偶: 'spouse',
  父亲: 'parent', 母亲: 'parent', 爸爸: 'parent', 妈妈: 'parent', 爹: 'parent', 娘: 'parent',
  老爸: 'parent', 老妈: 'parent', 父母: 'parent',
  哥哥: 'sibling', 姐姐: 'sibling', 弟弟: 'sibling', 妹妹: 'sibling',
  哥: 'sibling', 姐: 'sibling', 弟: 'sibling', 妹: 'sibling', 兄弟: 'sibling', 姐妹: 'sibling',
  儿子: 'child', 女儿: 'child', 孩子: 'child', 宝宝: 'child', 闺女: 'child',
  丈人: 'inlaw_parent', 丈母娘: 'inlaw_parent', 岳父: 'inlaw_parent', 岳母: 'inlaw_parent',
  公公: 'inlaw_parent', 婆婆: 'inlaw_parent', 岳父岳母: 'inlaw_parent',
  大姨姐: 'inlaw_sibling', 大姨子: 'inlaw_sibling', 小姨子: 'inlaw_sibling',
  姨姐: 'inlaw_sibling', 姨妹: 'inlaw_sibling',
  大舅子: 'inlaw_sibling', 小舅子: 'inlaw_sibling', 舅哥: 'inlaw_sibling', 舅弟: 'inlaw_sibling',
  大伯子: 'inlaw_sibling', 小叔子: 'inlaw_sibling', 大姑子: 'inlaw_sibling', 小姑子: 'inlaw_sibling',
  爷爷: 'grand', 奶奶: 'grand', 外公: 'grand', 外婆: 'grand', 姥姥: 'grand', 姥爷: 'grand',
  孙子: 'grandchild', 孙女: 'grandchild', 外孙: 'grandchild', 外孙女: 'grandchild',
  伯父: 'uncle', 伯母: 'uncle', 叔叔: 'uncle', 婶婶: 'uncle', 姑姑: 'uncle', 姑父: 'uncle',
  舅舅: 'uncle', 舅妈: 'uncle', 姨妈: 'uncle', 姨父: 'uncle',
  朋友: 'friend', 同事: 'friend', 同学: 'friend', 其他亲戚: 'other', 其他: 'other',
}

/**
 * 每个角色的「语义锚点」（力导向的起始位 + 稳态吸引位）：
 * 父母在上、配偶在右、子女在下、配偶的双亲/兄弟姐妹在配偶更外侧 —— 一眼能看出亲疏结构。
 */
const ROLE_ANCHOR = {
  self: { x: 450, y: 300 },
  spouse: { x: 660, y: 300, gapY: 95 },
  parent: { x: 450, y: 118, gapX: 122 },
  grand: { x: 148, y: 105, gapY: 78 },
  sibling: { x: 248, y: 205, gapY: 84 },
  uncle: { x: 235, y: 405, gapY: 84 },
  child: { x: 450, y: 480, gapX: 122 },
  inlaw_parent: { x: 768, y: 126, gapY: 84 },
  inlaw_sibling: { x: 768, y: 408, gapY: 84 },
  grandchild: { x: 645, y: 545, gapX: 104 },
  friend: { x: 135, y: 545, gapY: 76 },
  other: { x: 325, y: 560, gapY: 76 },
}

const ROLE_COLOR = {
  self: '#c7a96b',
  spouse: '#d9a94f',
  parent: '#7fa8a3',
  sibling: '#5f8fb4',
  child: '#5fa07f',
  inlaw_parent: '#8e6a9e',
  inlaw_sibling: '#a97142',
  uncle: '#9a8f6b',
  grand: '#8c93a3',
  grandchild: '#4f9273',
  friend: '#9aa0a6',
  other: '#9aa0a6',
}

const cvEl = ref(null)
const nodes = reactive([])
const selected = ref(null)
const loading = ref(true)

let edges = []
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

function roleOf(relation) {
  return ROLE_BY_RELATION[(relation || '').trim()] || 'other'
}

function buildGraph(list) {
  nodes.length = 0
  edges = []

  const withRole = list.map((p) => {
    const relation = (p.relation || '').trim()
    return { p, relation: relation || '未标注', role: roleOf(relation) }
  })

  // 同角色按锚点排开（自己居中，其余围绕锚点分布）
  const byRole = {}
  withRole.forEach((it) => { (byRole[it.role] ||= []).push(it) })
  Object.entries(byRole).forEach(([role, group]) => {
    const a = ROLE_ANCHOR[role] || ROLE_ANCHOR.other
    group.forEach((it, i) => {
      const off = i - (group.length - 1) / 2
      const x = a.x + off * (a.gapX || 0)
      const y = a.y + off * (a.gapY || 0)
      nodes.push({
        id: it.p.id, name: it.p.name, relation: it.relation, role,
        phone: it.p.phone, birthday: it.p.birthday, address: it.p.address,
        home: { x, y },
        x, y, vx: 0, vy: 0, r: role === 'self' ? 27 : 23,
      })
    })
  })

  edges = buildEdges(nodes)
  start()
}

/** 按亲缘关系连线：配偶、父母、兄弟姐妹、子女挂「本人」；岳家/婆家挂「配偶」 */
function buildEdges(ns) {
  const out = []
  const byRole = {}
  ns.forEach((n) => { (byRole[n.role] ||= []).push(n) })

  const self = byRole.self?.[0] || null
  const spouse = byRole.spouse?.[0] || null
  // 没录「自己」时用配偶当轴心，再退化到第一个人，避免整张图散掉
  const hub = self || spouse || ns[0]

  const link = (a, b, kind) => {
    if (!a || !b || a === b) return
    if (out.some((e) => (e.a === a && e.b === b) || (e.a === b && e.b === a))) return
    out.push({ a, b, kind })
  }

  if (self && spouse) link(self, spouse, 'self')
  ;['parent', 'sibling', 'child'].forEach((r) => (byRole[r] || []).forEach((n) => link(hub, n, 'self')))

  const inlaws = [...(byRole.inlaw_parent || []), ...(byRole.inlaw_sibling || [])]
  inlaws.forEach((n) => link(spouse || hub, n, spouse ? 'spouse' : 'self'))

  // 祖辈挂到对应那一系的父母（爷爷/奶奶→父系；外公/外婆→母系），找不到再退回轴心
  const father = (byRole.parent || []).find((n) => /父|爸|爹/.test(n.relation))
  const mother = (byRole.parent || []).find((n) => /母|妈|娘/.test(n.relation))
  ;(byRole.grand || []).forEach((n) => {
    const t = /外|姥/.test(n.relation) ? (mother || father) : (father || mother)
    link(t || hub, n, 'self')
  })
  ;(byRole.grandchild || []).forEach((n) => link((byRole.child || [])[0] || hub, n, 'self'))
  ;(byRole.uncle || []).forEach((n) => link(father || mother || hub, n, 'self'))
  ;[...(byRole.friend || []), ...(byRole.other || [])].forEach((n) => link(hub, n, 'dash'))

  return out
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
  // 斥力（节点间）——保证圆圈不重叠
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i], b = nodes[j]
      const dx = b.x - a.x, dy = b.y - a.y
      const d = Math.sqrt(dx * dx + dy * dy) || 1
      if (d < 96) {
        const f = (96 - d) / d * 0.5
        a.vx -= dx * f; a.vy -= dy * f
        b.vx += dx * f; b.vy += dy * f
      }
    }
  }
  // 亲缘连线当弹簧——被连线的人互相靠近，这是「大姨姐贴在老婆旁边」的来源
  for (const e of edges) {
    const dx = e.b.x - e.a.x, dy = e.b.y - e.a.y
    const d = Math.sqrt(dx * dx + dy * dy) || 1
    const len = e.kind === 'self' ? 175 : 158
    const f = (d - len) / d * 0.022
    e.a.vx += dx * f; e.a.vy += dy * f
    e.b.vx -= dx * f; e.b.vy -= dy * f
  }
  // 语义锚点（弱吸引，保证整体结构稳定：父母在上、配偶在右、子女在下）
  for (const n of nodes) {
    n.vx += (n.home.x - n.x) * 0.012
    n.vy += (n.home.y - n.y) * 0.012
    if (n !== dragNode) { n.x += n.vx; n.y += n.vy }
    n.vx *= 0.84; n.vy *= 0.84
    n.x = Math.max(34, Math.min(W - 34, n.x))
    n.y = Math.max(34, Math.min(H - 34, n.y))
  }
}

function draw() {
  const cv = cvEl.value
  if (!cv) return
  const ctx = cv.getContext('2d')
  ctx.clearRect(0, 0, W, H)

  // 先画连线（在节点下面）
  for (const e of edges) {
    ctx.beginPath()
    if (e.kind === 'dash') {
      ctx.setLineDash([6, 6])
      ctx.strokeStyle = 'rgba(154,160,166,.6)'
      ctx.lineWidth = 1.2
    } else if (e.kind === 'spouse') {
      ctx.setLineDash([])
      ctx.strokeStyle = 'rgba(127,168,163,.55)'
      ctx.lineWidth = 1.5
    } else {
      ctx.setLineDash([])
      ctx.strokeStyle = 'rgba(199,169,107,.55)'
      ctx.lineWidth = 1.6
    }
    ctx.moveTo(e.a.x, e.a.y)
    ctx.lineTo(e.b.x, e.b.y)
    ctx.stroke()
    ctx.setLineDash([])
  }

  // 节点
  for (const n of nodes) {
    const color = ROLE_COLOR[n.role] || ROLE_COLOR.other
    if (n.role === 'self') {                       // 轴心加一圈光晕
      ctx.beginPath()
      ctx.arc(n.x, n.y, n.r + 7, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(199,169,107,.16)'
      ctx.fill()
    }
    ctx.beginPath()
    ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2)
    ctx.fillStyle = n === selected.value ? 'rgba(199,169,107,.95)' : color
    ctx.fill()
    if (n === dragNode) {
      ctx.strokeStyle = 'rgba(255,255,255,.9)'
      ctx.lineWidth = 2
      ctx.stroke()
    }
    ctx.fillStyle = '#fff'
    ctx.font = '600 13px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(n.name.slice(0, 3), n.x, n.y + 4.5)

    // 关系名标注在圆圈下方（比原来「按关系分组画一个标签」更清楚，一人一标）
    ctx.fillStyle = color
    ctx.font = '600 11.5px sans-serif'
    ctx.fillText(n.relation, n.x, n.y + n.r + 15)
  }
}

function pick(e) {
  const rect = cvEl.value.getBoundingClientRect()
  const x = (e.clientX - rect.left) * (W / rect.width)
  const y = (e.clientY - rect.top) * (H / rect.height)
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
  dragNode.x = (e.clientX - rect.left) * (W / rect.width)
  dragNode.y = (e.clientY - rect.top) * (H / rect.height)
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
.mt-legend { margin-top: 10px; display: flex; gap: 18px; flex-wrap: wrap; font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
.mt-lg { display: inline-flex; align-items: center; gap: 6px; }
.mt-line { display: inline-block; width: 22px; height: 0; border-top-width: 2px; border-top-style: solid; }
.mt-line.self { border-top-color: rgba(199,169,107,.75); }
.mt-line.spouse { border-top-color: rgba(127,168,163,.75); }
.mt-line.dash { border-top-style: dashed; border-top-color: rgba(154,160,166,.8); }
.mt-hint { margin-top: 6px; font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
</style>
