<template>
  <div class="mempty" :class="$attrs.class">
    <svg class="mempty-art" viewBox="0 0 200 160" aria-hidden="true" fill="none">
      <!-- 云雾低透背景 -->
      <ellipse cx="100" cy="142" rx="72" ry="12" opacity=".25" fill="url(#meFog)"/>
      <!-- 墨玉玉简（凹陷层次：外框+内阴影感） -->
      <rect x="58" y="30" width="84" height="112" rx="14" fill="url(#meJade)"/>
      <rect x="66" y="38" width="68" height="96" rx="9" fill="none" stroke="#c9a35f" stroke-opacity=".6"/>
      <path d="M74 54 h52 M74 72 h52 M74 90 h34" stroke="#c9a35f" stroke-opacity=".35" stroke-width="3" stroke-linecap="round"/>
      <!-- 琥珀点 -->
      <circle cx="100" cy="66" r="4" fill="#caa466" opacity=".85"/>
      <!-- 光晕 -->
      <circle cx="116" cy="52" r="26" fill="#caa466" opacity=".10"/>
      <defs>
        <linearGradient id="meJade" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#1b312b"/><stop offset="1" stop-color="#0d1a15"/>
        </linearGradient>
        <radialGradient id="meFog" cx=".5" cy=".5" r=".6">
          <stop offset="0" stop-color="#caa466"/><stop offset="1" stop-color="#caa466" stop-opacity="0"/>
        </radialGradient>
      </defs>
    </svg>
    <p class="mempty-title">{{ title }}</p>
    <p v-if="desc" class="mempty-desc">{{ desc }}</p>
    <slot />
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  desc: { type: String, default: '' },
})
</script>

<style scoped>
.mempty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 48px 28px; text-align: center; gap: 6px;
}
.mempty-art { width: 150px; height: 120px; margin-bottom: 8px; }
.mempty-title { font-size: 16px; font-weight: 600; color: var(--lj-text, #dfebe5); letter-spacing: .05em; }
.mempty-desc { font-size: 12.5px; color: var(--lj-text-3, rgba(200,215,220,.5)); line-height: 1.5; }
</style>