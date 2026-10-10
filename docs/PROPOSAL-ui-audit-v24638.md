# UI 一致性审查 · 手机端 + 桌面端（v2.46.38 候选）

> 2026-10-10 夜星：「再找找手机端和电脑端的 UI 优化点，仔细看」。
> 两路并行审查 + 关键点人工核实（蓝紫主色 / 暗玻璃输入框 / 硬编码涨跌色均已确认属实）。

## 结论

手机端的短板集中在**体系没铺到的角落**（EP 弹层、三个整页、四个工具页按钮）；桌面端的短板集中在**页面 scoped 样式绕过令牌**（暗玻璃输入框、黑雾 hover 阴影、硬编码涨跌色）。以下按「做了立刻见效」排序。

---

## A 批 · P0 体系级（手机端，性价比最高）

### A1. EP 弹层 teleport 断点（一处修复全局生效）⭐
- `#app.is-mobile` 只挂在 `#app` 上，而 el-select / el-date-picker 的 popper、ElMessageBox 默认 **teleport 到 body** → paper.css/mobile-product.css 里所有 `#app.is-mobile .el-select__popper`、`.el-message-box` 规则**永远不命中**。
- 手机端下拉、日期面板、MessageBox 至今是 EP 默认白底蓝紫样式，宣纸夜间下是突兀白块。
- 修法：mobile-paper.css 末尾加一组 **body 级规则**（`html[data-theme="day"] .el-select__popper` / `.el-message-box` 等，不依赖 #app 前缀），不必逐组件 `:teleported="false"`。

### A2. EP 主色仍是蓝紫 ⭐
- `mobile-native-glass.css:16-31`：`--el-color-primary` 系 7 个变量全部蓝紫（日 `#5b6ae0`），且挂在 `#app.is-mobile` 上——#app 内的 checkbox/switch/radio/分页/focus ring 全是蓝紫，teleport 的弹层反而继承不到（连蓝紫都拿不到，用 EP 默认蓝）。
- 修法：paper.css 挂 **html 级**重映射：夜=鎏金 `--xz-gold`、日=赭石 `--xz-ochre`，light-3~9/dark-2 按亮度梯度配齐。

### A3. CountdownDetailView / LogView / NovelView 三整页接入
- **CountdownDetailView**：多处 blur 玻璃卡 + 深底浅字标签（`#a8d3ce`/`#e4d9bd`/白 75%），日间宣纸上不可读；`.cdd-page` 不在背景组。
- **LogView**：动作 chip 硬编码浅字（`#7cc2a6`/`#b8c5d4`/`#dbbe85`），日间对比 <2:1；卡片底用桌面令牌 `--dp-surface`。
- **NovelView**：`.manage-pane` 用 `--ls-glass` + blur(14px)，旧金 `#c7a96b` 残留。
- 修法：三页根容器入背景组、主卡入贴纸卡组，硬编码色换 `--m-positive/--m-negative/--m-warning/--xz-gold`。

### A4. `#061513` 深字根治（删掉 v2.46.34 补丁的根）
- `mobile-product.css:153,187,370,432,465` 五处 `color:#061513 !important` 配 `--m-accent` 底——v2.46.34 只在 paper 层补了 4 处漏网，属于打地鼠。
- 修法：product 层直接改 `var(--xz-btn-fg)`，删除 paper 补丁段，结构一次到位。

### A5. 四个工具页按钮收编（岛壳接了、岛芯没接）
- AsrToolView `:193` 金渐变按钮、CapsuleToolView `:151` 金底白字、FishToolView `:201` 旧金渐变条、PoemToolView `:53` 硬编码米色纸底（夜间是亮块钉在墨夜上）。
- 修法：换 `--xz-btn-bg/--xz-btn-fg/--xz-card-2`。

---

## B 批 · P0/P1 桌面端质感

### B1. 输入框大收编（消灭两页白天破相）⭐
- StocksView `.st-input/.st-sug-item/.st-cell-input`（:445,449,480）背景 `rgba(11,15,20,.35)`、FinanceView `.fin-note-input/.fin-filter-input`（:1906,2108）背景 `rgba(0,0,0,.15)`——白天主题深字压深底不可用。
- 修法：删掉这些 scoped 覆盖，吃 `desktop-product.css:669-729` 已有的全局控件皮肤（昼夜自动正确）。

### B2. 涨跌/状态色令牌化 ⭐
- WorkbenchView `#34d399/#f87171`（:212-213,230-231，且**涨绿跌红，方向反了**）、StocksView `#D8504F/#3F968E`（:421-434）、GamesView `#D8504F`，共约 10 处硬编码。
- 修法：主题文件补 `--dp-up/--dp-down` 各一次定义（涨红跌青，中国惯例），10 处替换；顺带收编 ProfileView 上古 Bootstrap 红 `#d9534f`。

### B3. hover 黑雾阴影统一
- WorkbenchView 五处 `0 22px 56px rgba(0,0,0,.32)` 重黑阴影（:210,246,276,294,326），白天是白卡上的灰雾；骨架层基线是「hover 只聚焦描边」。
- 修法：换 `var(--dp-glow)` 聚焦描边 + `--dp-line-strong`。

### B4. ProfileView 桌面对齐 --dp-*
- 全站唯一渐变金字标题（:490-493，白底对比不足）+ 修仙主题深青玻璃卡 `--xiu-card` + blur(14px) + `0 16px 40px` 重黑阴影（:504-511）。
- 修法：卡片对齐 `.wd-card` 三件套（`--dp-surface/--dp-line/--dp-shadow`），标题改实色 `--dp-text`。

### B5. el-dialog 桌面皮肤（3 行）
- `desktop-product.css` M 节只做了弹窗让位定位，无表面皮肤：圆角仍是 EP 默认 4px，比卡片廉价一档。
- 修法：补 `.el-dialog { border-radius: var(--dp-radius); background: var(--dp-surface); }`。

### B6. NotesView 桌面 blur 残留
- `.nt-*` 内容卡自带 blur(12px)（:240-249），违反「实色面、玻璃只留浮层」基线（.glass 被收口了，.nt-* 漏网）。

---

## C 批 · P2 锦上添花（可缓）

- **C1** 页面标题六种规格并存（28/26/24/22/32px、字距 0~.12em）→ 统一一档 `.dp-page-title`（24-26px / 650 / -.01em）。
- **C2** hover 过渡十种时长混用、`transition: all` 泛滥 → 统一 `var(--motion-fast/med) var(--ease-standard)`（desktop-product.css 已定义，只有 LifeView 在用）。
- **C3** FinanceView 桌面约 30 处 `rgba(127,168,163,.x)`/`rgba(199,169,107,.x)` 裸字面量 → 换 `--yq-gold-faint/--yq-gold`（体量大，单独一批）。
- **C4** mobile-deink.css 与 paper 衬线规则语义相反的死规则段 → 标注废弃。
- **C5** ContactsView 撞车 `.ct-*` 前缀（与 CountdownsView 共用），paper 规则静默命中两页 → 迁移 `contact-` 前缀或确认共享。

## 建议执行顺序

**A 批 + B1/B2/B5 一批做**（都是低风险高收益，A1/A2 各一处 CSS 全局生效）；B3/B4/B6 次之；C 批看心情。
