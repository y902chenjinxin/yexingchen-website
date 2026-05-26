# 个人网站 PRD v1.0

## 1. 项目概述

**项目名称**：叶兴辰的个人网站
**域名**：yexingchen.cn
**服务器**：203.195.208.25
**核心定位**：个人云存储与展示平台，以万妖之祖·神农图为灵感，采用云上浮空岛屿视觉风格，提供音乐、小说、视频等个人收藏的云端管理能力。

---

## 2. 功能总览

### 2.1 账号与权限

| 功能 | 描述 |
|------|------|
| 用户注册 | 邮箱+密码，提交申请 → 管理员审批 → 分配角色 |
| 邮箱验证码 | 6位数字，3分钟有效，10分钟内每账号最多3次 |
| 账号审批 | 管理员审批注册申请，分配角色（管理员/普通用户） |
| 用户管理 | 管理员增删改查用户，分配角色与可访问岛屿 |
| 登录登出 | JWT 凭证，7天自动续期 |

**角色说明**：
- **超级管理员**：审批用户、管理所有用户、查看操作日志
- **普通用户**：访问已分配岛屿、管理自己内容

### 2.2 五岛屿功能

| 岛屿 | 存储内容 | 上传要求 | 功能 |
|------|---------|---------|------|
| 音乐岛 | mp3 音频 | ≤50MB | 播放列表/搜索/下载 |
| 小说岛 | epub 电子书 | ≤100MB | 书名/封面/作者/下载 |
| 视频岛 | mp4 + 封面图 | ≤500MB | 封面/腾讯COS链接/下载 |
| 日志岛 | 操作记录 | — | 查看自己操作日志（管理员可查看所有） |
| 工具岛 | 外链集合 | — | 标题+链接，可新增/编辑/删除 |

### 2.3 全局功能

- **全局搜索**：支持按标题、标签、分类搜索
- **背景音乐**：全局 BGM，支持替换
- **响应式设计**：支持桌面端、移动端
- **CDN**：腾讯 COS 内置 CDN

---

## 3. 信息架构

```
登录页（光效+门户动画）
    ↓
申请注册 → 待审批状态
    ↓
主页面（云雾缭绕 + 5个浮空岛屿）
    ├── 音乐岛 → 音乐列表（搜索/下载）
    ├── 小说岛 → 小说列表（搜索/下载）
    ├── 视频岛 → 视频列表（搜索/下载）
    ├── 日志岛 → 操作日志列表
    └── 工具岛 → 外链卡片列表
    ↓
底部悬浮栏：岛屿切换弹层（退出按钮在最底部）
```

---

## 4. 数据库设计

### 4.1 用户表 `users`
| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | |
| email | VARCHAR(255) UNIQUE | |
| password_hash | VARCHAR(255) | bcrypt |
| role | VARCHAR(20) | super_admin / normal |
| status | VARCHAR(20) | pending / approved / rejected |
| allowed_islands | VARCHAR(255) | 逗号分隔，如 `music,novel,video,diary,tools` |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### 4.2 验证码表 `verification_codes`
| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | |
| email | VARCHAR(255) | |
| code | VARCHAR(10) | |
| attempts | INT | 10分钟内尝试次数 |
| expires_at | TIMESTAMP | 3分钟后过期 |
| created_at | TIMESTAMP | |

### 4.3 音乐表 `music`
| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | |
| title | VARCHAR(255) | |
| file_path | VARCHAR(500) | 存储路径 |
| uploader_id | INT FK | |
| category | VARCHAR(100) | 分类 |
| tags | VARCHAR(500) | 标签，逗号分隔 |
| created_at | TIMESTAMP | |

### 4.4 小说表 `novels`
| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | |
| title | VARCHAR(255) | |
| author | VARCHAR(255) | |
| cover_path | VARCHAR(500) | 封面图路径 |
| file_path | VARCHAR(500) | 存储路径 |
| uploader_id | INT FK | |
| category | VARCHAR(100) | |
| tags | VARCHAR(500) | |
| created_at | TIMESTAMP | |

### 4.5 视频表 `videos`
| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | |
| title | VARCHAR(255) | |
| cover_path | VARCHAR(500) | 封面图路径 |
| cos_url | VARCHAR(500) | 腾讯COS链接 |
| uploader_id | INT FK | |
| category | VARCHAR(100) | |
| tags | VARCHAR(500) | |
| created_at | TIMESTAMP | |

### 4.6 日志表 `operation_logs`
| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | |
| user_id | INT FK | |
| action | VARCHAR(100) | 上传/删除/修改等 |
| target_type | VARCHAR(50) | music/novel/video/tool |
| target_id | INT | |
| detail | TEXT | |
| created_at | TIMESTAMP | |

### 4.7 工具表 `tools`
| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | |
| title | VARCHAR(255) | |
| url | VARCHAR(500) | |
| uploader_id | INT FK | |
| created_at | TIMESTAMP | |

### 4.8 全局设置表 `global_settings`
| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | |
| key | VARCHAR(100) UNIQUE | bg_music 等 |
| value | TEXT | 路径或URL |
| updated_at | TIMESTAMP | |

---

## 5. API 接口设计

### 5.1 认证模块
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 注册（发验证码邮件） |
| POST | /api/auth/verify | 验证邮箱验证码 |
| POST | /api/auth/login | 登录，返回 JWT |
| POST | /api/auth/logout | 登出 |
| GET | /api/auth/me | 获取当前用户信息 |

### 5.2 用户管理（管理员）
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/admin/users | 用户列表 |
| POST | /api/admin/users/:id/approve | 审批通过 |
| PUT | /api/admin/users/:id | 修改用户角色/岛屿权限 |
| DELETE | /api/admin/users/:id | 删除用户 |

### 5.3 音乐岛
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/music | 列表（支持搜索/分类/标签） |
| POST | /api/music | 上传音乐 |
| PUT | /api/music/:id | 编辑 |
| DELETE | /api/music/:id | 删除 |

### 5.4 小说岛 / 视频岛 / 工具岛
同上格式，`/api/novels`、`/api/videos`、`/api/tools`

### 5.5 日志岛
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/logs | 操作日志（管理员可看全部，普通用户只能看自己） |

### 5.6 全局
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/search?q= | 全局搜索 |
| GET | /api/settings/bg_music | 获取背景音乐 |
| PUT | /api/settings/bg_music | 替换背景音乐 |

---

## 6. 视觉风格设计

### 6.1 登录页
- **进入动画**：一道金色流光从左向右闪过 → 云雾散开 → 古风木门双开 → 登录框淡入
- **配色**：深青墨 + 金色点缀，仙侠水墨风格
- **字体**：思源宋体 / Noto Serif SC

### 6.2 主页面
- **背景**：动态云海，有微风吹动效果
- **岛屿**：5座浮空岛屿悬于云上，轻微上下浮动（CSS动画）
- **岛屿风格**：
  - 音乐岛：琴/音律元素
  - 小说岛：竹简/书卷元素
  - 视频岛：光影/胶片元素
  - 日志岛：竹签/记录元素
  - 工具岛：齿轮/机关元素

### 6.3 各岛屿空间
- 进入岛屿后，云雾环绕效果消失，显示对应内容列表
- 各岛屿有独立的视觉主题色

---

## 7. 技术架构

```
前端：Vue 3 + Vite + Pinia + Vue Router
后端：Python FastAPI
数据库：SQLite（轻量级，单用户场景足够）
文件存储：腾讯 COS（音乐/小说/视频/封面）
邮件发送：QQ邮箱 SMTP
部署：Nginx 反向代理 + Gunicorn/uvicorn
域名：yexingchen.cn（已配置）
```

---

## 8. 部署方案

- **服务器**：203.195.208.25:8000（后端）
- **前端静态**：Nginx 托管，绑定域名 yexingchen.cn
- **API 反向代理**：/api → localhost:8000
- **文件上传**：直传腾讯 COS，或后端代理上传

---

## 9. 边界值补充

| 场景 | 处理方式 |
|------|---------|
| 验证码输错3次锁定 | 返回"尝试次数过多，请10分钟后再试" |
| 验证码过期 | 提示"验证码已过期，请重新获取" |
| 同一邮箱重复注册 | 提示"该邮箱已注册" |
| 上传文件超限 | 提示"文件大小超出限制" |
| 上传格式不符 | 提示"不支持的文件格式" |
| 用户未审批登录 | 提示"账号待审批，请联系管理员" |
| 搜索无结果 | 显示空状态"未找到相关内容" |
| Session 过期 | 自动跳转登录页 |

---

## 10. 待确认事项（Pending）

> 以下事项需用户确认后才能推进：

1. **数据库**：SQLite 是否接受？（轻量，单人使用足够）
2. **上传方式**：直传腾讯 COS（快）还是后端代理上传（统一）？
3. **登录页配色**：金色为主？还是青色为主？