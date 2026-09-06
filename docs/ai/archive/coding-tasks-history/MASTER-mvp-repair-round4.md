# 玄黄 MVP 最终上线前集中修复

## 必须修复

1. 完善 `frontend/src/utils/note-assets.js` 的富文本安全清洗：
   - 使用成熟 sanitizer 或明确白名单；
   - 移除 script、style、iframe 等不允许标签；
   - 移除 on* 事件属性；
   - 普通链接只允许安全 scheme；
   - 保留 data-asset-id 图片/PDF 占位结构；
   - 增加 XSS 回归测试。
2. 修复 `frontend/src/views/AssetsView.vue` 下载竞态：
   - 点击时阻止默认行为；
   - fetchBlob(download) 成功后显式触发临时下载；
   - 释放临时 object URL；
   - 失败显示提示；
   - 增加下载行为测试。
3. 修复本轮新增文件的 lint error：
   - 删除未使用 import/函数，或接入实际逻辑；
   - 不全量格式化旧代码。

## 必须验证

```text
python -m compileall -q backend/app backend/tests backend/alembic
pytest backend/tests -q
pip check

cd frontend
npm run build
npm run test
```

另需验证：

- `<script>`、`onerror`、`onclick`、`javascript:` 等不会进入可执行持久化 HTML；
- 资产下载在 object URL 未预加载时也能稳定触发；
- 新增/修改文件 lint error 为 0；
- 测试数据库、缓存、上传文件和 `__pycache__` 清理。

不要连接生产、迁移生产、推送 GitHub 或部署。
