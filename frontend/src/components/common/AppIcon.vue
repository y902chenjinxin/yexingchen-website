<template>
  <svg
    v-if="body"
    class="app-icon"
    :style="boxStyle"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="weight"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    v-html="body"
  ></svg>
  <span v-else class="app-icon is-raw" aria-hidden="true">{{ icon }}</span>
</template>

<script setup>
import { computed } from 'vue'
import { appIconBody } from '@/utils/icons'

const props = defineProps({
  // 存库 / 常量里的 emoji：命中图标表就画线性图标，没命中就原样渲染这个字符
  icon: { type: String, default: '' },
  // 显示边长（px）
  size: { type: Number, default: 18 },
  // 描边粗细（默认 1.6；13px 以下的小图标可传 1.8 更清晰）
  weight: { type: Number, default: 1.6 },
})

const body = computed(() => appIconBody(props.icon))
const boxStyle = computed(() => ({ width: `${props.size}px`, height: `${props.size}px` }))
</script>

<style scoped>
/* 图标本身零颜色：stroke 走 currentColor，完全继承所在容器的文字色 */
.app-icon { display: inline-block; vertical-align: -0.125em; flex: none; }
.app-icon.is-raw { width: auto; height: auto; font-size: inherit; line-height: 1; }
</style>
