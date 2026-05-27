# 项目版本信息

## 当前版本
- **版本号**: v1.1.0
- **版本名称**: 神农图·云境
- **发布日期**: 2026-05-27

## Git 仓库
- **地址**: https://github.com/y902chenjinxin/yexingchen-website
- **分支**: master (主分支)

## 版本迭代记录

### v1.1.0 (2026-05-27) ✓ 岛屿SVG已确认
- 登录页视觉重设计：年轻化渐变紫蓝配色
- 光效优化：纯净白光扫过效果
- 开门效果增强：增加光芒绽放动效
- 主页面背景改为渐变蓝天
- 五岛屿独立SVG设计图（音乐/小说/视频/日志/工具）✓
- 新增测试数据生成脚本 `generate_test_data.py`
- 背景音乐功能 `generate_bg_music.py`
- 代码优化：删除废弃的 `.island-icon` 样式，岛屿导航弹层图标统一为SVG，音乐按钮去除冗余 `!important`

### v1.0.0 (2026-05-26)
- 初始版本发布
- 神农图主题，云岛风格
- 5个内容岛屿：音乐、小说、视频、日志、工具
- FastAPI + Vue3 + SQLite 后端架构
- 邮箱注册+管理员审批流程
- JWT认证
- Nginx反向代理配置
- 腾讯云COS集成

## 账号信息

### 服务器
- **地址**: 203.195.208.25
- **用户**: root
- **密码**: Chen@12345678

### 数据库
- **类型**: SQLite
- **路径**: /var/www/yexingchen/backend/app.db

### 超级管理员
- **邮箱**: admin@yexingchen.cn
- **密码**: Chen@12345678

### GitHub
- **账号**: y902chenjinxin
- **Token**: <请在 GitHub Settings > Developer settings > Personal access tokens 中生成>

### 腾讯云
- **COS Bucket**: yexingfiles-1409757734
- **Region**: ap-guangzhou

### 域名
- **地址**: yexingchen.cn
- **SSL**: 已配置 (Let's Encrypt)

## 部署路径
- **后端**: /var/www/yexingchen/backend
- **前端**: /var/www/yexingchen/dist
- **日志**: /tmp/yexingchen_new.log