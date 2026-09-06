<template>
  <span
    v-if="voice.supported.value"
    class="vib"
    :class="{ listening: isListening }"
    :title="isListening ? '点击结束录音' : '语音输入'"
    @click.stop="onToggle"
  >
    <span v-if="isListening" class="vib-wave" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
    <svg v-else viewBox="0 0 24 24" class="vib-mic" aria-hidden="true">
      <path fill="currentColor" d="M12 14a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V20H8v2h8v-2h-3v-2.08A7 7 0 0 0 19 11z"/>
    </svg>
    <Transition name="vib-tip"><span v-if="isListening" class="vib-tip">正在聆听…</span></Transition>
  </span>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useVoiceInput } from '@/composables/useVoiceInput'

const props = defineProps<{ lang?: string }>()
const emit = defineEmits<{ (e: 'result', text: string): void }>()

const voice = useVoiceInput({ lang: props.lang })
const isListening = ref(false)

function onToggle() {
  if (voice.listening.value) {
    voice.stop()
    isListening.value = false
  } else {
    voice.start((text) => {
      isListening.value = false
      if (text) emit('result', text)
    })
    isListening.value = true
  }
}
</script>

<style scoped>
.vib {
  display: inline-flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; border-radius: 50%; cursor: pointer;
  color: var(--lj-text-2, #9aa8ad); transition: all .25s; flex: none;
}
.vib:hover { color: var(--lj-dai, #7fa8a3); background: rgba(127,168,163,.10); }
.vib.listening { color: #e06464; }
.vib-mic { width: 16px; height: 16px; opacity: .9; }
.vib-wave { display: inline-flex; align-items: center; gap: 2px; height: 16px; }
.vib-wave i { width: 2.5px; height: 6px; border-radius: 2px; background: currentColor; animation: vib-beat 1s ease-in-out infinite; }
.vib-wave i:nth-child(2) { animation-delay: .15s; }
.vib-wave i:nth-child(3) { animation-delay: .3s; }
.vib-wave i:nth-child(4) { animation-delay: .45s; }
@keyframes vib-beat { 0%,100% { transform: scaleY(.45); } 50% { transform: scaleY(1.4); } }
.vib-tip { position: absolute; top: calc(100% + 6px); right: 50%; transform: translateX(50%);
  font-size: 11px; color: var(--lj-text-2, #9aa8ad); white-space: nowrap;
  background: var(--lj-glass, rgba(127,168,163,.9)); padding: 2px 8px; border-radius: 6px; z-index: 5; }
.vib { position: relative; }
.vib-tip-enter-active, .vib-tip-leave-active { transition: opacity .18s; }
.vib-tip-enter-from, .vib-tip-leave-to { opacity: 0; }
</style>