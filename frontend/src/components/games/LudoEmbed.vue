<template>
  <div class="ld-wrap">
    <iframe
      src="/tools/ludo/game.html"
      class="ld-frame"
      title="飞行棋"
      allow="autoplay"
    ></iframe>
    <p class="ld-hint">
      中国飞行棋（开源实现，MIT License · netmanfisher/chinese-ludo）· 支持人机与同屏多人 · 在框内直接玩
      <br><span class="ld-note">提示：这是第三方页面，进度保存在它自己内部；退出全屏/返回列表不会重开，「刷新页面」才会。</span>
    </p>
  </div>
</template>

<script setup>
/** 飞行棋：第三方开源实现（MIT），以静态站方式随前端构建发布在 /tools/ludo/，这里 iframe 嵌入。
 * 选它而不是自写：中国飞行棋规则细节多（同色跳格/飞行捷径/安全格），先用成熟实现验证需求。
 *
 * v2.40.29：作为「需要大屏」的游戏，页面会默认全屏展示；iframe 只按视口高度铺开，
 * 组件实例不重建 —— 所以放大/退出/返回列表都不会把棋局重置（第三方内部状态无法序列化，
 * 因此不接入本项目的 localStorage 存档）。
 */
defineProps({
  initialMode: { type: String, default: '' },
  resume: { type: Boolean, default: false },
  bare: { type: Boolean, default: false },
})
</script>

<style scoped>
.ld-wrap { display: flex; flex-direction: column; align-items: center; gap: 10px; width: 100%; }
.ld-frame {
  width: 100%; height: min(76vh, 880px); border: 1px solid var(--dp-line, rgba(0,0,0,.12));
  border-radius: 14px; background: #fff; box-shadow: 0 10px 26px rgba(20,30,40,.1);
}
.ld-hint { font-size: 11.5px; color: var(--dp-text3, #8a8f98); text-align: center; line-height: 1.8; margin: 0; }
.ld-note { opacity: .85; }

@media (max-width: 860px) {
  .ld-frame { height: 68vh; border-radius: 12px; }
}
</style>
