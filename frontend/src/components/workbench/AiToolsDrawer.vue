<!--
  AiToolsDrawer.vue
  玄黄 AI 高级工具抽屉（v2.39）—— 给笔记/对话场景用的「AI 万能面板」。

  能力：
  - 改写（rewrite）：6 种风格
  - 解释（explain）：选中文字/粘贴图片
  - 语义搜索（semantic_search）：基于嵌入
  - 长期记忆（memory_distill）：从笔记抽取稳定事实
  - 自动任务（agent）：ReAct 循环执行多步工具调用
  - OCR（ocr）：图片→文字
  - 用量（usage）：当月 token 统计
-->
<template>
  <transition name="ai-fade">
    <div v-if="open" class="aid-mask" @click.self="$emit('close')" @keydown.esc="$emit('close')" tabindex="-1">
      <div class="aid-panel">
        <header class="aid-head">
          <div class="aid-title">
            <span class="aid-mark">✺</span>
            <span>AI 高级工具</span>
            <span class="aid-tag">v2.39</span>
          </div>
          <button class="aid-close" @click="$emit('close')" title="关闭（Esc）">✕ 关闭</button>
        </header>

        <nav class="aid-tabs">
          <button
            v-for="t in tabs"
            :key="t.key"
            class="aid-tab"
            :class="{ on: active === t.key }"
            @click="active = t.key"
          >
            <span class="aid-tab-ic">{{ t.icon }}</span>
            <span>{{ t.label }}</span>
          </button>
        </nav>

        <div class="aid-body">
          <!-- ===== 改写 ===== -->
          <section v-if="active === 'rewrite'" class="aid-section">
            <label class="aid-label">原文</label>
            <textarea
              v-model="rw.text"
              class="aid-textarea"
              rows="6"
              placeholder="把要改写的文字贴进来，或在编辑器选中文字后点「从笔记加载」"
            ></textarea>
            <div class="aid-row">
              <label class="aid-label">风格</label>
              <select v-model="rw.style" class="aid-select">
                <option value="casual">更口语</option>
                <option value="formal">更正式</option>
                <option value="concise">更短</option>
                <option value="emoji">加 emoji</option>
                <option value="polish">润色</option>
                <option value="critical">批判审视</option>
              </select>
              <button class="aid-btn" :disabled="rw.busy || !rw.text" @click="runRewrite">
                {{ rw.busy ? '改写中…' : '改写' }}
              </button>
            </div>
            <div v-if="rw.result" class="aid-result">
              <div class="aid-result-text">{{ rw.result }}</div>
              <div class="aid-result-meta" v-if="rw.diff_ratio">
                长度比 {{ (rw.diff_ratio * 100).toFixed(0) }}%
              </div>
              <div class="aid-result-actions">
                <button class="aid-btn ghost" @click="copyText(rw.result)">复制</button>
                <button class="aid-btn" @click="$emit('apply', { kind: 'rewrite', text: rw.result })">应用到笔记</button>
              </div>
            </div>
          </section>

          <!-- ===== 解释 ===== -->
          <section v-if="active === 'explain'" class="aid-section">
            <label class="aid-label">概念 / 选中文本 / 图片 URL</label>
            <textarea v-model="ex.text" class="aid-textarea" rows="4" placeholder="要解释的概念，或粘贴图片 URL"></textarea>
            <div class="aid-row">
              <button class="aid-btn" :disabled="ex.busy || !ex.text" @click="runExplain">
                {{ ex.busy ? '解释中…' : '解释' }}
              </button>
            </div>
            <div v-if="ex.result" class="aid-result">
              <p v-if="ex.definition" class="aid-def"><b>定义：</b>{{ ex.definition }}</p>
              <p v-if="ex.example" class="aid-def"><b>例子：</b>{{ ex.example }}</p>
              <p v-if="ex.related?.length" class="aid-def">
                <b>相关：</b>
                <span v-for="r in ex.related" :key="r" class="aid-chip">{{ r }}</span>
              </p>
              <p class="aid-result-text">{{ ex.result }}</p>
            </div>
          </section>

          <!-- ===== 语义搜索 ===== -->
          <section v-if="active === 'search'" class="aid-section">
            <label class="aid-label">自然语言查询</label>
            <input v-model="sr.q" class="aid-input" placeholder="比如：上次关于数据库索引优化的笔记" @keyup.enter="runSemantic" />
            <div class="aid-row">
              <button class="aid-btn" :disabled="sr.busy || !sr.q" @click="runSemantic">
                {{ sr.busy ? '召回中…' : '语义召回' }}
              </button>
              <span v-if="sr.results" class="aid-meta">{{ sr.results.length }} 条相关笔记</span>
            </div>
            <ul v-if="sr.results?.length" class="aid-list">
              <li v-for="r in sr.results" :key="r.id" @click="$emit('apply', { kind: 'goto_note', id: r.id })">
                <span class="aid-score">{{ (r.score * 100).toFixed(0) }}%</span>
                <span class="aid-list-title">{{ r.title }}</span>
                <span v-if="r.snippet" class="aid-list-snippet">{{ r.snippet }}</span>
              </li>
              <li v-if="!sr.results.length" class="aid-empty">未命中；先把笔记写得多一些再试。</li>
            </ul>
          </section>

          <!-- ===== 长期记忆 ===== -->
          <section v-if="active === 'memory'" class="aid-section">
            <p class="aid-meta">AI 自动从你最近笔记蒸馏出的稳定事实。点 ✓ 应用到对话，× 让 AI 忘记。</p>
            <div class="aid-row">
              <button class="aid-btn" :disabled="mem.distilling" @click="runDistill">
                {{ mem.distilling ? '蒸馏中…' : '从最近笔记蒸馏' }}
              </button>
              <button class="aid-btn ghost" :disabled="mem.loading" @click="loadMemory">刷新列表</button>
            </div>

            <!-- 手动添加：直接给 fact 或给 prompt 让 AI 整理 -->
            <details class="aid-add">
              <summary>手动添加 / 让 AI 整理口语化表述</summary>
              <div class="aid-add-body">
                <textarea
                  v-model="mem.addPrompt"
                  class="aid-textarea"
                  rows="3"
                  placeholder="两种填法：(1) 直接写要保留的事实  (2) 用自然语言描述「我是一名产品经理，偏好极简风格」，点下方按钮让 AI 整理成事实"
                ></textarea>
                <div class="aid-row">
                  <label class="aid-label">类别</label>
                  <select v-model="mem.addCategory" class="aid-select">
                    <option value="identity">身份 identity</option>
                    <option value="habit">习惯 habit</option>
                    <option value="preference">偏好 preference</option>
                    <option value="relationship">人际关系 relationship</option>
                    <option value="project">项目 project</option>
                    <option value="other">其它 other</option>
                  </select>
                  <button class="aid-btn" :disabled="mem.adding || !mem.addPrompt.trim()" @click="addMemory">
                    {{ mem.adding ? '添加中…' : '添加' }}
                  </button>
                </div>
                <p class="aid-meta">⚡ 填进 prompt 框时，点「添加」会先保存原文；点下方「AI 整理」会调用模型蒸馏出稳定事实。</p>
                <div class="aid-row">
                  <button class="aid-btn ghost" :disabled="mem.adding || !mem.addPrompt.trim()" @click="addMemoryAi">
                    {{ mem.adding ? 'AI 整理中…' : 'AI 整理成事实' }}
                  </button>
                </div>
              </div>
            </details>

            <ul v-if="mem.list.length" class="aid-mem">
              <li v-for="f in mem.list" :key="f.id">
                <span class="aid-cat">{{ f.category }}</span>
                <span class="aid-fact">{{ f.fact }}</span>
                <span class="aid-cf">{{ f.confidence }}%</span>
                <span v-if="f.source === 'manual'" class="aid-src">手动</span>
                <span v-else-if="f.source === 'ai_distill_from_prompt'" class="aid-src">AI整理</span>
                <span v-else-if="f.source === 'ai_distill'" class="aid-src">蒸馏</span>
                <button class="aid-mini danger" @click="forgetFact(f.id)" title="让 AI 忘记">×</button>
              </li>
            </ul>
            <div v-else class="aid-empty">暂无记忆。</div>
          </section>

          <!-- ===== 自动任务 Agent ===== -->
          <section v-if="active === 'agent'" class="aid-section">
            <label class="aid-label">目标</label>
            <textarea v-model="ag.goal" class="aid-textarea" rows="3"
              placeholder="例如：帮我把上周关于玄黄项目的笔记都整理成一份摘要并新建一条笔记"></textarea>
            <div class="aid-row">
              <button class="aid-btn" :disabled="ag.busy || !ag.goal" @click="runAgent">
                {{ ag.busy ? '执行中…' : '启动 Agent' }}
              </button>
              <span v-if="ag.result" class="aid-meta">用了 {{ ag.used_tokens }} tokens，{{ ag.step_count }} 步</span>
            </div>
            <div v-if="ag.job_id" class="aid-result">
              <div class="aid-result-text">{{ ag.result || '(已完成无文本输出)' }}</div>
              <details v-if="ag.steps?.length" class="aid-steps">
                <summary>查看执行步骤</summary>
                <ol>
                  <li v-for="s in ag.steps" :key="s.step">
                    <b>{{ s.action }}</b>（{{ s.thought }}）
                    <pre>{{ JSON.stringify(s.observation, null, 2) }}</pre>
                  </li>
                </ol>
              </details>
            </div>
          </section>

          <!-- ===== OCR ===== -->
          <section v-if="active === 'ocr'" class="aid-section">
            <label class="aid-label">图片 URL</label>
            <input v-model="oc.url" class="aid-input" placeholder="站内资产或外链均可" />
            <div class="aid-row">
              <button class="aid-btn" :disabled="oc.busy || !oc.url" @click="runOcr">
                {{ oc.busy ? '识别中…' : '识别' }}
              </button>
              <span v-if="oc.engine" class="aid-meta">引擎：{{ oc.engine }}</span>
            </div>
            <textarea v-if="oc.text" v-model="oc.text" class="aid-textarea" rows="6"></textarea>
          </section>

          <!-- ===== 用量 ===== -->
          <section v-if="active === 'usage'" class="aid-section">
            <p class="aid-meta">当月 token 用量（默认上限 1,000,000,000 ≈ 10 亿，可在 .env 用 AI_MONTHLY_TOKEN_LIMIT 调整）</p>
            <div v-if="us.total_tokens != null" class="aid-usage">
              <div class="aid-usage-bar">
                <div class="aid-usage-fill" :style="{ width: Math.min(100, (us.total_tokens / Math.max(us.limit, 1)) * 100) + '%' }"></div>
              </div>
              <div class="aid-usage-meta">
                <span>{{ us.total_tokens.toLocaleString() }} / {{ us.limit.toLocaleString() }} tokens</span>
                <span>{{ Math.round((us.total_tokens / Math.max(us.limit, 1)) * 100) }}%</span>
              </div>
              <table v-if="Object.keys(us.by_ability || {}).length" class="aid-usage-table">
                <thead><tr><th>能力</th><th>tokens</th></tr></thead>
                <tbody>
                  <tr v-for="(v, k) in us.by_ability" :key="k"><td>{{ k }}</td><td>{{ v.toLocaleString() }}</td></tr>
                </tbody>
              </table>
            </div>
            <button class="aid-btn ghost" @click="loadUsage">刷新</button>
          </section>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, watch } from 'vue'
import { workbenchApi } from '@/api/workbench'
import { ElMessage } from 'element-plus'

const props = defineProps({
  open: { type: Boolean, default: false },
  defaultContent: { type: String, default: '' },
  defaultImageUrl: { type: String, default: '' },
})
const emit = defineEmits(['close', 'apply'])

const tabs = [
  { key: 'rewrite',   label: '改写',   icon: '✎' },
  { key: 'explain',   label: '解释',   icon: '?' },
  { key: 'search',    label: '语义搜索', icon: '⌕' },
  { key: 'memory',    label: '长期记忆', icon: '☷' },
  { key: 'agent',     label: '自动任务', icon: '✺' },
  { key: 'ocr',       label: 'OCR',     icon: '◉' },
  { key: 'usage',     label: '用量',    icon: '⌗' },
]
const active = ref('rewrite')

// ==== 改写 ====
const rw = ref({ text: '', style: 'polish', busy: false, result: '', diff_ratio: 1.0 })
async function runRewrite() {
  rw.value.busy = true
  try {
    const r = await workbenchApi.aiAdv.invoke({ ability: 'rewrite', content: rw.value.text, style: rw.value.style })
    rw.value.result = (r?.data?.text) || r?.data?.data?.text || ''
    rw.value.diff_ratio = r?.data?.data?.diff_ratio || 1.0
  } catch (e) { ElMessage.error(e?.message || '改写失败') }
  finally { rw.value.busy = false }
}

// ==== 解释 ====
const ex = ref({ text: '', busy: false, result: '', definition: '', example: '', related: [] })
async function runExplain() {
  ex.value.busy = true
  try {
    const body = { ability: 'explain', content: ex.value.text }
    if (props.defaultImageUrl) body.image_url = props.defaultImageUrl
    const r = await workbenchApi.aiAdv.invoke(body)
    ex.value.result = r?.data?.text || ''
    const d = r?.data?.data || {}
    ex.value.definition = d.definition || ''
    ex.value.example = d.example || ''
    ex.value.related = d.related || []
  } catch (e) { ElMessage.error(e?.message || '解释失败') }
  finally { ex.value.busy = false }
}

// ==== 语义搜索 ====
const sr = ref({ q: '', busy: false, results: null })
async function runSemantic() {
  sr.value.busy = true
  try {
    const r = await workbenchApi.aiAdv.semanticSearch(sr.value.q)
    sr.value.results = r?.data?.results || []
  } catch (e) { ElMessage.error(e?.message || '语义搜索失败') }
  finally { sr.value.busy = false }
}

// ==== 长期记忆 ====
const mem = ref({
  list: [], loading: false, distilling: false,
  addPrompt: '', addCategory: 'other', adding: false,
})
async function loadMemory() {
  mem.value.loading = true
  try {
    const r = await workbenchApi.aiAdv.memoryList()
    mem.value.list = r?.data?.list || []
  } catch (e) { ElMessage.error(e?.message || '读取失败') }
  finally { mem.value.loading = false }
}
async function runDistill() {
  mem.value.distilling = true
  try {
    await workbenchApi.aiAdv.invoke({ ability: 'memory_distill', content: '请蒸馏本人最近笔记中的稳定事实。' })
    await loadMemory()
    ElMessage.success('蒸馏完成')
  } catch (e) { ElMessage.error(e?.message || '蒸馏失败') }
  finally { mem.value.distilling = false }
}
async function addMemory() {
  const text = mem.value.addPrompt.trim()
  if (!text) return
  mem.value.adding = true
  try {
    // 直接保存原文（不走 AI）
    await workbenchApi.aiAdv.memoryAdd({
      fact: text,
      category: mem.value.addCategory,
      confidence: 90,
    })
    mem.value.addPrompt = ''
    await loadMemory()
    ElMessage.success('已添加')
  } catch (e) { ElMessage.error(e?.message || '添加失败') }
  finally { mem.value.adding = false }
}
async function addMemoryAi() {
  const text = mem.value.addPrompt.trim()
  if (!text) return
  mem.value.adding = true
  try {
    await workbenchApi.aiAdv.memoryAdd({
      prompt: text,
      category: mem.value.addCategory,
      confidence: 80,
    })
    mem.value.addPrompt = ''
    await loadMemory()
    ElMessage.success('AI 已整理完成')
  } catch (e) { ElMessage.error(e?.message || 'AI 整理失败') }
  finally { mem.value.adding = false }
}
async function forgetFact(id) {
  try {
    await workbenchApi.aiAdv.memoryForget({ fact_id: id })
    mem.value.list = mem.value.list.filter(x => x.id !== id)
  } catch (e) { ElMessage.error(e?.message || '忘记失败') }
}

// ==== Agent ====
const ag = ref({ goal: '', busy: false, job_id: null, result: '', steps: [], used_tokens: 0, step_count: 0 })
async function runAgent() {
  ag.value.busy = true
  ag.value.job_id = null; ag.value.result = ''; ag.value.steps = []
  try {
    const start = await workbenchApi.aiAdv.agentStart({ goal: ag.value.goal, max_steps: 6 })
    const jobId = start?.data?.job_id
    if (!jobId) throw new Error('启动失败')
    const run = await workbenchApi.aiAdv.agentRun({ job_id: jobId })
    ag.value.job_id = jobId
    ag.value.result = run?.data?.result || ''
    ag.value.used_tokens = run?.data?.used_tokens || 0
    ag.value.step_count = run?.data?.step_count || 0
    // 拉取步骤详情
    try {
      const detail = await workbenchApi.aiAdv.agentGet(jobId)
      ag.value.steps = detail?.data?.steps || []
    } catch {}
  } catch (e) { ElMessage.error(e?.message || '执行失败') }
  finally { ag.value.busy = false }
}

// ==== OCR ====
const oc = ref({ url: '', busy: false, text: '', engine: '' })
async function runOcr() {
  oc.value.busy = true
  try {
    const r = await workbenchApi.aiAdv.ocr({ image_url: oc.value.url })
    oc.value.text = r?.data?.text || ''
    oc.value.engine = r?.data?.engine || ''
  } catch (e) { ElMessage.error(e?.message || 'OCR 失败') }
  finally { oc.value.busy = false }
}

// ==== 用量 ====
const us = ref({ total_tokens: 0, limit: 0, by_ability: {} })
async function loadUsage() {
  try {
    const r = await workbenchApi.aiAdv.usage()
    us.value = r?.data || us.value
  } catch (e) { ElMessage.error(e?.message || '读取失败') }
}

// ==== 默认内容同步 ====
watch(() => props.open, (v) => {
  if (v) {
    if (props.defaultContent && !rw.value.text) rw.value.text = props.defaultContent
    if (props.defaultContent && !ex.value.text) ex.value.text = props.defaultContent
    if (props.defaultImageUrl && !oc.value.url) oc.value.url = props.defaultImageUrl
    loadMemory()
    loadUsage()
  }
})

function copyText(s) {
  try { navigator.clipboard.writeText(s); ElMessage.success('已复制') } catch { ElMessage.error('复制失败') }
}
</script>

<style scoped>
.ai-fade-enter-active, .ai-fade-leave-active { transition: opacity .2s ease }
.ai-fade-enter-from, .ai-fade-leave-to { opacity: 0 }
.aid-mask { position: fixed; inset: 0; background: rgba(0,0,0,.45); backdrop-filter: blur(2px); z-index: 2000; display: flex; justify-content: flex-end }
.aid-panel {
  width: 460px; max-width: 100vw; height: 100%; background: var(--dp-surface, #141426);
  border-left: 1px solid var(--dp-line-strong); display: flex; flex-direction: column;
  box-shadow: -8px 0 32px rgba(0,0,0,.4); font-family: inherit;
}
.aid-head {
  padding: 14px 18px; display: flex; align-items: center; justify-content: space-between;
  border-bottom: 1px solid var(--dp-line);
}
.aid-title { display: inline-flex; align-items: center; gap: 8px; font-weight: 700; font-size: 14px }
.aid-mark { color: var(--dp-accent, #67e8f9); font-size: 16px }
.aid-tag { font-size: 10px; padding: 2px 6px; border-radius: 4px; background: var(--dp-accent-faint, rgba(167,139,250,.16)); color: var(--dp-accent); letter-spacing: .04em }
.aid-close { background: var(--dp-surface2); border: 1px solid var(--dp-line); color: var(--dp-text); cursor: pointer; font-size: 12px; font-weight: 600; padding: 6px 12px; border-radius: 6px; letter-spacing: .04em; position: relative; z-index: 2 }
.aid-close:hover { background: var(--dp-danger, #ff6b6b); color: #fff; border-color: var(--dp-danger, #ff6b6b) }
.aid-tabs { display: flex; gap: 4px; padding: 8px 12px; border-bottom: 1px solid var(--dp-line); overflow-x: auto }
.aid-tab {
  background: transparent; border: 0; cursor: pointer; padding: 6px 10px; border-radius: 8px;
  color: var(--dp-text2); font-size: 12.5px; display: inline-flex; gap: 4px; align-items: center;
  white-space: nowrap;
}
.aid-tab.on { background: var(--dp-accent-faint); color: var(--dp-accent); font-weight: 600 }
.aid-tab-ic { font-size: 14px }
.aid-body { flex: 1; overflow: auto; padding: 14px 18px }
.aid-section { display: flex; flex-direction: column; gap: 8px }
.aid-label { font-size: 11px; color: var(--dp-text3); letter-spacing: .12em; text-transform: uppercase }
.aid-textarea, .aid-input, .aid-select {
  background: var(--dp-surface2, #1c1c30); border: 1px solid var(--dp-line);
  border-radius: 8px; padding: 10px 12px; font-size: 13px; color: var(--dp-text);
  font-family: inherit; outline: none; resize: vertical;
}
.aid-textarea:focus, .aid-input:focus, .aid-select:focus { border-color: var(--dp-accent) }
.aid-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap }
.aid-btn {
  background: var(--dp-accent, #67e8f9); color: #001a1f; border: 0; padding: 7px 14px;
  border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer;
}
.aid-btn.ghost { background: transparent; color: var(--dp-text2); border: 1px solid var(--dp-line-strong) }
.aid-btn.ghost:hover { border-color: var(--dp-accent); color: var(--dp-accent) }
.aid-btn:disabled { opacity: .5; cursor: not-allowed }
.aid-mini { background: transparent; border: 1px solid var(--dp-line); color: var(--dp-text3); border-radius: 4px; padding: 1px 7px; cursor: pointer; font-size: 13px }
.aid-mini.danger { color: var(--dp-danger, #ff6b6b) }
.aid-result { background: var(--dp-surface2); border: 1px solid var(--dp-line); border-radius: 8px; padding: 12px; font-size: 13px; line-height: 1.7 }
.aid-result-text { white-space: pre-wrap; color: var(--dp-text) }
.aid-result-meta { color: var(--dp-text3); font-size: 11.5px; margin-top: 6px }
.aid-result-actions { display: flex; gap: 8px; margin-top: 10px }
.aid-def { margin: 0 0 6px; color: var(--dp-text2) }
.aid-chip { display: inline-block; padding: 1px 8px; border-radius: 12px; background: var(--dp-accent-faint); color: var(--dp-accent); font-size: 11.5px; margin: 0 4px 2px 0 }
.aid-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px }
.aid-list li { padding: 8px 10px; background: var(--dp-surface2); border-radius: 6px; cursor: pointer; border: 1px solid var(--dp-line); font-size: 12.5px }
.aid-list li:hover { border-color: var(--dp-accent) }
.aid-score { display: inline-block; min-width: 36px; text-align: right; color: var(--dp-accent); margin-right: 6px; font-variant-numeric: tabular-nums }
.aid-list-title { color: var(--dp-text); margin-right: 6px }
.aid-list-snippet { color: var(--dp-text3); display: block; margin-top: 3px; font-size: 11.5px }
.aid-mem { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px }
.aid-mem li { display: flex; align-items: center; gap: 8px; background: var(--dp-surface2); padding: 8px 10px; border-radius: 6px; border: 1px solid var(--dp-line); font-size: 12.5px }
.aid-cat { padding: 1px 8px; background: var(--dp-accent-faint); color: var(--dp-accent); border-radius: 10px; font-size: 10.5px; letter-spacing: .08em }
.aid-fact { flex: 1; color: var(--dp-text) }
.aid-cf { color: var(--dp-text3); font-size: 11.5px; font-variant-numeric: tabular-nums }
.aid-src { font-size: 10.5px; color: var(--dp-text3); padding: 1px 6px; border-radius: 8px; border: 1px solid var(--dp-line) }

.aid-add { background: var(--dp-surface2); border: 1px solid var(--dp-line); border-radius: 8px; padding: 8px 10px; margin: 4px 0 }
.aid-add summary { cursor: pointer; font-size: 12.5px; color: var(--dp-text2); user-select: none }
.aid-add summary:hover { color: var(--dp-accent) }
.aid-add-body { display: flex; flex-direction: column; gap: 8px; margin-top: 10px }
.aid-meta { color: var(--dp-text3); font-size: 11.5px }
.aid-empty { color: var(--dp-text3); font-size: 12px; padding: 8px 0 }
.aid-steps summary { cursor: pointer; color: var(--dp-text2); padding: 6px 0; font-size: 12.5px }
.aid-steps ol { padding-left: 18px; color: var(--dp-text2); font-size: 12px; line-height: 1.6 }
.aid-steps pre { background: var(--dp-bg, #000); color: var(--dp-text); padding: 8px; border-radius: 4px; font-size: 11.5px; overflow: auto }
.aid-usage-bar { height: 8px; background: var(--dp-line); border-radius: 4px; overflow: hidden }
.aid-usage-fill { height: 100%; background: linear-gradient(90deg, var(--dp-accent), var(--dp-warning)) }
.aid-usage-meta { display: flex; justify-content: space-between; color: var(--dp-text2); font-size: 12.5px; margin: 6px 0 12px; font-variant-numeric: tabular-nums }
.aid-usage-table { width: 100%; font-size: 12px; border-collapse: collapse }
.aid-usage-table th, .aid-usage-table td { text-align: left; padding: 4px 8px; border-bottom: 1px solid var(--dp-line); color: var(--dp-text2) }
.aid-usage-table th { color: var(--dp-text3); font-weight: 500 }
</style>
