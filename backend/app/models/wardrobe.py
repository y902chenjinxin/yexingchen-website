"""穿搭推荐（生活岛）—— 三张表。

设计要点（v2.40.21）：
- **人（owner）与上传人（uploader）分离**：妈妈可以帮孩子上传衣服，但归属人是孩子；
  推荐**必须按归属人分开算**，绝不把爸爸的衣服推给妈妈。
- 「人」的事实来源是站内 `household_member`（昵称/头像都在那），这里只存**穿搭附加信息**
  （全身照、尺码备注），按需创建，避免两套人名单。
- 复用「家庭成员」而非新建人表 → 前端一套人列表即可同时服务「筛选」与「推荐选人」。
"""
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, String, Text, UniqueConstraint

from app.database import Base


class WardrobeItem(Base):
    """单品：一件衣服/一双鞋。"""
    __tablename__ = "wardrobe_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    household_id = Column(Integer, nullable=False, default=1, index=True)
    owner_member_id = Column(Integer, nullable=True, index=True)    # 归属人（household_member.id）
    uploader_id = Column(Integer, nullable=False, index=True)       # 谁上传的（= users.id）
    name = Column(String(120), nullable=False, default="")
    category = Column(String(20), default="上装")                   # 上装/下装/外套/连衣裙/鞋/配饰
    color_name = Column(String(30), default="")                    # 黑 / 白 / 藏青…
    color_hex = Column(String(9), default="")                      # #RRGGBB，便于搭配判色
    seasons = Column(Text, nullable=False, default="[]")            # JSON ["春","秋","冬"]
    warmth = Column(Integer, default=3)                            # 1~5 保暖度
    formality = Column(Integer, default=3)                         # 1 居家 ~ 5 正式
    style_tags = Column(Text, nullable=False, default="[]")         # JSON ["通勤","运动"]
    photos = Column(Text, nullable=False, default="[]")             # JSON [url...]，第一张为封面
    brand = Column(String(60), default="")
    size = Column(String(30), default="")
    price = Column(Integer, nullable=True)
    buy_date = Column(Date, nullable=True)
    status = Column(String(20), default="在穿")                     # 在穿/闲置/已淘汰
    wear_count = Column(Integer, default=0)
    last_worn_at = Column(Date, nullable=True)
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True)


class WardrobePersonProfile(Base):
    """穿搭人附加信息：全身照（试穿/拼贴用）与尺码备注。人本身在 household_member。"""
    __tablename__ = "wardrobe_person_profiles"
    __table_args__ = (
        UniqueConstraint("member_id", name="uq_wardrobe_profile_member"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    household_id = Column(Integer, nullable=False, default=1, index=True)
    member_id = Column(Integer, nullable=False, index=True)         # household_member.id
    full_body_photo = Column(String(300), default="")              # /uploads/wardrobe/xxx.jpg
    size_note = Column(String(200), default="")                    # 上衣 L / 鞋 42
    style_note = Column(String(300), default="")                   # 偏好备注
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class WardrobeOutfit(Base):
    """搭配收藏：一套「今天就这么穿」。也按人存，绝不跨人共用。"""
    __tablename__ = "wardrobe_outfits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    household_id = Column(Integer, nullable=False, default=1, index=True)
    owner_member_id = Column(Integer, nullable=True, index=True)
    uploader_id = Column(Integer, nullable=False, index=True)
    name = Column(String(80), default="")
    item_ids = Column(Text, nullable=False, default="[]")           # JSON [item_id...]
    temp_min = Column(Integer, nullable=True)                      # 适用温度区间
    temp_max = Column(Integer, nullable=True)
    occasion = Column(String(20), default="")                      # 通勤/居家/正式/运动
    tryon_image = Column(String(300), default="")                  # 试穿或拼贴成品图（可空）
    is_favorite = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True)
