"""生活模块启动引导（v2.15）

非生产环境走 Base.metadata.create_all() 路径，Alembic migration 的"种子数据"不会执行。
此函数补齐：
- 确保全局 household id=1 存在
- 给所有现有用户自动建 member 档案（已存在就跳过）
- 兼容 SQLite / Postgres
"""
import logging
from app.models.life import Household, HouseholdMember
from app.models.user import User


logger = logging.getLogger(__name__)


def bootstrap_life(session_factory) -> None:
    """session_factory: 接受一个无参回调返回 Session（与 get_db 一致）。"""
    db = session_factory()
    try:
        # 1) 全局 household
        h = db.query(Household).filter(Household.id == 1).first()
        if not h:
            h = Household(id=1, name="我的家")
            db.add(h); db.flush()
            logger.info("[life] 创建全局 household id=1")

        # 2) 给每个 user 补一份 member 档案（一账号一成员）
        users = db.query(User).all()
        existing_user_ids = {m.user_id for m in db.query(HouseholdMember).all()}
        added = 0
        for u in users:
            if u.id in existing_user_ids:
                continue
            display_name = (u.nickname or u.email.split("@")[0])[:64]
            m = HouseholdMember(
                user_id=u.id,
                household_id=1,
                display_name=display_name,
                avatar="🌿",
                is_owner=1 if u.role == "admin" else 0,
            )
            db.add(m); added += 1
        if added:
            db.commit()
            logger.info("[life] 自动建 %d 个家庭成员档案", added)
    except Exception as e:  # noqa: BLE001
        logger.exception("[life] bootstrap failed: %s", e)
        db.rollback()
    finally:
        db.close()
