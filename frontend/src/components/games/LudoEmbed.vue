<template>
  <div class="ld-wrap">
    <iframe
      src="/tools/ludo/game.html"
      class="ld-frame"
      title="飞行棋"
      allow="autoplay"
    ></iframe>
    <p class="ld-hint">中国飞行棋（开源实现，MIT License · netmanfisher/chinese-ludo）· 支持人机与同屏多人 · 在框内直接玩</p>
  </div>
</template>

<script setup>
/** 飞行棋：第三方开源实现（MIT），以静态站方式随前端构建发布在 /tools/ludo/，这里 iframe 嵌入。
 * 选它而不是自写：中国飞行棋规则细节多（同色跳格/飞行捷径/安全格），先用成熟实现验证需求。
 */
</script>

<style scoped>
.ld-wrap { display: flex; flex-direction: column; align-items: center; gap: 10px; width: 100%; }
.ld-frame {
  width: min(560px, 100%); height: min(640px, 78vh); border: 1px solid var(--dp-line, rgba(0,0,0,.12));
  border-radius: 12px; background: #fff;
}
.ld-hint { font-size: 11.5px; color: var(--dp-text3, #8a8f98); }
</style>
