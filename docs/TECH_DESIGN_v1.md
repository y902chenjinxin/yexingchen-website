# 个人网站 技术详细设计 v1.0

> 基于 PRD v1.0 + UI_DESIGN_v1.0，本文档为技术落地设计，待评审确认后进入开发。

---

## 1. 技术栈总览

| 层级 | 技术选型 |
|------|---------|
| 前端 | Vue 3 + Vite + Pinia + Vue Router |
| 后端 | Python FastAPI |
| 数据库 | SQLite + SQLAlchemy ORM |
| 文件存储 | 腾讯 COS（后端代理上传） |
| 邮件 | QQ邮箱 SMTP (Python smtplib) |
| 认证 | JWT (python-jose) |
| 部署 | Nginx + Uvicorn |

---

## 2. 项目目录结构

```
yexingchen/
├── backend/                      # 后端项目
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置（数据库/腾讯COS/邮箱）
│   │   ├── database.py          # 数据库连接
│   │   ├── models/              # SQLAlchemy 模型
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── music.py
│   │   │   ├── novel.py
│   │   │   ├── video.py
│   │   │   ├── tool.py
│   │   │   ├── operation_log.py
│   │   │   └── global_setting.py
│   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   ├── music.py
│   │   │   ├── novel.py
│   │   │   ├── video.py
│   │   │   ├── tool.py
│   │   │   └── common.py
│   │   ├── routers/             # 路由
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── admin.py
│   │   │   ├── music.py
│   │   │   ├── novel.py
│   │   │   ├── video.py
│   │   │   ├── tool.py
│   │   │   ├── log.py
│   │   │   ├── search.py
│   │   │   └── settings.py
│   │   ├── services/           # 业务逻辑
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── email_service.py
│   │   │   ├── cos_service.py
│   │   │   └── log_service.py
│   │   └── utils/               # 工具函数
│   │       ├── __init__.py
│   │       ├── security.py      # JWT/密码工具
│   │       └── file_utils.py   # 文件处理
│   ├── requirements.txt
│   └── run.py                   # 启动脚本
│
├── frontend/                     # 前端项目
│   ├── public/
│   │   ├── favicon.ico
│   │   └── music/               # 默认背景音乐
│   ├── src/
│   │   ├── api/                 # API 封装
│   │   │   ├── index.js
│   │   │   ├── auth.js
│   │   │   ├── music.js
│   │   │   ├── novel.js
│   │   │   ├── video.js
│   │   │   ├── tool.js
│   │   │   ├── log.js
│   │   │   ├── search.js
│   │   │   └── settings.js
│   │   ├── assets/              # 静态资源
│   │   │   ├── styles/
│   │   │   │   ├── main.css    # 全局样式
│   │   │   │   └── variables.css
│   │   │   └── images/          # SVG图标等
│   │   ├── components/          # 公共组件
│   │   │   ├── IslandCard.vue
│   │   │   ├── ContentCard.vue
│   │   │   ├── MusicPlayer.vue
│   │   │   ├── IslandSwitcher.vue
│   │   │   ├── SearchBar.vue
│   │   │   └── TopBar.vue
│   │   ├── composables/         # 组合式函数
│   │   │   ├── useAuth.js
│   │   │   ├── useMusicPlayer.js
│   │   │   └── useIsland.js
│   │   ├── router/
│   │   │   └── index.js
│   │   ├── stores/              # Pinia Store
│   │   │   ├── auth.js
│   │   │   ├── music.js
│   │   │   ├── novel.js
│   │   │   ├── video.js
│   │   │   ├── tool.js
│   │   │   └── settings.js
│   │   ├── views/               # 页面
│   │   │   ├── LoginView.vue
│   │   │   ├── HomeView.vue
│   │   │   ├── MusicIsland.vue
│   │   │   ├── NovelIsland.vue
│   │   │   ├── VideoIsland.vue
│   │   │   ├── LogIsland.vue
│   │   │   ├── ToolIsland.vue
│   │   │   └── AdminView.vue
│   │   ├── App.vue
│   │   └── main.js
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── .env                     # 前端环境变量
│
├── nginx/
│   └── yexingchen.cn.conf       # Nginx 配置
│
└── README.md
```

---

## 3. 数据库详细设计

### 3.1 ER 关系图

```
users (1) ──── (N) music
      │
      └─── (N) novels
      │
      └─── (N) videos
      │
      └─── (N) tools
      │
      └─── (N) operation_logs

global_settings (独立，无外键)
verification_codes (独立，无外键，按 email 关联)
```

### 3.2 字段详情

#### users
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(100) DEFAULT '',
    role VARCHAR(20) NOT NULL DEFAULT 'normal',      -- super_admin / normal
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending / approved / rejected
    allowed_islands VARCHAR(500) DEFAULT 'music,novel,video,diary,tools',
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### verification_codes
```sql
CREATE TABLE verification_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) NOT NULL,
    code VARCHAR(10) NOT NULL,
    purpose VARCHAR(20) NOT NULL DEFAULT 'register',  -- register / reset_password
    attempts INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### music
```sql
CREATE TABLE music (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,        -- 服务器存储路径
    original_filename VARCHAR(255),
    duration INTEGER DEFAULT 0,             -- 时长（秒）
    category VARCHAR(100) DEFAULT '',
    tags VARCHAR(500) DEFAULT '',
    uploader_id INTEGER NOT NULL,
    file_size INTEGER DEFAULT 0,             -- 字节
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (uploader_id) REFERENCES users(id)
);
```

#### novels
```sql
CREATE TABLE novels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) DEFAULT '',
    cover_path VARCHAR(500) DEFAULT '',      -- 封面图路径
    file_path VARCHAR(500) NOT NULL,
    original_filename VARCHAR(255),
    category VARCHAR(100) DEFAULT '',
    tags VARCHAR(500) DEFAULT '',
    uploader_id INTEGER NOT NULL,
    file_size INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (uploader_id) REFERENCES users(id)
);
```

#### videos
```sql
CREATE TABLE videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    cover_path VARCHAR(500) DEFAULT '',      -- 封面图路径
    cos_url VARCHAR(500) NOT NULL,           -- 腾讯COS链接
    original_filename VARCHAR(255),
    category VARCHAR(100) DEFAULT '',
    tags VARCHAR(500) DEFAULT '',
    uploader_id INTEGER NOT NULL,
    file_size INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (uploader_id) REFERENCES users(id)
);
```

#### tools
```sql
CREATE TABLE tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    url VARCHAR(500) NOT NULL,
    description VARCHAR(500) DEFAULT '',
    icon VARCHAR(255) DEFAULT '',           -- 图标名称/路径
    uploader_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (uploader_id) REFERENCES users(id)
);
```

#### operation_logs
```sql
CREATE TABLE operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action VARCHAR(100) NOT NULL,           -- upload / delete / update / login / logout / approve / reject
    target_type VARCHAR(50),                -- music / novel / video / tool / user / NULL
    target_id INTEGER,
    detail TEXT DEFAULT '',
    ip_address VARCHAR(50) DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### global_settings
```sql
CREATE TABLE global_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT DEFAULT '',
    description VARCHAR(255) DEFAULT '',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 初始数据
INSERT INTO global_settings (key, value, description) VALUES
('bg_music', '/music/default-bg.mp3', '全局背景音乐路径'),
('site_title', '叶兴辰的个人网站', '网站标题'),
('site_subtitle', '神农遗风，云上洞天', '网站副标题');
```

---

## 4. API 接口详细设计

### 4.1 认证模块 `/api/auth`

#### POST /api/auth/register
**功能**：发送注册验证码邮件
```json
// Request
{
  "email": "1678069299@qq.com"
}

// Response 200
{
  "code": 0,
  "msg": "验证码已发送到邮箱",
  "data": null
}

// Response 400 (邮箱已注册)
{
  "code": 400,
  "msg": "该邮箱已注册",
  "data": null
}
```

#### POST /api/auth/verify
**功能**：验证验证码并完成注册
```json
// Request
{
  "email": "1678069299@qq.com",
  "code": "123456",
  "password": "xxxxxx"
}

// Response 200
{
  "code": 0,
  "msg": "注册申请已提交，请等待管理员审批",
  "data": null
}

// Response 400 (验证码错误/过期/次数超限)
{
  "code": 400,
  "msg": "验证码已过期，请重新获取",
  "data": null
}
```

#### POST /api/auth/login
**功能**：登录
```json
// Request
{
  "email": "1678069299@qq.com",
  "password": "xxxxxx"
}

// Response 200
{
  "code": 0,
  "msg": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "email": "1678069299@qq.com",
      "role": "super_admin",
      "status": "approved",
      "nickname": "",
      "allowed_islands": "music,novel,video,diary,tools"
    }
  }
}

// Response 401 (账号待审批)
{
  "code": 401,
  "msg": "账号待审批，请联系管理员",
  "data": null
}
```

#### POST /api/auth/logout
**功能**：登出（前端删除token即可，后端可记录日志）

#### GET /api/auth/me
**功能**：获取当前用户信息

---

### 4.2 用户管理 `/api/admin/users`

> 需要 `role: super_admin` 权限

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /api/admin/users | 用户列表 |
| POST | /api/admin/users/:id/approve | 审批通过 |
| POST | /api/admin/users/:id/reject | 审批拒绝 |
| PUT | /api/admin/users/:id | 修改用户信息 |
| DELETE | /api/admin/users/:id | 删除用户 |

#### PUT /api/admin/users/:id
```json
// Request
{
  "role": "normal",
  "status": "approved",
  "allowed_islands": "music,novel,video"
}

// Response 200
{
  "code": 0,
  "msg": "更新成功",
  "data": null
}
```

---

### 4.3 音乐岛 `/api/music`

#### GET /api/music
```json
// Query: ?q=关键词&category=分类&tags=标签1,标签2&page=1&size=20

// Response 200
{
  "code": 0,
  "msg": "",
  "data": {
    "list": [
      {
        "id": 1,
        "title": "菊花台",
        "file_path": "/uploads/music/xxx.mp3",
        "duration": 245,
        "category": "古风",
        "tags": ["古风", "周杰伦"],
        "uploader_id": 1,
        "file_size": 5242880,
        "created_at": "2026-05-26T10:00:00Z"
      }
    ],
    "total": 100,
    "page": 1,
    "size": 20
  }
}
```

#### POST /api/music
**功能**：上传音乐（后端代理）
- Content-Type: `multipart/form-data`
- 字段：`file`（mp3）、`title`、`category`、`tags`

#### PUT /api/music/:id
可修改：`title`、`category`、`tags`

#### DELETE /api/music/:id
物理删除文件 + 数据库记录

---

### 4.4 小说岛 `/api/novels`

#### GET /api/novels
同音乐岛格式

#### POST /api/novels
- Content-Type: `multipart/form-data`
- 字段：`file`（epub）、`title`、`author`、`category`、`tags`、`cover`（封面图，可选）

#### PUT /api/novels/:id
可修改：`title`、`author`、`category`、`tags`

#### DELETE /api/novels/:id

---

### 4.5 视频岛 `/api/videos`

#### GET /api/videos
返回列表含 `cos_url`（腾讯COS链接）

#### POST /api/videos
- Content-Type: `multipart/form-data`
- 字段：`file`（mp4）、`title`、`category`、`tags`、`cover`（封面图）、`cos_url`（可选，若填则用提供的COS链接）

**上传流程**：
1. 前端上传视频到后端
2. 后端上传到腾讯COS
3. 返回COS链接存入数据库

#### PUT /api/videos/:id
#### DELETE /api/videos/:id

---

### 4.6 工具岛 `/api/tools`

#### GET /api/tools
```json
{
  "list": [
    {
      "id": 1,
      "title": "ChatGPT",
      "url": "https://chat.openai.com",
      "description": "AI对话助手",
      "uploader_id": 1,
      "created_at": "2026-05-26T10:00:00Z"
    }
  ]
}
```

#### POST /api/tools
```json
// Request
{
  "title": "ChatGPT",
  "url": "https://chat.openai.com",
  "description": "AI对话助手"
}
```

#### PUT /api/tools/:id
#### DELETE /api/tools/:id

---

### 4.7 日志岛 `/api/logs`

#### GET /api/logs
```json
// Query: ?user_id=xxx&target_type=music&page=1&size=50

// Response 200
{
  "code": 0,
  "data": {
    "list": [
      {
        "id": 1,
        "user_id": 1,
        "user_email": "1678069299@qq.com",
        "action": "upload",
        "target_type": "music",
        "target_id": 1,
        "detail": "上传音乐：菊花台",
        "ip_address": "x.x.x.x",
        "created_at": "2026-05-26T10:00:00Z"
      }
    ],
    "total": 500,
    "page": 1,
    "size": 50
  }
}
```

---

### 4.8 全局搜索 `/api/search`

#### GET /api/search
```json
// Query: ?q=关键词&page=1&size=20

// Response 200
{
  "code": 0,
  "data": {
    "music": [{ "id": 1, "title": "菊花台", "_type": "music" }],
    "novels": [{ "id": 2, "title": "凡人修仙传", "_type": "novel" }],
    "videos": [],
    "tools": [{ "id": 1, "title": "ChatGPT", "_type": "tool" }],
    "total": 3
  }
}
```

---

### 4.9 全局设置 `/api/settings`

#### GET /api/settings/bg_music
#### PUT /api/settings/bg_music
- `Content-Type: multipart/form-data`
- 字段：`file`（mp3）

---

## 5. 核心业务逻辑

### 5.1 注册流程

```
1. 用户输入邮箱 → POST /api/auth/register
2. 后端验证：
   - 查 users 表，邮箱已存在 → 返回"已注册"
   - 生成6位数字验证码
   - 写入 verification_codes 表（email, code, attempts=0, expires_at=now+3min）
   - 发送邮件到 1678069299@qq.com（主题：验证码）
3. 用户输入验证码+密码 → POST /api/auth/verify
4. 后端验证：
   - 查验证码记录，email匹配
   - 检查 attempts >= 3 → 返回"尝试次数过多"
   - 检查 expires_at < now → 返回"验证码已过期"
   - 检查 code 不匹配 → attempts+1，更新，返错
   - 全部通过 → 创建用户（status=pending）、删除验证码
5. 用户登录 → POST /api/auth/login → 返回"账号待审批"
```

### 5.2 登录流程

```
1. POST /api/auth/login
2. 后端验证密码
3. 检查 status：
   - pending → 返回"账号待审批"
   - rejected → 返回"账号已被拒绝"
   - approved → 继续
4. 检查 allowed_islands 中是否包含请求的岛屿
5. 生成 JWT（user_id, role, exp=7d）
6. 更新 last_login_at
7. 记录操作日志（login）
8. 返回 token
```

### 5.3 JWT 验证中间件

```python
# utils/security.py
from jose import JWTError, jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = "your-secret-key-here"  # 写入 config.py
ALGORITHM = "HS256"

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        role = payload.get("role")
        if user_id is None:
            raise HTTPException(status_code=401, detail="无效的token")
        return {"user_id": user_id, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="token已过期")
```

### 5.4 权限装饰器

```python
def require_super_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="需要超级管理员权限")
    return current_user
```

### 5.5 操作日志记录

```python
# services/log_service.py
def log_action(user_id: int, action: str, target_type: str = None,
               target_id: int = None, detail: str = "", ip: str = ""):
    db = SessionLocal()
    log = OperationLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        ip_address=ip
    )
    db.add(log)
    db.commit()
```

### 5.6 邮箱发送

```python
# services/email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_verification_code(to_email: str, code: str):
    msg = MIMEMultipart()
    msg['From'] = "叶兴辰的个人网站 <1678069299@qq.com>"
    msg['To'] = to_email
    msg['Subject'] = "【叶兴辰的个人网站】注册验证码"

    body = f"""
    您的注册验证码是：<b>{code}</b>

    验证码有效期为3分钟，请尽快完成验证。

    如果您没有进行注册操作，请忽略此邮件。
    """

    msg.attach(MIMEText(body, 'html', 'utf-8'))

    with smtplib.SMTP_SSL("smtp.qq.com", 465) as server:
        server.login("1678069299@qq.com", "your-auth-code")
        server.send_message(msg)
```

---

## 6. 前端关键设计

### 6.1 路由设计

```javascript
// router/index.js
const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: { requiresAuth: false }
  },
  {
    path: '/home',
    name: 'Home',
    component: HomeView,
    meta: { requiresAuth: true }
  },
  {
    path: '/island/music',
    name: 'MusicIsland',
    component: MusicIsland,
    meta: { requiresAuth: true, island: 'music' }
  },
  {
    path: '/island/novel',
    name: 'NovelIsland',
    component: NovelIsland,
    meta: { requiresAuth: true, island: 'novel' }
  },
  {
    path: '/island/video',
    name: 'VideoIsland',
    component: VideoIsland,
    meta: { requiresAuth: true, island: 'video' }
  },
  {
    path: '/island/log',
    name: 'LogIsland',
    component: LogIsland,
    meta: { requiresAuth: true, island: 'log' }
  },
  {
    path: '/island/tool',
    name: 'ToolIsland',
    component: ToolIsland,
    meta: { requiresAuth: true, island: 'tool' }
  },
  {
    path: '/admin',
    name: 'Admin',
    component: AdminView,
    meta: { requiresAuth: true, role: 'super_admin' }
  }
]
```

### 6.2 Pinia Store 示例（auth.js）

```javascript
// stores/auth.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login, getMe, logout } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  const isLoggedIn = computed(() => !!token.value)
  const isSuperAdmin = computed(() => user.value?.role === 'super_admin')

  async function loginAction(email, password) {
    const res = await login(email, password)
    token.value = res.data.token
    user.value = res.data.user
    localStorage.setItem('token', token.value)
    return res
  }

  async function fetchUser() {
    if (!token.value) return
    const res = await getMe()
    user.value = res.data
  }

  function logoutAction() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  return { token, user, isLoggedIn, isSuperAdmin, loginAction, fetchUser, logoutAction }
})
```

### 6.3 路由守卫

```javascript
// router/index.js (完整版)
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    next('/login')
    return
  }

  if (to.meta.role === 'super_admin' && !auth.isSuperAdmin) {
    next('/home')
    return
  }

  next()
})

export default router
```

### 6.4 背景音乐全局控制

```javascript
// composables/useMusicPlayer.js
import { ref, watch } from 'vue'
import { useSettingsStore } from '@/stores/settings'

export function useMusicPlayer() {
  const settings = useSettingsStore()
  const audio = ref(new Audio())

  watch(() => settings.bgMusicUrl, (url) => {
    audio.value.src = url
    audio.value.play()
  }, { immediate: true })

  function toggle() {
    if (audio.value.paused) {
      audio.value.play()
    } else {
      audio.value.pause()
    }
  }

  return { audio, toggle }
}
```

---

## 7. 部署方案

### 7.1 服务器端口

| 服务 | 端口 |
|------|------|
| 后端 FastAPI | 8000 |
| Nginx | 80/443 |

### 7.2 Nginx 配置

```nginx
# /etc/nginx/sites-available/yexingchen.cn
server {
    listen 80;
    server_name yexingchen.cn;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yexingchen.cn;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    root /var/www/yexingchen/dist;
    index index.html;

    # 前端路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 静态文件
    location /uploads/ {
        alias /var/www/yexingchen/uploads/;
        expires 30d;
    }

    # 音乐文件
    location /music/ {
        alias /var/www/yexingchen/uploads/music/;
        expires 30d;
        add_header Access-Control-Allow-Origin *;
    }
}
```

### 7.3 启动脚本

```bash
# backend/run.sh
#!/bin/bash
cd /var/www/yexingchen/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 7.4 PM2 守护进程（可选）

```bash
# backend/ecosystem.config.js
module.exports = {
  apps: [{
    name: 'yexingchen-api',
    script: 'run.py',
    interpreter: 'python3',
    cwd: '/var/www/yexingchen/backend',
    instances: 1,
    autorestart: true,
    watch: ['app/'],
    env: {
      PYTHONPATH: '/var/www/yexingchen/backend'
    }
  }]
}
```

---

## 8. 文件命名规范

| 类型 | 命名规范 | 示例 |
|------|---------|------|
| 音乐文件 | `{timestamp}_{uuid}.mp3` | `1716789000_a1b2c3.mp3` |
| 视频封面 | `{timestamp}_{uuid}_cover.jpg` | `1716789000_a1b2c3_cover.jpg` |
| 小说封面 | `{timestamp}_{uuid}_cover.{ext}` | `1716789000_a1b2c3_cover.jpg` |
| 上传目录 | `/uploads/music/` `/uploads/novels/` `/uploads/videos/` `/uploads/covers/` |
| 日志文件 | `app_{date}.log` | `app_2026-05-26.log` |

---

## 9. 第三方依赖

### 9.1 后端 requirements.txt

```
fastapi==0.110.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.29
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
pydantic==2.7.1
pydantic-settings==2.2.1
cos-python-sdk-v5==1.9.26  # 腾讯COS
aiosmtplib==3.0.1
Pillow==10.3.0  # 图片处理
python-dotenv==1.0.1
```

### 9.2 前端 package.json

```json
{
  "name": "yexingchen-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.27",
    "vue-router": "^4.3.2",
    "pinia": "^2.1.7",
    "axios": "^1.7.2",
    "element-plus": "^2.7.2"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.4",
    "vite": "^5.2.11"
  }
}
```

---

## 10. 开发里程碑

| 阶段 | 任务 | 预计顺序 |
|------|------|---------|
| M1 | 项目初始化 + 数据库 + JWT认证框架 | 1 |
| M2 | 注册/登录API + 邮箱验证码 | 2 |
| M3 | 用户管理后台（管理员） | 3 |
| M4 | 音乐/小说/视频/工具 CRUD API | 4 |
| M5 | 日志岛 + 全局搜索 API | 5 |
| M6 | 全局设置（背景音乐）API | 6 |
| M7 | Vue 前端初始化 + 路由 + Store | 7 |
| M8 | 登录页（动画）开发 | 8 |
| M9 | 主页面（岛屿背景+浮动动画）开发 | 9 |
| M10 | 各岛屿空间页面开发 | 10 |
| M11 | 管理员后台页面开发 | 11 |
| M12 | 响应式适配 + 细节调优 | 12 |
| M13 | 联调测试 + 部署上线 | 13 |

---

**下一步**：确认此技术设计文档，确认后进入代码开发阶段（M1 项目初始化）。