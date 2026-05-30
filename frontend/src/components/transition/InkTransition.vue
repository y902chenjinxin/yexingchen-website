<template>
  <Teleport to="body">
    <div class="ink-transition" v-if="isActive" @click="skip">
      <div class="ink-corner ink-tl"></div>
      <div class="ink-corner ink-tr"></div>
      <div class="ink-corner ink-bl"></div>
      <div class="ink-corner ink-br"></div>
      <div class="ink-line"></div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  active: {
    type: Boolean,
    default: false
  },
  duration: {
    type: Number,
    default: 800
  }
})

const emit = defineEmits(['complete'])
const isActive = ref(false)

watch(() => props.active, (newVal) => {
  if (newVal) {
    triggerTransition()
  }
})

const triggerTransition = () => {
  isActive.value = true

  setTimeout(() => {
    isActive.value = false
    emit('complete')
  }, props.duration)
}

const skip = () => {
  isActive.value = false
  emit('complete')
}
</script>

<style scoped>
.ink-transition {
  position: fixed;
  inset: 0;
  z-index: 9999;
  pointer-events: all;
  cursor: pointer;
}

.ink-corner {
  position: absolute;
  width: var(--ink-corner-size, 100px);
  height: var(--ink-corner-size, 100px);
  background: var(--ink-color, #0A0C12);
  transition: all var(--ink-duration, 0.8s) var(--ink-transition-easing, cubic-bezier(0.65, 0, 0.35, 1));
}

/* 四角墨色从无到有凝聚 */
.ink-tl {
  top: 0;
  left: 0;
  transform-origin: top left;
  clip-path: inset(0 100% 100% 0);
}

.ink-tr {
  top: 0;
  right: 0;
  transform-origin: top right;
  clip-path: inset(0 0 100% 100%);
}

.ink-bl {
  bottom: 0;
  left: 0;
  transform-origin: bottom left;
  clip-path: inset(100% 100% 0 0);
}

.ink-br {
  bottom: 0;
  right: 0;
  transform-origin: bottom right;
  clip-path: inset(100% 0 0 100%);
}

/* 触发时四角展开 */
.ink-transition.active .ink-tl {
  clip-path: inset(0 0 0 0);
}

.ink-transition.active .ink-tr {
  clip-path: inset(0 0 0 0);
}

.ink-transition.active .ink-bl {
  clip-path: inset(0 0 0 0);
}

.ink-transition.active .ink-br {
  clip-path: inset(0 0 0 0);
}

/* 中间墨线 */
.ink-line {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--ink-color, #0A0C12);
  transform: scaleX(0);
  transition: transform var(--ink-duration, 0.8s) var(--ink-transition-easing, cubic-bezier(0.65, 0, 0.35, 1));
}

/* 墨线展开 */
.ink-transition.active .ink-line {
  transform: scaleX(1);
}
</style>