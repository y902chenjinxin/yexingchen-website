# 叶兴辰的个人网站

基于万妖之祖·神农图灵感，采用云上浮空岛屿视觉风格的个人云存储与展示平台。

## 技术栈

- **前端**: Vue 3 + Vite + Pinia + Vue Router + Element Plus
- **后端**: Python FastAPI + SQLAlchemy + JWT
- **数据库**: SQLite
- **文件存储**: 腾讯 COS
- **邮件**: QQ邮箱 SMTP
- **部署**: Nginx + Uvicorn

## 项目结构

```
yexingchen/
├── backend/              # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py      # FastAPI 入口
│   │   ├── config.py    # 配置
│   │   ├── database.py  # 数据库连接
│   │   ├── models/      # SQLAlchemy 模型
│   │   ├── schemas/     # Pydantic 模型
│   │   ├── routers/     # API 路由
│   │   ├── services/    # 业务逻辑
│   │   └── utils/       # 工具函数
│   ├── uploads/         # 文件上传目录
│   ├── requirements.txt
│   └── run.py           # 启动脚本
│
├── frontend/            # Vue 3 前端
│   ├── src/
│   │   ├── api/         # API 封装
│   │   ├── assets/      # 静态资源
│   │   ├── components/  # 公共组件
│   │   ├── composables/ # 组合式函数
│   │   ├── router/      # 路由配置
│   │   ├── stores/      # Pinia Store
│   │   └── views/       # 页面组件
│   └── package.json
│
└── nginx/               # Nginx 配置
```

## 快速启动

### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入真实配置

# 启动服务
python run.py
# 或
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
```

## 功能模块

- **🎵 音乐岛**: 音乐文件上传、播放列表、搜索、下载
- **📖 小说岛**: 电子书上传播放、管理、下载
- **🎬 视频岛**: 视频链接管理、腾讯COS存储
- **📝 日志岛**: 操作日志记录与查看
- **⚙️ 工具岛**: 常用外链收藏管理
- **🔐 用户系统**: 注册审批、角色权限、JWT认证
- **🔍 全局搜索**: 跨岛屿内容搜索

## 配置说明

### 腾讯 COS

需要配置 `COS_SECRET_ID` 和 `COS_SECRET_KEY`，可在 [腾讯云控制台](https://console.cloud.tencent.com/cos) 获取。

### QQ邮箱授权码

1. 登录 QQ 邮箱网页版
2. 设置 → 账户 → POP3/SMTP服务 → 生成授权码
3. 将授权码填入 `SMTP_PASSWORD`

## 部署

1. 前端构建: `npm run build`，将 `dist` 目录部署到 Nginx
2. 后端启动: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
3. 配置 Nginx 反向代理，参考 `nginx/yexingchen.cn.conf`

## API 文档

启动后端后访问 `http://localhost:8000/docs` 查看完整 API 文档。