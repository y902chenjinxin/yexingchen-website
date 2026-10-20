/**
 * 图标查表入口 —— 把各域注册表合并成一张 emoji → SVG 的表。
 *
 * 优先级（先命中先返回）：
 *   1. `utils/icons/appIcons.js`    —— 天气 / 人物头像 / 通用 UI / 物件；
 *   2. `utils/icons/gameIcons.js`   —— 棋牌道具、事件格、对局结果、状态圆点；
 *   3. `utils/finance/ledgerIcons.js` —— 记账页 38 枚（v2.46.125 已上线验收，
 *      与后端 EXPENSE_CATEGORIES / INCOME_CATEGORIES 的 emoji 一一对应）。
 *
 * 记账表之所以放最后：它是唯一已经上线被验收过的一批，避免新表里语义相近的
 * 写法把它覆盖掉（收入 / 支出分类图标必须保持线上原样）。
 * 三张表都不命中时返回空串，调用方（AppIcon.vue）回落渲染原字符 ——
 * 用户自己从输入法挑的 emoji、历史怪数据都不会变成空白。
 *
 * 变体选择符（U+FE0E / U+FE0F）先归一化再查表：'🛍️' 与 '🛍' 视为同一个键。
 */
import { ICONS as APP_ICONS } from './appIcons'
import { ICONS as GAME_ICONS } from './gameIcons'
import { ledgerIconBody } from '../finance/ledgerIcons'

const norm = (s) => String(s ?? '').replace(/[\uFE0E\uFE0F]/g, '').trim()

/** 合并后的表：键为归一化后的 emoji */
const TABLE = {}
for (const src of [APP_ICONS, GAME_ICONS]) {
  for (const [k, v] of Object.entries(src)) {
    const key = norm(k)
    if (!TABLE[key]) TABLE[key] = v
  }
}

/** 取图标内部 SVG；返回空串表示「表里没有，按原字符渲染」 */
export function appIconBody(icon) {
  const key = norm(icon)
  if (!key) return ''
  if (TABLE[key]) return TABLE[key]
  // 记账域另有自己的归一化实现，兜一层以防两处 norm 行为不一致
  return ledgerIconBody(key)
}

/** 已收录的图标数（设计稿与自检脚本用） */
export const APP_ICON_COUNT = Object.keys(TABLE).length
