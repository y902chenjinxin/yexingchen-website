# 工具库可接入 GitHub 纯前端工具推荐（方案）

> 日期：2026-09-04
> 状态：⏳ **调研结论已完成，待用户选型后实施**
> 触发：User「下面我想看看 github 上有没有什么推荐的」——为工具库挑选可纯前端内嵌的开源工具。
> 关联：`WORK_LOG.md`（本方案为检索文档，接入实施后的结论并入 WORK_LOG）。

## 一、选型约束

- **纯前端可内嵌**：要么 `iframe` 内嵌现成静态页，要么 `npm` 依赖 + CDN 按需加载在主站内实现；不需自建后端 / API 密钥 / 登录。
- **许可证友好**：优先 MIT / Apache-2.0 / BSD；**避开 AGPL-3.0**（传染性）、需付费、需自架服务器才能用的。
- **通用、高常用度、易实现** 优先，与现有工具互补（现有：视频去水印 / PDF 多功能 / 像素压缩 / 练字 / 中英文翻译）。

## 二、候选清单（已核实）

### 第一梯队（低工作量 · 高常用度，建议优先）

| 工具 | 仓库 | Star | 许可证 | 接入 | 工作量 | 价值 |
|---|---|---|---|---|---|---|
| **二维码 生成+解析** | [paulmillr/qr](https://github.com/paulmillr/qr) | 368 | Apache-2.0 / MIT | npm / CDN | 低 | 零依赖，可生成且可扫码解析；URL/文本/链接一键转码 |
| **图片 OCR 文字识别** | [Tesseract.js](https://github.com/naptha/tesseract.js) | 38.7k | Apache-2.0 | npm / CDN | 中 | 最成熟纯前端 OCR，图片转文字（中文语言包按需加载，体积中） |
| **JSON 格式化/校验** | 建议**自建**（原生 JS / Prettier） | — | — | 站内组件 | 低 | 调研到的 json-formatter 仅 0★ 不稳；JSON 工具用原生 `JSON.stringify` + 校验即可，零依赖零风险 |

### 第二梯队（中工作量 / 受众略窄）

| 工具 | 仓库 | Star | 说明 |
|---|---|---|---|
| 图片转 SVG 矢量化 | [99buntai/Front-End-SVGConverter](https://github.com/99buntai/Front-End-SVGConverter) | 1 | Potrace 算法，适合设计向，但 Star 太低 |
| 写作/字数分析 | [MianScribe](https://github.com/Mianhassam96/MianScribe) | 31 | 字数/句段/阅读时间统计，受众窄 |

### 明确不推荐

| 项目 | 原因 |
|---|---|
| xxnuo/qrcode、Sid-1996/pictool | 许可不明（`null` / `NOASSERTION`） |
| xsukax-Favicon-Generator | GPL-3.0 传染风险 |
| Pic Smaller | 已与现有「像素压缩」工具重复 |
| editor.md | 笔记模块已有 Markdown 编辑能力 |

## 三、明确推荐（Top 3）

1. **二维码生成+解析** — `@paulmillr/qr`，接入成本最低、通用性最强。
2. **图片 OCR 转文字** — Tesseract.js，价值最高，工作量中等。
3. **JSON 格式化/校验** — 原生 JS 自建，零依赖零风险，最快上线。

## 四、实施（待选型）

> 待 User 从上述推荐中选定 1~2 个后按既有工具流程实施：
> 1. 建独立工具页路由（`/tool/:id`），登记 `tools` 表（`kind=builtin` 置顶、禁删）。
> 2. 纯前端实现（禁止后端请求）；二维码用 `@paulmillr/qr`（generator + decoder），OCR 用 Tesseract.js 按需加载语言包。
> 3. 构建 → 部署 → SW 升版本 → 浏览器清 SW 实测 PASS → 结论并入 `WORK_LOG.md` 时间线。