<template>
  <!-- 统一空状态（APP_design.md #24 · v2.46.33）：
       插图 + 解释 + 下一步行动（slot CTA），消灭裸「暂无数据」。
       手账风简笔插图跟随主题令牌（墨描边/鎏金点缀），宣纸/墨夜自动适配。 -->
  <div class="xz-empty">
    <svg class="xz-empty-art" viewBox="0 0 96 72" width="84" height="63" aria-hidden="true">
      <!-- 斜放便签 -->
      <g transform="rotate(-4 48 36)">
        <rect x="22" y="12" width="52" height="46" rx="6" fill="var(--xz-card, #fffdf8)" stroke="var(--xz-ink, #2b2b26)" stroke-width="2" />
        <path d="M62 12 l12 0 l0 12 z" fill="var(--xz-card-2, #f3ede0)" stroke="var(--xz-ink, #2b2b26)" stroke-width="2" stroke-linejoin="round" />
        <line x1="32" y1="30" x2="58" y2="30" stroke="var(--xz-ink, #2b2b26)" stroke-width="2" stroke-linecap="round" opacity=".45" />
        <line x1="32" y1="40" x2="50" y2="40" stroke="var(--xz-ink, #2b2b26)" stroke-width="2" stroke-linecap="round" opacity=".3" />
        <circle cx="33" cy="20" r="2.5" fill="var(--xz-gold, #c9a45c)" />
      </g>
      <!-- 点缀小星 -->
      <path d="M14 18 l2.2 4.4 4.8 .7 -3.5 3.4 .8 4.8 -4.3 -2.3 -4.3 2.3 .8 -4.8 -3.5 -3.4 4.8 -.7 z" fill="var(--xz-gold, #c9a45c)" opacity=".8" transform="scale(.62) translate(6 10)" />
      <circle cx="84" cy="58" r="2.5" fill="var(--xz-ochre, #b0684a)" opacity=".7" />
    </svg>
    <p class="xz-empty-t">{{ title }}</p>
    <p v-if="sub" class="xz-empty-s">{{ sub }}</p>
    <div v-if="$slots.default" class="xz-empty-cta"><slot /></div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  sub: { type: String, default: '' },
})
</script>

<style scoped>
.xz-empty {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding: 26px 16px; text-align: center;
}
.xz-empty-t { margin: 6px 0 0; font-size: 14.5px; font-weight: 600; color: var(--m-text); }
.xz-empty-s { margin: 0; font-size: 12.5px; line-height: 1.5; color: var(--m-text-2); }
.xz-empty-cta { margin-top: 10px; }
</style>
