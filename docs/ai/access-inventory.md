# 访问与环境清单

> 只记录非敏感信息。密码、私钥、Token、Secret 等不要写在此文件。

## GitHub

- 用户名：
- 仓库地址：
- 仓库是否私有：是 / 否 / 待确认
- 默认分支：
- 是否允许协助提交代码：是 / 否 / 待确认
- 是否已有 Actions：是 / 否 / 待确认

## 腾讯云服务器

- 公网 IP：203.195.208.25
- SSH 用户名：
- SSH 端口：22 / 其他：
- 操作系统：
- 是否有 sudo 权限：是 / 否 / 不清楚
- Docker 是否可用：是 / 否 / 不清楚
- 部署目录：
- 服务器所在地域：

## 域名与 HTTPS

- 主域名：https://yexingchen.cn/
- www 域名：
- DNS 管理位置：
- 证书管理位置：
- 当前证书到期日：待修复/核验

## 应用与部署

- 前端技术栈：Vue 3 / Vue Router / Element Plus / Axios（线上构建产物初步判断）
- 后端技术栈：
- 数据库：
- 文件存储：
- 反向代理：Nginx
- 部署方式：Docker / 其他：
- 日志位置：
- 备份位置：

## 外部服务

<!-- 例如：腾讯云 COS、对象存储、GitHub、AI API、邮件、企业微信等。 -->

| 服务 | 用途 | 是否已接入 | 配置位置 | 备注 |
|---|---|---|---|---|
|  |  |  |  |  |

## 2026-08-27：项目与线上环境核对结果

- GitHub 仓库：`https://github.com/y902chenjinxin/yexingchen-website`
- 仓库状态：公开，默认分支 `master`
- 当前版本线索：v2.12.0，最近提交日期 2026-05-31
- 前端：Vue 3 / Vite / Vue Router / Pinia / Element Plus / Axios / Three.js
- 后端：FastAPI / SQLAlchemy / JWT；默认 SQLite；支持腾讯云 COS 和 SMTP
- 仓库部署文档：Nginx + PM2；是否实际使用 Docker 待 SSH 只读核验
- 本地授权状态：`GITHUB_TOKEN` 当前为空，未使用 GitHub 私有授权
- 安全备注：公开仓库中存在服务器凭证明文，已列为最高优先级待处理事项；此处不记录具体凭证

## 2026-08-27：安全处置更新

- 服务器登录密码：用户已更换；新值不写入项目记忆
- 腾讯云 COS：原桶已删除；新文件存储方案待重新设计
- GitHub 历史敏感内容：待清理
- SMTP/JWT：用户暂未处理，是否存在实际泄露待后续核验
- SSH 访问：后续必须使用新凭证，不能继续使用公开仓库中出现过的旧凭证

## 协作方式

- 设计、PRD、架构、评审、验收和部署检查：当前助手负责
- 代码实现和常规测试：交给用户指定的 Coding 模型执行
- 敏感账号和云控制台操作：由用户在本地/控制台完成，不在会话中粘贴新凭证


## 2026-08-30：服务器只读核验完成

- 状态：已确认，待部署
- 系统：OpenCloudOS 9.4
- Nginx：1.26.3，运行中
- Docker：未安装/不可用
- 后端：PM2 管理 Python 进程，监听 0.0.0.0:8000
- 前端：`/var/www/yexingchen/dist`
- 后端：`/var/www/yexingchen/backend`
- 数据库：`/var/www/yexingchen/backend/yexingchen.db`，当前只有旧 9 张表，无 `alembic_version`
- 线上工作台：`/api/workbench/summary` 当前返回 404，尚未部署
- 服务器虚拟环境：Python 3.11.6，Alembic 尚未安装
- ENV：production
- HTTPS：当前证书有效至 2026-11-12
- 磁盘：40G，总使用约 29%
- 部署方式结论：Nginx 静态前端 + PM2/Python 后端 + SQLite
- 部署前：需要保留前后端旧版本回滚副本；不执行业务数据备份（用户已明确 MVP 不做备份）


## 2026-08-30：玄黄 MVP 生产部署

- 状态：已完成基础上线
- 线上前端：`/var/www/yexingchen/dist`
- 线上后端：`/var/www/yexingchen/backend`
- 进程：PM2 `app` online
- 数据库：22 张表，Alembic `b2c3d4e5f6a7 (head)`
- 回滚 release：`/var/www/yexingchen/releases/20260830-120959`
- AI：当前未配置真实 Provider，默认 fake
- 证书：当前证书有效至 2026-11-12
