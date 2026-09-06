# 背景音乐 + 视频去水印 + 三库 CRUD 方案（20260903）

> 定位：一次大型功能迭代。经多轮用户追问收敛，需求已确认。本方案先做**背景音乐**，再做**视频去水印**。
> 原则：跨会话可执行接续文档；实施完成后回填结论与验收。

---

## 一、背景音乐功能

### 目标
1. 支持本地音乐上传（已有部分基础），音乐可编辑基础信息。
2. 背景音乐播放与音乐库关联：从音乐库选曲设为背景、可切换、跨会话记住。
3. 全站统一底部播放条，统一点播与背景 BGM 的播放/暂停/进度/音量控制。
4. 背景 BGM 与音乐岛点播互斥：点播时暂停背景，离开恢复。

### 现状（调研结论）
- 音乐上传 `MusicIsland.vue` → `POST /api/music` 后端完备；字段 title/original_filename/category/tags/file_size 等。
- **Music 模型缺 `artist` 字段**，需加列（迁移）以支持"编辑作者"。
- 背景音乐当前是"管理员上传 → 存 GlobalSetting 'bg_music' → 流式播放默认 '/music/default-bg.mp3'"（`settings.py`），与音乐库无关联、无用户选择记忆。
- 前端背景播放：`GlobalTopBar.initAudio()` 新建 `new Audio(settingsStore.bgMusicUrl)` loop。
- **bug**：`MusicIslandInner` 读 `item.name/item.artist` ≠ 后端 `title/original_filename`；`handlePlay` 仅 console.log 无真实播放。

### 设计

**数据层（后端）**
- `Music` 增列 `artist VARCHAR(255) default ''`。
- 新表/字段：`GlobalSetting` 增 `key='bgm_user_setting'` 存储 `{"bgm_music_id": <int|null>, "refer_default": true}` → 即用户选定的背景曲是"音乐库某曲(id)" 还是 "系统默认古筝(default)"。**引用曲目 ID，不复制文件**。
- 新增 `GET /api/settings/bgm_choice`（读当前用户后台设定，默认 default）、`PUT /api/settings/bgm_choice`（写）。（沿用 get_current_user 而非 require_super_admin，登录即可改）
- `POST /api/music` 上传限制：`.mp3/.wav/.flac`，单文件 ≤ 50MB（需在 settings 校验已有 `MAX_MUSIC_SIZE`，若不同则调整）。
- 默认古筝曲：作为音乐库列表**首条**返回（标记 `is_system=1`），只读保护不可删改；由后端在 `GET /api/music` 时预插，或前端在 settingsStore 注入。→ 选用后端注入：列表首条系统曲（id 用特殊值 `'default'`，`title='古筝·玄黄'`, `artist='系统'`, url=`/api/settings/bg_music/stream/default`）。

**播放层（前端，核心）**
- 新增全局底部组件 `NowPlayingBar.vue`：封面/标题/暂停播放/进度条(可拖)/上一曲下一曲/音量。**播放时才出现，否则隐藏**；固定底部，避开右下角桌宠（右侧留出桌宠区，z-index 低于桌宠 10001）。
- 新增 store `stores/player.js`：单一 `<audio>` 元素；管理当前队列来源(`type:'bgm'|'playlist'`)、音源 url、isPlaying、volume、progress。
- 规则：
  - 背景BGM模式：播放当前选定（默认古筝或音乐库某首 url），loop。
  - 点播模式：在 MusicIsland 点某首 → `player.playMusic(item)`，切到 playlist 播放该曲；同时**暂停触发背景BGM**。
  - 离开点播（离开播放条交互/回后台）→ 若 original 是 bgm，恢复背景 BGM 播。
- 音量：背景与点播音量都写 `localStorage`（playVolume/bgmVolume），跨会话记住；替换掉现有无实际含义的 `sound_volume` 误用。
- 顶栏音频下拉：新增"背景音乐"项，展开列出"系统默认古筝 + 我的/全站音乐库曲目"，点选即 `PUT bgm_choice` 并播放。
- 音乐岛内页：每曲目加"设为背景"按钮（`💠`），点击即设当前曲为背景并播。

**权限（已确认）**
- 三库(音乐/工具/视频)**全站公开可改**，登录即可编辑/删除。
- 系统默认古筝曲只读保护。

### 验收（浏览器实测，截图 _screens）
1. 上传 .mp3 后出现在音乐库；列表首条系统默认古筝（只读）。
2. 顶栏下拉设置背景为某上传曲 → 播放；刷新后仍记住该曲。
3. 音乐岛点播 → 背景暂停；返回 → 背景恢复。
4. 底部播放条出现/隐藏符合"播放时出现"；避开桌宠。
5. 编辑音乐作者/标题保存生效。

---

## 二、视频去水印工具

### 目标
工具岛内新增"视频去水印"：粘贴链接 → 解析无水印源 → 在线预览 + 下载视频/音频/封面到本地。

### 技术选型（已调研落地：parse-video-py）
- **parse-video-py**（https://github.com/wujunwei928/parse-video-py）：Python FastAPI 原生、依赖最少(fastapi/httpx/parsel)，覆盖抖音/快手/小红书/微博/西瓜/微视等 20 平台，返回 video_url/cover_url/music_url。
- 备选：`wwwzhouhui/video-parser`（全但依赖重，含 Gradio/Qwen）；`yt-dlp`（做通用层，抖音不稳定需签名）。

### 架构
- **独立解析服务**：把 parse-video-py 部署为一个独立 FastAPI 服务（服务器/本地单独端口，如 8070），负责调用其解析函数。
- 现有后端新增转发路由 `POST /api/video_parse`：接收 url → 串行调用解析服务 → 返回 `{title, author, video_url, music_url, cover_url}`。
- **单任务串行**：解析服务内加互斥锁，同一时间只处理一个；简化防滥用与压力。
- 前端工具岛内页嵌入去水印面板：粘贴链接 → 解析(loading) → 展示预览 `<video>` + 三个下载按钮（视频/音频/封面），`window.open(url)` 直接下载回浏览器。
- 失败友好提示"暂不支持该平台或链接已失效"，可重新粘贴重试；**不存历史**。
- 合规提示：面板角落加一句"请在权利允许范围内使用"。

### 验收
1. 粘贴有效抖音/快手链接 → 解析成功，视频预览可播，三下载按钮可点。
2. 无效链接 → 友好提示可重试。
3. 并发点解析 → 串行排队不崩溃。
4. 无历史残留、无越权。

---

## 三、三库 CRUD 完善 + 修 bug（贯穿两阶段）

- **修 bug**：
  - `ToolIsland.vue` 的 `toolStore.add` 不存在 → 改用 `useCrudStore` 的 `upload`。
  - 前端字段名与后端不匹配（`item.name`→`title`、`item.artist` 等）统一校正。
- 完善 `MusicIsland.vue` / `ToolIsland.vue` / `VideoIsland.vue` 管理页：列表/新增/编辑/删除（已有雏形补齐）。
- 岛屿内页卡片加 `...` 菜单（编辑/删除），操作就近完成；视频内页加在线播放。
- 编辑基础字段（音乐：标题/作者/分类/标签）。

---

## 四、部署与收尾
- 本地 build + 浏览器实测（真实账号）→ 一次部署现网（SW 升版 → scripts/deploy_front.py 上传 → 后端起新接口/迁移 → 生产浏览器实测）。
- SW 升 `xuanhuang-v12`（含本轮）。
- 更新 WORK_LOG.md / CURRENT_STATE.md；删除临时脚本；git commit + push。

## 五、涉及文件（草拟）
- 后端：`app/models/user.py`(Music.artist)、`app/routers/music.py`、`app/routers/settings.py`(bgm_choice/默认曲注入/video_parse转发)、`app/routers/tool.py`、`app/routers/video.py`、依赖 parse-video-py
- 前端：`components/NowPlayingBar.vue`(新)、`stores/player.js`(新)、`stores/settings.js`、`components/GlobalTopBar.vue`、`views/islands/MusicIslandInner.vue`、`views/MusicIsland.vue`、`views/ToolIsland.vue`、`views/islands/ToolIslandInner.vue`、`views/VideoIsland.vue`、`views/islands/VideoIslandInner.vue`

## 六、顺序
1. 阶段1 背景音乐（含 Music.artist 迁移、player store、NowPlayingBar、默认曲、顶栏/内页入口）。
2. 阶段2 去水印（部署 parse 服务、后端转发、工具岛面板、合规提示）。
3. 贯穿：三库 CRUD 完善 + 修 bug。

---

## 七、实施完成回填（2026-09-03）

> ✅ 已按本方案完成并部署上线（SW `xuanhuang-v13`），生产浏览器实测 **10 项全 PASS**。

- **背景音乐**：`Music` 增 `artist/is_default`（Alembic `d4e5f6a7b8c9` + 生产 `ALTER TABLE`）；`GET/PUT /api/settings/bgm_choice` 用户级；`player.js` 单一音频中枢（背景↔点播互斥、点播播毕自动恢复背景、音量 `localStorage`）；`NowPlayingBar` 全局底部播放条（播放才显、避桌宠）；系统默认古筝曲列表首条只读注入。
- **视频去水印**：独立 `parse-service`（parse-video-py，8070，串行锁）上线；后端 `POST /api/video_parse`（用户 3s 限流+串行）；工具岛内页去水印面板（预览/下载/合规提示）。
- **三库 CRUD**：音乐/工具/视频/小说管理页+内页新增/编辑/删除，内页 `⋯` 菜单、视频内联播放、系统默认曲只读；四岛管理页「沉浸浏览」+ 工具岛「去水印工具」入口。
- **部署**：`deploy_backend.py` / `deploy_frontend.py` / `deploy_parse.py`；验收截图见各步骤浏览器实测。
- 遗留：`parse-video-py` 各平台解析稳定性待长期观察。