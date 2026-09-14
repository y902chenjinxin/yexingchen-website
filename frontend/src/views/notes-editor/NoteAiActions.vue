<template>
  <div class="ne-ai">
    <h4>AI 操作（需用户确认）</h4>
    <el-button size="small" :disabled="disabled" @click="$emit('preview', 'summarize')">生成摘要</el-button>
    <el-button size="small" :disabled="disabled" @click="$emit('preview', 'organize')">整理笔记</el-button>
    <el-button size="small" :disabled="disabled" @click="$emit('preview', 'suggest_tags')">建议标签</el-button>
    <el-button size="small" :disabled="disabled" @click="$emit('preview', 'suggest_task')">生成任务草稿</el-button>
    <el-button size="small" :disabled="disabled" @click="$emit('link-open')">关联到对话</el-button>
  </div>

  <el-dialog
    :model-value="aiDialog"
    title="AI 调用确认"
    width="600px"
    :close-on-click-modal="false"
    @update:model-value="(v) => !v && $emit('cancel')"
  >
    <p>将发送以下内容到 AI：</p>
    <pre class="ai-scope">{{ aiPreview }}</pre>
    <p v-if="aiSending" class="ai-status">正在调用 AI…</p>
    <div v-if="aiHasResult" class="ai-result-block">
      <h4>AI 返回结果（应用前需你确认）</h4>
      <pre class="ai-result">{{ aiResult }}</pre>
    </div>
    <template #footer>
      <el-button @click="$emit('cancel')" :disabled="aiSending">取消</el-button>
      <el-button
        v-if="!aiHasResult"
        type="primary"
        :disabled="aiSending"
        @click="$emit('confirm')"
      >确认发送</el-button>
      <el-button v-else type="primary" @click="$emit('apply')">已确认，写入</el-button>
    </template>
  </el-dialog>

  <el-dialog
    :model-value="linkDialog"
    title="选择 AI 对话"
    width="480px"
    @update:model-value="(v) => !v && $emit('link-close')"
  >
    <el-select
      :model-value="linkConvId"
      placeholder="选择对话"
      filterable
      style="width:100%"
      @update:model-value="(v) => $emit('link-update', v)"
    >
      <el-option
        v-for="c in conversations"
        :key="c.id"
        :label="c.title || '新对话'"
        :value="c.id"
      />
    </el-select>
    <template #footer>
      <el-button @click="$emit('link-close')">取消</el-button>
      <el-button type="primary" :disabled="!linkConvId" @click="$emit('link-confirm')">关联</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
/**
 * AI 操作区：4 个能力按钮（摘要 / 整理 / 标签 / 任务）+ 关联对话按钮，
 * 以及两个 el-dialog（AI 调用确认、关联对话）。
 *
 * 仅负责 UI 与 emit，所有 API 调用与消息流由 NoteEditorView 容器负责。
 */
defineProps({
  disabled: { type: Boolean, required: true },
  aiDialog: { type: Boolean, required: true },
  aiAbility: { type: String, required: true },
  aiPreview: { type: String, required: true },
  aiSending: { type: Boolean, required: true },
  aiResult: { type: String, required: true },
  aiHasResult: { type: Boolean, required: true },
  linkDialog: { type: Boolean, required: true },
  linkConvId: { type: [Number, null], required: true },
  conversations: { type: Array, required: true },
})

defineEmits([
  'preview',       // (ability)
  'confirm',
  'apply',
  'cancel',
  'link-open',
  'link-update',   // (id)
  'link-confirm',
  'link-close',
])
</script>

<style scoped>
.ne-ai { margin-top: 16px; padding: 12px; background: var(--xiu-card); border: 1px solid var(--xiu-line); border-radius: 10px; backdrop-filter: blur(10px); }
.ne-ai h4 { margin: 0 0 8px; font-size: 14px; color: var(--xiu-gold); letter-spacing: .08em; }
.ne-ai .el-button { margin-right: 6px; margin-bottom: 6px; }
.ai-scope { background: rgba(0,0,0,.2); border: 1px solid var(--xiu-line); padding: 8px; border-radius: 8px; font-size: 12px; max-height: 160px; overflow: auto; white-space: pre-wrap; word-break: break-word; color: var(--xiu-text-2); }
.ai-status { color: var(--xiu-primary-bright); font-size: 13px; margin-top: 8px; }
.ai-result-block { margin-top: 12px; }
.ai-result { background: rgba(61, 184, 176, .08); border: 1px solid rgba(61, 184, 176, .15); padding: 8px; border-radius: 8px; font-size: 12px; max-height: 200px; overflow: auto; white-space: pre-wrap; word-break: break-word; color: var(--xiu-text); }
</style>
