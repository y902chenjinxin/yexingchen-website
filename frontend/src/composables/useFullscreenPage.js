import { onMounted, onBeforeUnmount, getCurrentInstance } from 'vue'

/**
 * 真全屏页面（v2.46.217）
 *
 * 背景：项目里"全屏"以前有两种做法，都不对 ——
 * ① 用 `position: fixed; inset: 0` 的覆盖层（游戏放大 isBig、翻页时钟 fc-stage、
 *    音乐全屏播放器 MobileFullPlayer）：**全屏是组件状态而不是路由**，
 *    于是手机系统返回键走浏览器历史后退，直接退出整个页面，而不是退出全屏。
 * ② 内容被套在 IslandInnerBase 卡片里（游戏页、工具页）：视口里嵌一张卡片，
 *    上下左右都是站点外壳，沉浸感为零，这就是夜星说的"页面里嵌入了一个小页面"。
 *
 * 正确做法（小说阅读器 v2.46.207 已验证）：**全屏态必须有自己的 URL**。
 * 这样浏览器箭头 / 手机返回键 = 路由后退 = 退出全屏，两条路径行为一致，
 * 且能深链、能刷新、能分享。
 *
 * 本 composable 负责进入/退出时的"外壳"处理：
 * - 给 body 加 `fs-page`（全局 CSS 隐藏侧栏/顶栏/TabBar/页脚/播放条/桌宠）
 * - 锁 body 滚动
 * - 触摸设备切真机 viewport（本站手机浏览器 viewport 被 main.js 覆写成 width=1280，
 *   不切回来字号会被缩到 1/3、分栏宽度算错）
 * - 卸载时还原
 *
 * 🔴 必须配 router.afterEach 兜底（router/index.js 里已加）：组件异常卸载时
 * body 上的 class 会残留，落到的下一个页面会"没侧栏、不能滚、看着空白"。
 *
 * 用法：
 *   useFullscreenPage()                  // 普通全屏页
 *   useFullscreenPage({ viewport: false }) // 不要改 viewport（桌面为主的页面）
 */

const BODY_CLASS = 'fs-page'
const ORIGINAL_VIEWPORT = 'width=1280, viewport-fit=cover'
const DEVICE_VIEWPORT =
  'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover'

// 引用计数：万一两个全屏页短暂共存（路由过渡期间），不要互相把 class 清掉
let depth = 0
let savedViewport = ''

function isTouchDevice() {
  return (navigator.maxTouchPoints || 0) > 0 || 'ontouchstart' in window
}

function enterShellHide(switchViewport) {
  depth += 1
  document.body.classList.add(BODY_CLASS)
  if (!switchViewport || !isTouchDevice()) return
  const meta = document.querySelector('meta[name="viewport"]')
  if (!meta) return
  savedViewport = meta.getAttribute('content') || ORIGINAL_VIEWPORT
  meta.setAttribute('content', DEVICE_VIEWPORT)
}

function exitShellHide() {
  depth = Math.max(0, depth - 1)
  if (depth > 0) return
  document.body.classList.remove(BODY_CLASS)
  if (!savedViewport) return
  const meta = document.querySelector('meta[name="viewport"]')
  if (meta) meta.setAttribute('content', savedViewport)
  savedViewport = ''
}

/** 强制清理（路由兜底用）：无视计数，把残留状态一次清干净 */
export function forceExitFullscreenPage() {
  depth = 0
  document.body.classList.remove(BODY_CLASS)
  if (!savedViewport) return
  const meta = document.querySelector('meta[name="viewport"]')
  if (meta) meta.setAttribute('content', savedViewport)
  savedViewport = ''
}

/**
 * 条件式全屏（页内"放大"按钮那种）。
 *
 * 用于全屏态是**组件内部状态**的页面（游戏放大 isBig、翻页时钟舞台）——
 * 这些页面切路由会丢对局状态，所以不能改成子路由。
 * 需要调用方自己配一条 history 记录（见 pushFullscreenHistory），
 * 让系统返回键先退出全屏、而不是退出整个页面。
 */
export function enterFullscreenShell(options = {}) {
  enterShellHide(options.viewport !== false)
}

export function exitFullscreenShell() {
  exitShellHide()
}

/**
 * 往浏览器历史压一条"全屏"记录（不改 URL）。
 *
 * 为什么不改 URL：App.vue 用 `:key="route.fullPath"` 渲染路由组件，
 * **query 一变整个组件重挂载，对局状态全丢**。压历史记录能达到
 * "返回键先退出全屏"的效果，且路由完全无感。
 *
 * state 里保留原字段（`{ ...history.state }`），否则 vue-router 的 popstate
 * 处理读到不认识的 state 会乱。
 *
 * @returns {() => void} 消费掉这条记录（用户点页内"退出全屏"时调用）
 */
export function pushFullscreenHistory() {
  if (typeof history === 'undefined' || !history.pushState) return () => {}
  try {
    history.pushState({ ...(history.state || {}), __fs: 1 }, '')
  } catch {
    return () => {}
  }
  let consumed = false
  return () => {
    if (consumed) return
    consumed = true
    try { history.back() } catch { /* 忽略 */ }
  }
}

export function useFullscreenPage(options = {}) {
  const { viewport = true } = options
  const inst = getCurrentInstance()
  // 组件里没 setup 上下文时（理论上不会有）就退化成不处理，别炸
  if (!inst) return { exit: () => {} }

  let active = false

  onMounted(() => {
    if (active) return
    active = true
    enterShellHide(viewport)
  })

  onBeforeUnmount(() => {
    if (!active) return
    active = false
    exitShellHide()
  })

  return {
    /** 统一退出：走浏览器历史，和系统返回键同一条路径 */
    exit: () => {
      if (window.history.length > 1) window.history.back()
      else window.location.assign('/')
    },
  }
}
