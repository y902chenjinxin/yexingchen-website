# 抽象与复用清单（v2.46.158 起）

> 目的：夜星要求「把重复的方法/组件抽象出来，以后改一处就够」。
> 本文是**全盘审计结果 + 分批落地计划**，避免一次动 6000 行导致线上不可控。

## 一、审计数据（实测，非估算）

### 前端

| 重复模式 | 数量 | 现状 |
|---|---|---|
| 搜索输入框（`placeholder="搜…"`） | **15** | 宽度/高度/清空/按钮各写一套；曾有 6 处只有回车没按钮 |
| 表格操作列（`label="操作"`） | **6** | 每页各写一份 `row-ops` + 一串 IconButton |
| 使用 `el-table` 的页面 | 7 | — |
| `el-pagination` 出现 | 14 | 分页参数/布局/事件各写一遍 |
| 手写空态 class | 70 | `EmptyState` 组件已存在但只覆盖 25 处 |
| `el-date-picker` | 8 | 格式/宽度/是否 clearable 不一致 |
| `toFixed` | **87** | 金额/百分比/体积算在一起，口径不统一 |
| 日期切片 `slice(0,10)` / `replace('T',' ')` | 17 | 与 `Date.UTC` 铁律混用，有时区风险 |
| 自定义 `function fmtXxx()` | **37** | 同一件事十几种实现 |
| 硬编码 `#rrggbb` | **2978** | 换肤时漏改的主要来源 |
| 硬编码 `rgba()` | **3058** | 同上 |

### 后端

| 重复模式 | 数量 | 现状 |
|---|---|---|
| `household_id == …` 过滤 | **130** | 每个查询手写一遍，漏写就串户 |
| `deleted_at.is_(None)` 软删过滤 | **104** | 同上 |
| `page/size` 分页声明 | 6 | 上限/默认值不一致 |
| `return ok(...)` 响应包装 | 135 | 已统一，无需动 |

## 二、本轮已落地的抽象（v2.46.158）

| 产物 | 路径 | 解决什么 |
|---|---|---|
| `SearchField` | `components/common/SearchField.vue` | 搜索框 + 查询按钮一体，Enter/按钮/清除三路统一；手机自动只留图标 |
| `OpsCell` | `components/common/OpsCell.vue` | 表格行内动作：图标化、`danger`、`disabled(row)`、`show(row)`、自定义插槽 |
| `PageToolbar` | `components/common/PageToolbar.vue` | 工具栏布局：左筛选 / 右主操作，间距与换行一处定义，主操作永远贴右 |
| `format.js` | `utils/format.js` | `fmtDate / fmtDateTime / fmtTime / fmtMd / fmtMoney / fmtYuan / fmtSize / fmtRelative / fmtPercent`，空值统一返回 `''` |

> 设计取舍：`OpsCell` **只封装单元格内容**，不封装 `el-table-column`。
> 列宽、`fixed` 各页不同，包进去反而每次都要传一堆 props；保持「列由页面声明、内容由组件渲染」更好用。

### 试点页面（已上线验证）

- **工具管理**：操作列换 `OpsCell` → 实测 15 行 / 45 个图标按钮 / `title` 正确。
- **遗失物**：工具栏换 `PageToolbar` + `SearchField` → 实测搜索「手环」命中 1 条，无报错。

## 三、分批计划

### P1（下一批，低风险）
1. `SearchField` 铺开剩余 13 处（机械替换，逐页验搜索行为）。
2. `OpsCell` 铺开剩余 5 处（音乐/小说/视频/用户/菜单）。
3. `PageToolbar` 铺开剩余 5 处工具栏（`.va-toolbar` / `.wd-toolbar` / `.tk-toolbar` …）。
4. `format.js` 替换 37 个自定义 `fmtXxx`（**只替换函数体，不动调用点**，回归面最小）。

### P2（中风险，需逐页回归）
5. `usePagedList` composable：收敛 14 处 `el-pagination`（页码/每页数/总数/加载态）。
6. `EmptyState` 铺开 70 处手写空态。

### P3（高风险，单独立项）
7. **颜色 token 化**：6000+ 处硬编码色 → 分批（按模块），每批一次全站截图比对。
   不建议一次全改：视觉回归无法用单测保证。
8. **后端查询收口**：130 处 `household_id` + 104 处软删 → 统一 `scoped_query()`。
   收益是「不会再漏写导致串户」，但涉及所有读写接口，需要全接口回归。

## 四、新增代码的约定（从本版起生效）

- 搜索框：一律 `SearchField`，不要再手写 `<input>` + 查询按钮。
- 表格行内动作：一律 `OpsCell`，`danger` 用 `danger: true`，不要手写 `variant="danger"`。
- 工具栏：一律 `PageToolbar`，主操作放 `#actions`。
- 日期/金额/体积：一律 `utils/format.js`，**禁止再新建 `fmtXxx`**。
- 下拉：一律 `FilterSelect`（v2.46.148 起）。
- 图片：一律 `utils/img.js` 的 `thumb()`（v2.46.145 起）。

## 五、验收方式

- 每批改完：`eslint` 0 error → `vite build` → 上线 → 抽查 2–3 个页面用浏览器读实际 DOM/行为（不只看截图）。
- 涉及样式统一时，**必须记录改前/改后的量化值**（宽度、行高、按钮数、命中条数），避免「看着差不多」。
