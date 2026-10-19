# Spec：3D 棋牌大厅化 + 双游戏规则引擎接入（v2.46.122）

日期：2026-10-19
路由：`/tool/games-3d` → `frontend/src/views/Games3DView.vue`

## 1. 需求（夜星原话，5 条）

1. 进入即开局的现状要改：需要一个「选择页面」，交互参考 2D 牌局（`GamesView.vue` 大厅），牌局逻辑也参考 2D。
2. 3D 麻将与 3D 掼蛋**分开**，不再用顶栏按钮切换。
3. 3D 掼蛋的逻辑与 2D 掼蛋**一致**（接规则引擎，而不是随机抽牌）。
4. 背景现在近全黑，需要美化：加颜色 / 装饰元素。
5. 头像与积分「缠一块」（积分是头像右下角绝对定位角标），需要拆开重排。

## 2. 已确认口径（AskUserQuestion 已答，不再询问）

- 深度：麻将 + 掼蛋**都完整复刻 2D**，接本地规则引擎。
- 入口：**单入口 + 选择页**。保留 `/tool/games-3d`，进入是「3D 棋牌大厅」（选游戏 → 开局）。**去掉**顶栏麻将/掼蛋切换按钮。不拆成两个导航模块。

## 3. 现状与可复用资产（已核实）

- `Games3DView.vue`（约 700 行）：顶栏 `mode` 切换（模板 L13-16，`switchMode` L441）；`onMounted` 直接 `rebuild()` 开局；掼蛋仅随机抽牌 `playGd/aiPlayGd`（L411-429）；`.g3d-root` L465-477 深墨绿近黑；积分是 `.gt3-score` 绝对定位角标（L622-631）压头像。
- 规则引擎为**纯 JS、无 Vue 依赖、可直接复用**：
  - `frontend/src/utils/games/guandan.js`（`import * as G`）：`deal(level)→hands[4][27]`、`detectPattern(cards,level)`、`canBeat(cand,target)`、`aiChoose(hand,target,level,ctx)`、`upgradeFor(order)`、`nextLevel`、`TEAM_OF`、`levelText`、`MAX_LEVEL`、`highestRemainingSingle`。**引擎自带声明不做进贡/还贡**（上一局头游起牌）。
  - `frontend/src/utils/games/mahjong.js`（`import * as M`）：`buildDeck/shuffle/sortHand/openingPlan/dealOpening/drawOne 相关`、`isStandardHu/isSevenPairs/isFlush/isAllTriplets/isAllEyes/canHu/scoreHu/tingTiles/shanten/aiDiscard/aiWantPong/aiWantKong/chiCombos/aiWantChi/aiWantHu/findAnkongs/findBugangs/dangerOf`、`MJ_STACKS/MJ_RING/MJ_WALL_AFTER_DEAL`。**v2.46.17 起无定缺**。
- 2D 掼蛋主循环（`components/games/GuandanBoard.vue`）已读，可直接移植：
  - 状态：`teamLevel=[2,2] / roundLevel / roundNo / hands[4] / turn / target{seat,cards,pattern} / seatThrows / passCount / finished[] / phase('playing'|'settled') / sel / history / roundResult{up,winTeam,order} / matchOver / firstSeat`。
  - 函数：`newRound()`(L1184) `nextActive` `advance()`(L1210) `applyPlay(seat,cards)`(L1241) `applyPass(seat)`(L1262) `endRound()`(L1271) `nextRound()`(L1287) `aiTurn()`(L1321，ctx `{lastIsTeammate, pressure:对手最少剩牌, highestSingle}`) `scheduleAI()`(L1314，非人类座位才 AI，延时 3000–3500ms) `doPlay()`(L1518) `doPass()`(L1526) `doHint()`(L1532)。人类座位 `HUMAN_SEATS=[0]`。
  - 2D「单人练习」是本地单机，本页内嵌 Board；只有 online 才跳在线牌桌。
- 3D 原语已在 `Games3DView.vue` `<style scoped>` 内实现：`.gt3-table`(6 面挤出)、`.pc3d`/`.pc-face`/`.pc-front..right`、`.mj-front/mj-ivory/mj-edge/mj-back`、`.card-front/back`、`.gt3-compass`、`.gt3-felt/woven/vignette`；JS 变换助手 `boxVars/pieceBox/wallTF/handTF/oppTF/centerTF/seatTF/CENTER_TF/VIEW_RX`。沉浸态 `useImmersive`+`syncImmersive` 必须保留。
- `frontend/src/components/games/MahjongTileFace.vue` 是现成矢量牌面组件（props `suit,rank`）。
- 发版基线：`APP_VERSION=v2.46.121`、`sw.js=v435`。

## 4. 目标架构

```
frontend/src/
  assets/styles/games3d.css          ← 新建：全局（非 scoped）共用 3D 原语 + 大厅/背景/铭牌样式
  components/games3d/
    use3dTable.js                    ← 新建：纯函数 3D 变换助手
    Guandan3DBoard.vue               ← 新建：3D 掼蛋（接 G 引擎）
    Mahjong3DBoard.vue               ← 新建：3D 麻将（接 M 引擎）
  views/Games3DView.vue              ← 改写：3D 棋牌大厅（选择页 + 渲染 board）
```

`Games3DView.vue` 的 `<style scoped>` 不再承载 3D 原语（scoped 样式不会作用到子组件），改由 `games3d.css` 全局提供；组件内 `import '@/assets/styles/games3d.css'`。

### 4.1 `assets/styles/games3d.css`（全局）

类名统一前缀 `g3d- / gt3- / pc3d- / mj- / card-`（现有文件无冲突）。内容：
1. 从现 `Games3DView.vue` 样式**搬运**：`.gt3-table`、`.gt3-face`、`.gt3-top/bottom/left/right/front/back`、`.gt3-felt/woven/vignette`、`.gt3-compass`、`.cw*`、`.pc3d`、`.pc-face`、`.pc-front/back/top/bottom/left/right`、`.mj-front/ivory/edge/back`、`.card-front/back`、`.cf-rank/.cf-suit`。
2. **背景美化**（需求 4）：`.g3d-root` 由近黑改为「深空冷蓝 + 光点线条」：
   - 多层 `radial-gradient` 冷蓝光晕（`#0e1b33/#101a2e` 系）+ 底部暗角；
   - 叠加点阵/网格纹理（`repeating-linear-gradient` 或 `radial-gradient` 星点）与一条桌沿光带；
   - 可加轻微漂浮装饰层（`g3d-deco`），纯 CSS 不引入图片。
3. **大厅**（需求 1）：`.g3d-lobby`（居中标题 + 副标题）、`.g3d-lobby-cards`（两张大卡）、`.g3d-lobby-card`（毛玻璃/玻璃质感，含图标、名称、描述、「开局」按钮，hover 微光克制）。
4. **座位铭牌重排**（需求 5）：`.gt3-seat` 改为「头像 / 名字 / 积分」**分行或分栏**，**移除** `.gt3-score` 的 `position:absolute; right/bottom:-8px` 角标写法，积分改为铭牌内独立行/独立 chip（含 `is-you` 高亮）。
5. 棋盘顶栏通用件：`.g3d-topbar`、`.g3d-op`（含 `.on/.ghost`）、`.g3d-title/.g3d-logo/.g3d-tx`。

### 4.2 `components/games3d/use3dTable.js`（纯函数，无响应式）

```js
export const VIEW_RX = 66
export const CENTER_TF = 'translate(-50%,-50%) translate3d(0px,0px,240px) scale(0.16)'
export function boxVars(w, h, t) // → { '--w':'Npx','--h':'Npx','--t':'Npx' }
export function pieceBox(dealt, w, h, t, finalTF, delayIdx, clickable, instant)
  // dealt=false 时收拢到 CENTER_TF；instant 时无错峰；clickable 决定 cursor
export function wallTF(side, i, n)   // 'N'|'W'|'E'，同现实现
export function handTF(i, n, stand)  // stand=立牌（麻将）/ 平贴（掼蛋）
export function oppTF(side, k, n)    // 'N'|'W'|'E'
export function centerTF(i, lift = 40)
export function seatTF(s)            // billboard，rotateX(-VIEW_RX)
```
数值与现实现保持一致（step、z 高度等）。

### 4.3 `views/Games3DView.vue`（改写为大厅）

- `import '@/assets/styles/games3d.css'`；`import Guandan3DBoard from '@/components/games3d/Guandan3DBoard.vue'`；`import Mahjong3DBoard from '@/components/games3d/Mahjong3DBoard.vue'`。
- 状态：`phase = ref('lobby')`、`game = ref(null)`（`'mahjong'|'guandan'`）。
- `lobby`：decorated `.g3d-root` + `.g3d-lobby`，两张大卡「3D 麻将」「3D 掼蛋」，点「开局」→ `game=…; phase='play'`。
- `play`：`<component :is="game === 'mahjong' ? Mahjong3DBoard : Guandan3DBoard" @exit="backToLobby" />`；board 自带顶栏与透明背景（背景由大厅 `.g3d-root` 提供）。
- 保留 `useImmersive` + `syncImmersive` 与 resize/orientationchange 监听；离开路由时 `exitImmersive`。
- **删除** `mode` 切换按钮、`switchMode`、`rebuild/buildMjHand/buildGdHand` 等演示逻辑。

### 4.4 `components/games3d/Guandan3DBoard.vue`（3D 掼蛋，接 G 引擎）

- `props`: 无（或 `{}`）；`emit: ['exit']`；自带顶栏（`第 N 局`、`我方 X / 对方 Y 级`、`重新开始`、`返回`）。
- 移植 2D solo 循环（见 §3）：`HUMAN_SEATS=[0]`；`G.deal` 发牌、`G.detectPattern/canBeat` 校验、`G.aiChoose` AI、`G.upgradeFor/nextLevel` 升级、`G.TEAM_OF` 分队；AI 延时 3000–3500ms；`advance/applyPlay/applyPass/endRound/nextRound/doPlay/doPass/doHint` 与 2D 语义一致（含接风、一圈结束清空中央、4 名排序、matchOver 重置）。
- 3D 渲染：复用 `.gt3-*/.pc3d/.card-*`；4 座位铭牌（重排后）、对手 3 面牌背、玩家 27 张手牌（`.gd-hand`，选中抬升）、各座位中央出牌区（`.centerTF`）。
- 牌面文本：`G.RANK_TEXT` / `c.suit`（♥♦ 红）/ joker『大/小』；逢人配高亮 `G.isWild(c, level)`。
- 操作：点选出牌（点击切换选中）、`出牌`（`doPlay`）、`不要`（`doPass`，无 target 时禁用）、`提示`（`doHint`）；结算浮层 `再来一局/重新开始`。
- **跳过** 2D 特有：语音 TTS/音效、划选手势、上滑出牌、存档、在线同步、进贡/还贡、倒计时。

### 4.5 `components/games3d/Mahjong3DBoard.vue`（3D 麻将，接 M 引擎）

- `props`: 无；`emit: ['exit']`；自带顶栏（庄家/番、`重新开始`、`返回`）。
- 移植 `components/games/MahjongBoard.vue` solo 循环（**执行时以该文件实际实现为准**，v2.46.17 起无定缺）：`startGame/dealRound/drawOne/discardTile/advance/aiTurn/react`；`M.buildDeck/dealOpening/canHu/scoreHu/tingTiles/aiDiscard/aiWantPong/aiWantKong/chiCombos/aiWantChi/aiWantHu/findAnkongs/findBugangs`；胡牌即结束（一炮只取一家）。
- 3D 渲染：四面牌墙（`.mj-wall`，可按 `M.stackRemain` 显示剩牌）、玩家手牌（`.mj-hand` 立牌 + `MahjongTileFace`）、副露 melds、中央牌河/出牌区、听牌提示。
- 操作：摸打（点手牌打出）、碰 / 杠 / 胡 / 过（react 队列）、`提示` 听牌；结算浮层。
- **跳过** 2D 特有：语音/音效、划选、存档、在线同步。

## 5. 验收标准（对应 5 条需求）

1. 进入 `/tool/games-3d` **先看到选择页**（3D 棋牌大厅），点卡片才开局。
2. 顶栏**没有**麻将/掼蛋切换按钮；两游戏各自独立进入。
3. 3D 掼蛋可完整打完一局：发牌 27 张、牌型识别、压牌/不要、四家轮转、名次、升级、`再来一局`。
4. 背景**非全黑**，有冷蓝光晕 / 纹理 / 装饰。
5. 座位铭牌上头像与积分**不再重叠**，分栏/分行清晰。

## 6. 验证方式

- `npm run build`（node 不在 PATH，先注入 `C:\Users\123\.workbuddy\binaries\node\versions\22.22.2-6` 到 `$env:Path`；cwd `yexingchen-website\frontend`）零错误通过。
- **不自动做现网浏览器验收**（夜星偏好 2026-10-11），由夜星自行验收。

## 7. 发版

- `frontend/public/sw.js`：`xuanhuang-v435` → `v436`。
- `frontend/src/constants/version.js`：`APP_VERSION` → `v2.46.122`。
- `docs/CHANGELOG.md` 顶部加条目；`docs/ISSUES.md` 更新 V246105-001（「3D 棋牌是纯前端演示、不接后端」→ 改为接本地规则引擎）。
- 部署：仓库根 `python scripts/deploy_frontend.py`（是否需要部署按夜星指示）。
