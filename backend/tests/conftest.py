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

# 触发所有模型 import，让 User 等类的 relationship('Music' / 'Novel' / ...) 字符串能解析。
# 测试文件里不必再单独 import 这些模型。
from app.models.user import User, VerificationCode  # noqa: F401,E402
from app.models.music import Music  # noqa: F401,E402
from app.models.novel import Novel  # noqa: F401,E402
from app.models.video import Video  # noqa: F401,E402
from app.models.tool import Tool  # noqa: F401,E402
from app.models.log import OperationLog  # noqa: F401,E402
from app.models.system import GlobalSetting, TokenBlocklist  # noqa: F401,E402
