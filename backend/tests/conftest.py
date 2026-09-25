"""pytest 配置文件

- 设置环境变量
- 确保所有 SQLAlchemy 模型都被 import 并注册到 Base.metadata
  （按 model 拆分到多个文件后，必须显式 import 才能让 mapper 的字符串关系解析成功）
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 设置环境变量用于测试
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ.setdefault('SMTP_USER', 'test@example.com')

# 触发所有模型 import，让 User 等类的 relationship('Music' / 'HouseholdMember' / ...)
# 字符串关系能解析；测试文件里不必再单独 import 这些模型。
#
# 这里改成自动遍历 app.models 包：此前是手写清单，随着模型变多（family / finance / life /
# habits / stocks / travels / workbench …）没有同步补充，导致 User 里指向 HouseholdMember
# 的 relationship 在测试中解析失败：
#   InvalidRequestError: expression 'HouseholdMember' failed to locate a name
# 自动遍历后，以后新增模型文件不需要再改这里。
import importlib
import pkgutil

import app.models as _models_pkg

for _mod in pkgutil.iter_modules(_models_pkg.__path__):
    importlib.import_module(f"app.models.{_mod.name}")
