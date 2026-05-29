---
name: project-lessons
description: 项目遇到的问题和解决记录，下次部署/开发时必读
metadata:
  type: project
---

## 项目经验积累

> 每次遇到问题并解决后，必须更新此文档

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

### 前端相关

| 问题 | 解决方案 | 预防措施 |
|------|----------|----------|
| CSS变量未定义 | 在variables.css补充--color-qi-primary等 | 使用CSS变量，禁止硬编码 |
| Math.random()导致动画不连贯 | 使用seed计算伪随机 | 注意渲染性能 |

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