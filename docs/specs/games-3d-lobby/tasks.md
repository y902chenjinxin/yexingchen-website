# Tasks：3D 棋牌大厅化 + 双游戏规则引擎接入

对应 `spec.md`。执行顺序如下。

- [x] **T1 — 建全局样式 `frontend/src/assets/styles/games3d.css`**
  搬运 3D 原语；新增背景美化（冷蓝光晕/纹理/光点）、大厅卡、座位铭牌分栏、棋盘顶栏与 `.g3d-btn/.g3d-ctl/.g3d-toast/.g3d-over` 通用件。

- [x] **T2 — 建 `frontend/src/components/games3d/use3dTable.js`**
  导出 `VIEW_RX/CENTER_TF/boxVars/pieceBox/wallTF/handTF(自适应步长+lift)/oppTF/centerTF/seatTF/screenPos/SEAT_SLOT`。

- [x] **T3 — 改写 `frontend/src/views/Games3DView.vue` 为大厅**
  `phase=lobby|play`、`game`，两卡开局，play 渲染对应 board；删除 mode 切换/演示逻辑；保留沉浸态同步。

- [x] **T4 — 建 `frontend/src/components/games3d/Guandan3DBoard.vue`**
  移植 2D 掼蛋 solo 循环 + G 引擎（`deal/detectPattern/canBeat/aiChoose/upgradeFor/nextLevel`）；3D 渲染 + 选牌/出牌/不要/提示/重开/返回。

- [x] **T5 — 建 `frontend/src/components/games3d/Mahjong3DBoard.vue`**
  移植 2D 麻将 solo 循环 + M 引擎；3D 渲染 + 摸打/碰·杠·吃·胡·过/暗杠/补杠/听牌/重开/返回。

- [x] **T6 — 接入 + 构建验证**
  `npm run build` 两次通过（含麻将补吃/暗杠/补杠、掼蛋积分栏改为「级」后复跑）。

- [x] **T7 — 发版（不含部署）**
  `sw.js`→v436、`version.js`→v2.46.122；`CHANGELOG.md` 新增条目；`ISSUES.md` 新增 V246122 段（更新 V246105-001 口径）。
