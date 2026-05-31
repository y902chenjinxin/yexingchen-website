<template>
  <div class="grain-overlay"></div>
</template>

<script setup>
// Pure CSS rice paper grain overlay
</script>

<style scoped>
.grain-overlay {
  position: fixed;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  pointer-events: none;
  z-index: 9998;
  opacity: 0.025;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 300 300' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='paper'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.7' numOctaves='4' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23paper)'/%3E%3C/svg%3E");
  animation: grain-shift 0.5s steps(1) infinite;
  mix-blend-mode: multiply;
}

@keyframes grain-shift {
  0% { transform: translate(0, 0); }
  25% { transform: translate(-1.5%, -1.5%); }
  50% { transform: translate(1.5%, 0); }
  75% { transform: translate(0, 1.5%); }
  100% { transform: translate(0, 0); }
}
</style>