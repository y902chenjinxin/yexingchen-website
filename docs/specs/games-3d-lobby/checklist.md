# Checklist：3D 棋牌大厅化 + 双游戏规则引擎接入

对应 `spec.md` §5 验收标准。区分「可静态核验」与「需夜星现网验收」。

- [x] **构建**：`npm run build` 零错误通过（含全部改动后复跑）。
- [x] **需求2（静态）**：`Games3DView.vue` 已无麻将/掼蛋切换按钮与 `switchMode`。
- [x] **需求1（静态）**：`Games3DView.vue` 默认 `phase='lobby'`，进入即选择页；点卡片才 `phase='play'`。
- [x] **需求3（静态）**：`Guandan3DBoard.vue` 已接 `guandan.js` 引擎，含 `newRound/advance/applyPlay/applyPass/endRound/nextRound/aiTurn/doPlay/doPass/doHint`。
- [x] **发版（静态）**：`sw.js`=v436、`version.js`=v2.46.122、CHANGELOG/ISSUES 已更新。
- [ ] **需求3（运行）**：3D 掼蛋能完整打完一局（发牌 27 张 / 压牌 / 四家轮转 / 名次 / 升级 / 再来一局）。— 待夜星现网验收
- [ ] **需求1/3（运行）**：3D 麻将能摸打、碰杠吃胡过、胡牌结束。— 待夜星现网验收
- [ ] **需求4（视觉）**：背景非全黑、有冷蓝光晕与装饰。— 待夜星验收
- [ ] **需求5（视觉）**：座位铭牌头像与积分分栏、不重叠。— 待夜星验收
