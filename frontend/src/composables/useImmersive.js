import { computed, ref } from 'vue'

/**
 * 全屏沉浸态（牌桌 / 全屏对局）。
 *
 * 背景（V2461-001）：移动端底部 Tab 栏是 `position: fixed; z-index: 1500`，
 * 而单机牌桌全屏舞台只有 z-index 400（在线房间牌桌是 3000）—— 于是**单机**玩掼蛋时
 * Tab 栏压在牌桌底部操作区上，按钮点不到、手牌被盖。只抬 z-index 是治标：
 * 桌宠(1800)、阅读条等其它常驻浮层同样会干扰。这里给一个全局开关，
 * 沉浸期间由 App.vue 统一收起这些常驻浮层。
 *
 * 用**引用计数**而不是布尔值：可能有多个组件先后进入/退出（例如从在线房间牌桌
 * 再跳进结算全屏），布尔值会被后一个的退出动作误清掉前一个的状态。
 */

const depth = ref(0)

export function useImmersive() {
  const immersive = computed(() => depth.value > 0)

  function enterImmersive() {
    depth.value += 1
  }

  /** 幂等退出：不会把计数压到负数 */
  function exitImmersive() {
    depth.value = Math.max(0, depth.value - 1)
  }

  return { immersive, enterImmersive, exitImmersive }
}
