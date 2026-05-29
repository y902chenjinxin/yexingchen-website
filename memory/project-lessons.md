---
name: project-lessons
description: 项目遇到的问题和解决记录，下次部署/开发时必读
metadata:
  type: project
---

## 项目经验积累

> 每次遇到问题并解决后，必须更新此文档

---

## v1.7.2 部署问题（2026-05-29）

| 问题 | 解决方案 | 预防措施 |
|------|----------|----------|
| 上传脚本path拼接bug | 重写upload_dist_fix.py，path统一 `replace("\\", "/")` | SFTP路径必须用正斜杠 |
| 服务器dist目录损坏 | 删除重建dist目录 | 部署后立即验证 `sftp.listdir()` |
| nginx返回403 | 检查root目录是否有index.html | 部署后先curl验证HTTP 200 |

### 部署验证清单
1. 上传后 `sftp.listdir(remote_dist)` 确认文件数 > 0
2. `curl -I https://yexingchen.cn` 确认 HTTP 200
3. `curl -s https://yexingchen.cn/assets/index-*.js | head -c 100` 确认JS可访问

---

## v1.6.1 审查发现的问题（2026-05-29）

### 安全相关

| 问题 | 解决方案 | 预防措施 |
|------|----------|----------|
| CORS允许任意来源 | 限制allow_origins为yexingchen.cn | 生产环境禁止通配符 |
| SECRET_KEY硬编码默认值 | 移除默认值，启动时强制检查 | 环境变量必须配置 |
| 注册接口无限流 | 增加RegisterLimiter，1小时最多3次 | 所有敏感接口必须限流 |
| 修改密码API未实现 | 实现/api/auth/change-password接口 | 功能开发完成必须自测 |
| 头像保存API未实现 | avatar_id字段+updateMe接口 | 同上 |

### CI相关

| 问题 | 解决方案 | 预防措施 |
|------|----------|----------|
| Lint失败被静默忽略 | 移除continue-on-error:true | CI必须严格 |
| 后端无测试文件 | 创建backend/tests/目录 | 新功能必须配套测试 |
| E2E未纳入CI | 补充CI中的e2e job | 自动化测试必须纳入CI |

### 后端相关

| 问题 | 解决方案 | 预防措施 |
|------|----------|----------|
| JWT payload伪造风险 | get_current_user每次查DB验证用户状态 | 不能只信任JWT payload |
| 密码明文存储风险 | 使用pbkdf2_sha256，get_password_hash() | 禁止明文 |
| 错误码体系不统一 | ErrCode 5位系统（XYnnn） | 使用raise_error(ErrCode.XXX) |
| API路由重复前缀 | /api/v1统一前缀 | 检查router.prefix |

### UI/前端相关

| 问题 | 解决方案 | 预防措施 |
|------|----------|----------|
| CSS变量未定义 | 在variables.css补充--color-qi-primary等 | 使用CSS变量，禁止硬编码 |
| Math.random()导致动画不连贯 | 使用seed计算伪随机 | 注意渲染性能 |
| 硬编码颜色#1a1a2e, #667eea | 全部替换为CSS变量 | CSS变量强制检查 |
| HomeView.vue 975行超大组件 | 拆分composables/提取组件 | 单一职责原则 |
| CSS变量重复定义 | --color-primary等定义了两次 | 新增变量必须追加到现有块，禁止重定义 |

---

## 强制规则（来自团队审查）

### 前端强制规则
- **CSS变量双重定义Bug**: `--color-primary`、`--color-secondary`、`--color-accent` 在 variables.css 中各自定义了两次（行54-56和59-61）。新颜色变量必须追加到现有块，禁止重新声明已有变量
- **组件行数限制**：Vue单文件组件不得超过500行。超限时必须拆分：把逻辑提取到 `composables/`，把子UI提取到 `components/`。当前违规：HomeView.vue(975行)、LoginView.vue(1204行)
- **动画seed模式**：粒子/仙气等连续动画必须使用确定性的seed计算伪随机，禁止直接用 `Math.random()`
- **CSS变量门控**：每次修改样式前必须 `grep -n '#\|rgb(' **/*.vue` 确认无硬编码hex/rgb

### 后端强制规则
- **Pydantic Schema强制**：所有API请求/响应必须使用Pydantic Schema，禁止dict直传
- **统一错误格式**：raise_error(ErrCode.XXX) 是唯一错误抛出方式，禁止直接raise HTTPException
- **API路由前缀**：所有router必须使用 /api/v1 前缀，禁止混用
- **数据库Migration**：使用Alembic，禁止直接create_all。新增表/字段必须生成migration: `alembic revision --autogenerate -m 'add xxx'`
- **Migration回滚**：每次migration后检查docs/ROLLBACK.md是否更新
- **认证vs授权分离**：get_current_user只验身份，依赖require_super_admin验权限
- **输入验证**：Pydantic Schema的Field()必须设置ge/le constraints，禁止白名单放开
- **文件上传**：必须UUID存储+后缀白名单+content-type检测，不能信任前端传来扩展名

---

## 历史问题记录

### v1.6.0 部署问题

| 日期 | 问题 | 解决 |
|------|------|------|
| 2026-05-29 | 前端dist打包路径错误 | 使用npm run build正确输出 |
| 2026-05-29 | 服务器密码硬编码 | 迁移到环境变量管理 |

### 沟通要求

1. **部署前必须自测**：使用npm run preview验证
2. **提交前必须lint**：npm run lint通过后再commit
3. **Secret Key必须设置**：生产环境必须配置.env文件
4. **依赖变更必须测试**：pip install / npm install后验证功能正常

---

## 开发注意事项

### 后端
- SECRET_KEY必须从环境变量读取，禁止硬编码默认值
- 所有敏感接口必须加限流
- 数据库迁移必须走migration脚本

### 前端
- 使用variables.css中的CSS变量，禁止硬编码颜色
- 组件销毁时必须清理定时器
- 表单提交前必须做客户端验证

### CI/CD
- lint失败必须阻断CI
- 自动化测试必须纳入CI
- 安全扫描(npm audit)必须定期执行