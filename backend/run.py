import os
import sys

# 添加 backend 目录到 Python 路径（仅一层 dirname：run.py → backend/）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        # v2.46.302：原来是单 worker。所有路由都是 async def 里跑同步 SQLAlchemy，
        # 一个请求查询期间事件循环被占住，其它请求只能排队 ——
        # 实测并发 5 个列表请求，第 4、5 个从 0.25s 涨到 1.3/1.6s；
        # 浏览器进音乐页一次要发十几个接口，末尾的就被拖到 3.5s。
        # 2 个 worker 后并发能力翻倍（服务器 2 核）。
        workers=2,
    )