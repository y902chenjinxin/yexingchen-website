/**
 * 全站模块注册表（单一真源）。
 *
 * 桌面侧栏（DesktopSidebar）与手机端模块目录（ModulesView）都读这里，
 * 避免两端各维护一份导致「PC 有、手机没有」。新增二级模块只改这一处。
 *
 * 结构：
 * - 一级模块 = 数组里的一项（`label` 为空串表示不显示分组标题，目前只有「工作台」这样）
 * - 二级模块 = `items` 里的一项；`external: true` 表示外链静态站，用原生 <a> 打开
 * - `superOnly: true` 只有超管可见（由 buildNavModules 过滤）
 */
import {
  House,
  Headset,
  Reading,
  VideoPlay,
  Apple,
  EditPen,
  Bell,
  MapLocation,
  Money,
  TrendCharts,
  Notebook,
  Calendar,
  ChatLineRound,
  Connection,
  Compass,
  Coin,
  UserFilled,
  Lock,
  Menu,
  Coffee,
  Message,
  Grid,
  Football,
  Refresh,
  Box,
  Suitcase,
  Bowl,
} from '@element-plus/icons-vue'

export const NAV_GROUPS = [
  {
    label: '',
    items: [
      { path: '/workbench', title: '工作台', icon: House },
    ],
  },
  {
    label: '内容',
    items: [
      { path: '/music', title: '音乐', icon: Headset },
      { path: '/novel', title: '小说', icon: Reading },
      { path: '/video', title: '视频', icon: VideoPlay },
      { path: '/log', title: '日志', icon: EditPen },
      { path: '/tool', title: '工具', icon: Bell },
      { path: '/notes', title: '笔记云台', icon: Notebook },
    ],
  },
  {
    label: '生活',
    items: [
      { path: '/life/weight', title: '体重记录', icon: Apple },  // v2.41 由「体重三餐」拆出
      { path: '/life/meals', title: '美食记忆', icon: Bowl },    // v2.41 只记大餐 / 纪念餐
      { path: '/tool/countdown', title: '时光痕迹', icon: Calendar },
      { path: '/tool/lifegrid', title: '人生 4000 周', icon: Grid },
      { path: '/tool/capsule', title: '时间胶囊', icon: Message },
      { path: '/tool/fish', title: '摸鱼日历', icon: Coffee },
      { path: '/travels', title: '足迹地图', icon: MapLocation },
      { path: '/finance/book', title: '记账', icon: Money },
      { path: '/lost', title: '遗失物件', icon: Box },
      { path: '/wardrobe', title: '穿搭推荐', icon: Suitcase },
      { path: '/vault', title: '密码保险箱', icon: Lock },
      { path: '/contacts', title: '通讯录', icon: Compass },
      { path: '/subscriptions', title: '订阅', icon: Coin },
    ],
  },
  {
    // v2.40.23：娱乐由「生活 › 娱乐」二级子模块提升为一级模块
    label: '娱乐',
    items: [
      { path: '/tool/games', title: '棋类游戏', icon: Football },
      { path: '/tools/liferestart/index.html', title: '人生重开模拟器', icon: Refresh, external: true },
    ],
  },
  {
    label: '财经',
    items: [
      { path: '/finance/market', title: '行情', icon: TrendCharts },
      { path: '/finance/news', title: '资讯', icon: Connection },
    ],
  },
  {
    label: '智能',
    items: [
      { path: '/assistant', title: 'AI 对话', icon: ChatLineRound },
    ],
  },
]

const ADMIN_GROUP = {
  label: '管理',
  items: [
    { path: '/admin/users', title: '用户管理', icon: UserFilled, superOnly: true },
    { path: '/admin/roles', title: '角色管理', icon: Lock, superOnly: true },
    { path: '/admin/menus', title: '菜单管理', icon: Menu, superOnly: true },
  ],
}

/**
 * 按角色产出可见模块树。
 * - 非超管剔除 `superOnly` 条目与「管理」分组
 * - 顺带丢掉空分组，避免出现只有一个标题的空壳
 */
export function buildNavModules(isSuper = false) {
  const groups = NAV_GROUPS.map((g) => ({
    ...g,
    items: g.items.filter((it) => !it.superOnly || isSuper),
  }))
  if (isSuper) groups.push(ADMIN_GROUP)
  return groups.filter((g) => g.items.length > 0)
}

/** 模块总数（不含分组标题），用于手机端目录页头计数 */
export function countNavItems(groups) {
  return groups.reduce((n, g) => n + g.items.length, 0)
}

/**
 * 路径命中判断：进入子页（如 /tool/countdown/123）时父条目也要高亮。
 * 口径与桌面侧栏完全一致，避免同一路由在两端口径不同、出现「两个菜单同时亮」。
 */
const EXACT_MATCH_PATHS = new Set([
  '/workbench',
  '/finance/market',
  '/finance/news',
  '/finance/book',
  '/admin/users',
])

// 这些内置工具挂到了「生活 / 娱乐 / 通讯录」等模块下，点它们时不该把「工具」一并点亮
const TOOLS_IN_OTHER_MODULES = [
  '/tool/countdown', '/tool/lifegrid', '/tool/capsule', '/tool/fish',
  '/tool/muyu', '/tool/games', '/tool/contactsmap',
]

export function isNavItemActive(path, currentPath) {
  if (path === '/workbench') return currentPath === '/workbench'
  if (path === '/notes') return currentPath === '/notes' || currentPath.startsWith('/notes/')
  if (path === '/contacts') return currentPath === '/contacts' || currentPath.startsWith('/tool/contactsmap')
  if (path === '/tool/countdown') return currentPath.startsWith('/tool/countdown')
  if (path === '/admin/users') return currentPath === '/admin' || currentPath === '/admin/users'
  if (path === '/tool') {
    return currentPath === '/tool'
      || (currentPath.startsWith('/tool/')
        && !TOOLS_IN_OTHER_MODULES.some((p) => currentPath.startsWith(p)))
  }
  if (EXACT_MATCH_PATHS.has(path)) return currentPath === path
  return currentPath === path || currentPath.startsWith(path + '/')
}
