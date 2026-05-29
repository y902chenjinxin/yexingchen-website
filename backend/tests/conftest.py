"""pytest配置文件"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 设置环境变量用于测试
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"