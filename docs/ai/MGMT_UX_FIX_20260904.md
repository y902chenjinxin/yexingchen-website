# 管理页交互修复 + 桌宠行为优化 + 搜索按钮化

日期：2026-09-04
范围：音乐 / 小说 / 视频 / 工具 四个模块管理页 + 全局桌宠 + 管理搜索

## 一、背景与问题

用户在多个会话中反馈以下 4 类问题，均经**线上浏览器实测取证**确认：

1. **管理页按钮失效（四模块一致）**
   - 上传：打开弹窗后"选择文件"拉不起本地文件选择器；
   - 编辑：点击"编辑"弹窗不出/点不动；
   - 删除：点击"删除"弹出英文确认框（OK/Cancel），且盖在整页之上，用户感知为"跳到工作台首页"。
2. **桌宠归位**：桌宠每次停止（散步停、拖拽松手）都被强制拉回右下角初始地，而不是停在原地。
3. **桌宠越界**：自动跑步（runAcross）会穿屏跑出边界，散步/拖拽也可能贴边越界。
4. **搜索无按钮**：管理搜索框只能回车触发，没有"查询"按钮；用户要求加按钮 + 明确模糊查询。

## 二、线上取证结论（证据）

- 已登录身份：管理员（工作台显示"🌙 管理员"）。
- 音乐管理页：
  - 上传弹窗可打开，但"选择文件"按钮正上方与祖先链存在 `z-index:10001` 的 `position:fixed` 元素（`.whale-stage` / `.whale-frame`），且 `.whale-frame` 为 `pointer-events:auto` → 拦截弹窗内按钮点击。
  - 编辑：点击无弹窗反应（openEdit 未触发或被遮挡）。
  - 删除：`ElMessageBox.confirm` 确认按钮文字为英文 OK/Cancel（Element Plus 未配置 `zh-cn` locale，`main.js` 仅 `app.use(ElementPlus)`）；确认框盖在全页视口。
- 工具管理页："添加"弹窗同样存在被 `z-index:10001` 的 `.whale-stage` 覆盖的交互问题（复现一致）。

### 根因判定

- **英文弹窗**：`frontend/src/main.js` 未配置 Element Plus 中文 locale。
- **按钮失效 / 弹窗盖到别处**：桌宠组件 `.whale-stage` 全局 `position:fixed; z-index:10001`，高于 Element 弹出层默认 `z-index`（el-dialog≈2000，ElMessageBox≈2001 级），导致所有 `append-to-body` 的管理弹窗/确认框被桌宠压在下面、或因 `.whale-frame` 的 `pointer-events:auto` 拦截而点不到。
- **删除确认"跳到首页"**：`ElMessageBox` 挂载到 `body` 顶层、按视口居中，视觉上脱离管理页；用户希望确认框出现在管理页内。

## 三、修复方案

### 需求 1：管理页按钮全面修复（t3 / t4）

1. **全局中文 locale**（`frontend/src/main.js`）：
   - `import zhCn from 'element-plus/es/locale/lang/zh-cn'`
   - `app.use(ElementPlus, { locale: zhCn })` → 所有 ElMessage/ElMessageBox/分页等立即中文。
2. **降低桌宠层叠**（`WhaleCompanion.vue`）：
   - `.whale-stage` z-index 从 `10001` 降至 `1800`（高于普通页面内容、低于 Element 弹出层 2000 级），保证管理弹窗/确认框始终在桌宠之上、可点击。
   - 说明：桌宠仍需盖在普通内容上，1800 足够；同时避免与任何自带更小 z-index 的弹窗冲突。
3. **管理页内统一中文对话框**：
   - 删除确认：四模块（Music/Novel/Video/Tool）管理页从 `ElMessageBox.confirm` 改为组件内 `el-dialog` 中文确认框（"确认删除「XXX」吗？"，确定/取消），不再弹到全局层。
   - 编辑：确认 `showEdit` 的 `el-dialog` 正常触发与展示（修复遮挡后即可点开），保留现有编辑表单项。
   - 上传/添加：修复遮挡后弹窗内"选择文件/添加"可正常使用；同时把上传/添加/编辑表单弹窗统一为管理页内 `el-dialog`。
4. **四模块一致性**：音乐/小说/视频/工具的管理页全部按钮（添加/上传、编辑、删除、翻页分页器）统一走上述逻辑并逐一浏览器实测。

### 需求 2：桌宠停止停在原地（t5）

- 移除/改写"归位"逻辑：`stopWalk()`、`onPointerUp`、`endAutoWalk` 停止时**只停住当前位置**，不再 `right:30px; bottom:40px; left:auto` 复位。
- 停止时保持当前 `bottom` 高度（沿用当前位置的行内 left/style），仅结束动画。
- 下次自动跑步/散步从当前位置出发（随遇而安）。

### 需求 3：桌宠全部横移限界 + 边界镜像调头（t6）

- 所有横移（自动 `runAcross`、散步 `toggleWalk`、手动拖拽）统一约束在左右边界 `[0, innerWidth - 桌宠实际宽度]` 内。
- 到边界时**镜像调头**：`flipped` 用 `scaleX(-1)` 翻转素材（正脸朝前），非倒着走。
- 自动跑步 `runAcross` 不再穿屏跑出屏外，改为边界内来回；散步模式保持边界内来回。
- 拖拽：拖动位置被钳位在左右边界内，松手停在钳位后的位置（拖拽也限界，用户已确认）。
- 边界宽度以桌宠实际可见宽度（含 `transform: scale(0.75)` 后）计算。

### 需求 4：搜索按钮化 + 仅按钮触发 + 模糊查询（t7）

- 四模块管理搜索框旁新增"查询"按钮。
- **仅按钮触发**：输入关键字和回车不自动请求；点"查询"才发请求；"清空筛选"只清空关键字 UI，需再点"查询"恢复全量（用户已确认）。
- 移除现有 `watch(keyword)` 的"清空即自动刷新"逻辑，严格改为按钮触发。
- 模糊查询：后端已完成 `LIKE contains`（音乐/小说 title+artist，视频 title+category，工具 title+description），保持续用。

## 四、验收标准

- 音乐/小说/视频/工具管理页：上传/添加可选定本地文件、编辑可打开并保存、删除在管理页内弹中文确认、分页可用，全程无英文、不为桌宠遮挡。
- 桌宠停止后停留在原位置，不归位右下角。
- 桌宠自动跑步/散步/拖拽均不出左右边界，到边界正脸镜像调头。
- 四模块搜索框有"查询"按钮，仅按钮触发，模糊查询生效。

## 五、落地顺序

1. main.js 配中文 locale；
2. WhaleCompanion.vue 降 z-index + 停止停原地 + 全横移限界调头（合并 t5/t6 一次改完）；
3. 四模块删除确认改管理页内中文 dialog、确认编辑/上传弹窗可用；
4. 四模块搜索加"查询"按钮 + 仅按钮触发；
5. 构建 dev 自测脚本无关 → 直接 prod 构建部署；
6. Nginx 生产 deployment：构建 → 部署 → 清 SW 版本 → 线上浏览器逐模块实测截图；
7. 更新 WORK_LOG.md / CURRENT_STATE.md / HISTORY.md，删除临时脚本，git 提交并推送 GitHub master。

## 六、本地实测验收结果（2026-09-04）

本地环境（前端 http://localhost:5173，后端 :8000，解析 :8070，DB=yexingchen.db）以 admin@yexingchen.cn 登录后，浏览器端到端逐项实测：

| 项 | 结果 | 证据 / 现象 |
|----|------|-------------|
| 音乐管理页中文 + 删除弹窗 | PASS | 表头/弹窗全中文，删除确认「删除确认」出现在管理页内居中，不跳站首页（music_page/music_delete_dialog） |
| 音乐上传弹窗 | PASS | 弹出文件选择对话框，可拉起本地文件选择器（music_upload） |
| 音乐编辑弹窗 | PASS | 点编辑弹出管理页内中文编辑表单（music_edit_dialog） |
| 音乐搜索「查询」按钮 + 模糊 | PASS | 搜索框旁有「查询」按钮，输入即显示匹配条数 |
| 小说管理页 | PASS | novel_manage：中文 + 删除中文弹窗 + 查询按钮 |
| 视频管理页 | PASS | video_manage/video_search/video_delete_dialog：中文 + 查询按钮 + 中文删除确认 |
| 工具管理页 | PASS | tool_manage/tool_search/tool_delete_dialog：中文 + 查询按钮 + 中文删除确认 + 添加对话框 |
| 桌宠拖拽停留 | PASS | 拖到中间偏左松手后停留原位不回归角落（computed left/top 保持） |
| 桌宠左右限界 | PASS | 移到右缘 left 稳定 244px、左缘 0px，均未穿屏 |
| 桌宠边界镜像调头 | PASS（代码+位置） | tick() 边界翻转 dir + CSS `scaleX(-1)` 正脸镜像，非倒着走 |

说明：桌宠边界反向的「动画翻转」以代码 `scaleX(-1)` + 位置钳位双重保证；四模块删除仅验证弹窗（未真删）以保护测试数据。本地测试数据已 seed（tools4/music4/novels3/videos3，is_test_data=1）。本地 admin 密码临时重置为 Admin@1234（开发库，不在 git）。

### 追加修复（2026-09-04 晚）：上传/编辑/删除「仍然没反应」

用户上传现场截图复查：按钮在新界面可见但真实物理点击无反应。浏览器以 elementFromPoint + 真实坐标点击在窄屏视口复现，锁定新根因：

- **根因**：`IslandInnerBase.vue` 的 `.island-inner`（岛屿内页**全屏容器**）为 `position:fixed; inset:0; z-index:10001`。此 10001 高于 Element Plus 弹层（约 2000 级）与桌宠（1800），把挂到 body 的「上传/编辑/删除」弹窗**整页压在容器之下**，弹窗其实弹出但被岛屿背景盖住 → 表现"点击按钮没反应"。窄屏视口下尤为明显（首轮验证依赖 JS 程序化点击与桌面视口，未能暴露）。
- **修复（SW 升 `xuanhuang-v18`）**：`.island-inner` z-index `10001 → 1`（保持 `fixed` 全屏布局，但不再压住任何弹层）。全局规则，桌面/窄屏均生效。
- **线上复测**：`.island-inner` z-index 实测为 `1`；上传、编辑真实物理点击均弹出可见对话框；elementFromPoint 命中按钮自身，不再命中容器。
- **残留（仅边缘态）**：底部音乐播放条 `npbar`（播放中显示，`z-index:980`）悬浮时，若表格行恰好滚动到播放条矩形（底部中央），该处按钮点击被播放条盖住。与本次修复无直接关系，待评估是否需额外留白/隐藏处理。