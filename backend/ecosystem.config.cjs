// 生产后端 pm2 application 配置
// 关键作用：固定 ENV=production，启用「资讯自动同步」等仅生产特性。
// 其余密钥 / 数据库等配置统一由 backend/.env (pydantic-settings) 加载，不入本文件、不入 git。
module.exports = {
  apps: [{
    name: 'yexingchen-backend',
    cwd: '/var/www/yexingchen/backend',
    script: '/var/www/yexingchen/backend/run.py',
    interpreter: '/var/www/yexingchen/backend/venv/bin/python',
    exec_mode: 'fork',
    autorestart: true,
    max_restarts: 10,
    env: {
      ENV: 'production'
    }
  }]
}