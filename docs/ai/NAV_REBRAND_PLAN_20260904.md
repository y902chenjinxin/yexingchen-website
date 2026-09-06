# 内容板块去「岛」重构 + 工具独立页 + 视频解析增强（2026-09-04）

> 状态：✅ 已完成（2026-09-04 部署现网，生产浏览器实测 9 项全 PASS）。背景：UI 大改后用户反馈 5 点——①工具链接要独立页（点「使用」跳转）；②视频解析要预览播放；③补「下载音频」；④各模块增删改查要有入口和字段；⑤新版本去掉「岛」字。以下为已对齐并落地的方案。

## 一、总体原则
- 五模块（音乐/小说/视频/工具/日志）全去「岛」，**显示文案 + 路由同步改**。
- 每模块将「管理表格页」与「沉浸浏览内页」**合并成一个内容页**：卡片墙浏览 + 顶部「管理」按钮同页切换成表格（增删改查）。
- 工具体系升级为「每个工具一个独立页」：外部链接 iframe（先加载按钮）；去水印作为**内置工具置顶第一条**。
- 「音频必须可下载」：平台无音频源时，后端**服务端抽音轨（ffmpeg）**兜底。
- 旧路由 `/island/*` 一律重定向到新路由，老链接不失效。
- 工作台玉简卡片入口保留，文案已无「岛」。

## 二、路由重构（新表）
| 新路由 | 组件 | 说明 | 旧路由(重定向→) |
|---|---|---|---|
| `/music` | MusicView.vue | 音乐·卡片墙+管理一体化 | `/island/music`、`/island/music/inner` |
| `/novel` | NovelView.vue | 小说·同上 | `/island/novel`、`/island/novel/inner` |
| `/video` | VideoView.vue | 视频·同上 | `/island/video`、`/island/video/inner` |
| `/tool` | ToolView.vue | 工具·卡片列表(含置顶去水印)+管理表格 | `/island/tool`、`/island/tool/inner` |
| `/tool/:id` | ToolDetailView.vue | 外部工具独立页（iframe） | 新增 |
| `/tool/watermark` | WatermarkView.vue | 内置去水印独立页（解析UI迁入） | `/island/tool/inner` 合并 |
| `/log` | LogView.vue | 日志·仅改名，只读流水(不做CRUD) | `/island/log`、`/island/log/inner` |

- `views/` 下原 `MusicIsland.vue` 等重命名为 `MusicView.vue` 等；`views/islands/*IslandInner.vue`（音乐/小说/视频）被 `*View.vue` 吸收删除；`ToolIslandInner.vue` 迁移为 `WatermarkView.vue`。
- `island` meta 标签改/去；`IslandInnerBase.vue` 改名 `ContentViewBase.vue`（若保留复用）。
- 兜底路由 `/island/:path*` 统一 302 → 对应新路由；未匹配仍回 `/workbench`。

## 三、内容页（去岛 + 合并）
每个模块一张合并页，两种模式同页切换：
1. **浏览模式（默认）**：沿用现 `*IslandInner` 的卡片墙玉化视觉；顶部栏标题去「岛」（如表头 `🎵 音乐`）。
2. **管理模式**：顶部「管理」按钮点击切换；表格展示**全部字段**——
   - 音乐：标题 / 作者 / 分类 / 标签 / 大小 / 上传时间 / 上传者 / 是否系统默认(只读)
   - 小说：标题 / 作者 / 分类 / 标签 / 大小 / 上传时间 / 上传者
   - 视频：标题 / 分类 / 标签 / 大小 / 上传时间 / 上传者 / 链接(COS)
   - 工具：名称 / 图标 / 描述 / 链接 / 上传时间 / 上传者
   - 增删改查齐全；音乐系统默认曲只读保护。
3. 原「沉浸浏览」入口按钮移除（浏览即卡片墙）。

## 四、工具独立页
- `ToolView` 卡片列表 = 内置置顶「视频去水印」 + 数据库外部工具（按时间），每卡带 **「使用」** 按钮。
- 外部工具点「使用」→ `/tool/:id` 独立页：先显示工具图标/名称/描述 + **「加载工具」** 按钮，点击才内嵌 iframe；若工具拒绝 iframe（X-Frame-Options），**一律新标签打开**。
- 内置「视频去水印」点「使用」→ `/tool/watermark` 独立页，内置解析 `WatermarkView`。
- 工具管理表格：「管理」按钮 → 外部工具增删改查（名称/图标/描述/链接/上传时间/上传者）。

## 五、视频解析增强（WatermarkView）
- **预览播放**：解析结果的 `<video controls playsinline>` 内联实时播放（沿用现有实现，确认可播）。
- **下载音频兜底**（服务端抽音轨）：
  1. 平台返回 `music_url` → 直接提供可下载链接。
  2. 无 `music_url` → 前端调 **`POST /api/video_parse/audio`**（传分享 url）→ 后端下载无水印视频临时文件 → `ffmpeg -i video -vn -acodec libmp3lame out.mp3` → `FileResponse` 返回 mp3。
  3. 交互：点「下载音频」→ 按钮 loading「抽取中…」（几秒）→ 生成可下载 mp3 / 失败提示；临时文件用后即清。

## 六、后端改动
- `routers/video_parse.py`：复用串行 `_lock` 与按用户限流；新增 `POST /api/video_parse/audio` 子路由（`httpx` 下载 + `subprocess` ffmpeg 抽音轨 + `FileResponse` + 临时目录清理）。
- 服务器：需安装 `ffmpeg`（`apt-get install -y ffmpeg`）。
- 现有视频/音乐/工具/小说 CRUD 接口不变；仅前端字段展示补全走现有接口。

## 七、去岛文案落点
- 页面标题/表头/空态/桌宠相关提示中所有「岛」字移除（`grep 岛` 逐处清）。
- 工作台玉简卡片文案无岛（已验证）；其占位入口路由改为新路径 `/music` 等。
- 日志：仅改名去岛、改路由，不做增删改查。

## 八、风险与兼容
- 路由大改：靠 `/island/*` → 新路由重定向兜底，旧收藏/链接不失效；SW 升版（`xuanhuang-v14`）清除旧缓存。
- 抽音轨依赖服务器 ffmpeg 与 `parse-video-py` 能解析出可下载视频源；个别平台无水印视频下载受限时抽轨失败 → 明确提示。
- iframe 内嵌受第三方 CSP/X-Frame-Options 限制 → 已定「被拒一律新标签打开」。

## 九、验收
- 新路由直达：`/music /novel /video /tool /tool/:id /tool/watermark /log` 均正常，旧 `/island/*` 自动跳到新页。
- 每模块卡片墙 + 「管理」表格（增删改查/全字段/音乐默认曲只读）浏览器实测通过。
- 工具：外部工具「使用」→ 独立页先「加载工具」→ iframe 内嵌；被拒新标签；去水印棋盘格第一条点击进 `/tool/watermark`。
- 解析：预览可播；「下载音频」有源直下、无源后台抽轨出 mp3。
- 全站界面无「岛」字残留。

## 十、顺序
1. 路由重构 + 文件重命名 + 旧路由重定向（SW v14）。
2. 合并内容页（卡片墙+管理切换）+ 全字段表格。
3. 工具独立页 + 去水印独立页迁入 + 预览播放。
4. 后端抽音轨接口 + 服务器装 ffmpeg。
5. 去岛文案清零 → 本地构建 → 浏览器实测 → 部署现网 → 收尾（文档/清理/git 推送）。