"""内置背景曲改为真实音乐记录（v2.40.5）

需求：「系统默认」背景曲应该能像普通曲子一样被编辑、删除、打标签。

原实现的问题：`/api/music` 列表接口在返回前**硬塞**了一条合成条目
（`id='default'`、`is_default=True`），音频写死在 `uploads/bgm/bamboo_flute.mp3`。
它**不是数据库记录**，所以后台改不了、删不掉；而前端又把它当默认 BGM
在每次进站时自动播放。

本迁移把那个文件落成一条**真实**的 `music` 记录（`is_default=0`）。
之后列表接口不再合成条目，这首曲子就完全走普通曲子的增删改流程。

幂等：按 `file_path` 判重，已存在则直接返回，重复 upgrade 不会产生副本。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "z6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "y5z6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 统一用「相对 uploads 的绝对风格路径」，与其它曲目一致（_stream_file 会自动补 uploads/ 前缀）
FILE_PATH = "/bgm/bamboo_flute.mp3"


def _audio_size() -> int:
    """尽量取到音频真实体积；取不到就写 0（只影响列表里显示的大小）。"""
    import os

    here = os.path.dirname(os.path.abspath(__file__))          # backend/alembic/versions
    cand = os.path.join(here, "..", "..", "uploads", "bgm", "bamboo_flute.mp3")
    try:
        return os.path.getsize(os.path.normpath(cand))
    except OSError:
        return 0


def upgrade() -> None:
    conn = op.get_bind()

    dup = conn.execute(
        sa.text("SELECT id FROM music WHERE file_path = :p"), {"p": FILE_PATH}
    ).fetchone()
    if dup:
        return

    # uploader_id 非空且外键指向 users → 优先挂给超管，其次任意一个用户
    uid = conn.execute(
        sa.text("SELECT id FROM users WHERE is_super_admin = 1 ORDER BY id LIMIT 1")
    ).scalar()
    if uid is None:
        uid = conn.execute(sa.text("SELECT id FROM users ORDER BY id LIMIT 1")).scalar()
    if uid is None:
        return  # 库里一个用户都没有，跳过（正常部署不会走到这里）

    conn.execute(
        sa.text(
            "INSERT INTO music "
            "(title, artist, file_path, original_filename, duration, category, tags, "
            " uploader_id, file_size, created_at, updated_at, is_test_data, is_default) "
            "VALUES (:title, :artist, :path, :orig, 0, :cat, :tags, "
            "        :uid, :size, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, 0)"
        ),
        {
            "title": "玄黄古筝",
            "artist": "系统内置",
            "path": FILE_PATH,
            "orig": "bamboo_flute.mp3",
            "cat": "古风",
            "tags": "古筝,古风,背景音乐",
            "uid": uid,
            "size": _audio_size(),
        },
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text("DELETE FROM music WHERE file_path = :p"), {"p": FILE_PATH}
    )
