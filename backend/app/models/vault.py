"""密码保险箱（生活岛）—— 家里共享的「不重要的密码」便签本。

⚠️ 定位边界（页面顶部也会写）：**只放不重要、丢了不致命的密码**
（网站会员、WiFi、门禁、旧设备、临时注册）。银行/支付/邮箱/主账号请用专业工具
（Vaultwarden / KeePassXC / 系统钥匙串）。

按 v2.40.21 决策：**不加密**（是便签本不是金库），**家庭共享**（household_id 过滤），
记住 `uploader_id` 以便「谁存的」可见、可筛选。前端默认打码，点开才显示。
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database import Base


class VaultEntry(Base):
    __tablename__ = "vault_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    household_id = Column(Integer, nullable=False, default=1, index=True)
    uploader_id = Column(Integer, nullable=False, index=True)
    title = Column(String(120), nullable=False, default="")
    url = Column(String(300), default="")
    username = Column(String(160), default="")
    password = Column(String(300), default="")
    note = Column(Text, default="")
    category = Column(String(20), default="网站")     # 网站/WiFi/设备/门禁/其他
    tags = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True)
