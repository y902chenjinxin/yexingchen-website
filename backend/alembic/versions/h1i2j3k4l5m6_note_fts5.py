"""note_fts5 全文搜索：为 notes 表建 FTS5 虚拟表 + 触发器同步。

- 虚拟表 note_fts 与 notes 表 rowid 对齐
- 3 个触发器（AI/AD/AU）同步 INSERT / DELETE / UPDATE
- 迁移执行后回填已有 notes 数据（仅未软删）

按用户隔离：在虚拟表里加 user_id 列，查询时按 uid 过滤。
"""
revision = "h1i2j3k4l5m6"
down_revision = "g1h2i3j4k5l6"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    bind = op.get_bind()
    has_notes = bind.execute(
        sa.text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='notes'")
    ).scalar() is not None
    # 1) 虚拟表：FTS5 + user_id 隔离
    op.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS note_fts USING fts5(
            title,
            content,
            summary,
            user_id UNINDEXED,
            tokenize = 'unicode61 remove_diacritics 2'
        )
        """
    )
    if not has_notes:
        # 老库/全新部署但表未建：仅建虚拟表，触发器等业务表就绪后再补
        return
    # 2) 触发器：notes 写入同步到 FTS5
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
            INSERT INTO note_fts(rowid, title, content, summary, user_id)
            VALUES (new.id, new.title, new.content, IFNULL(new.summary, ''), new.user_id);
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
            DELETE FROM note_fts WHERE rowid = old.id;
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
            DELETE FROM note_fts WHERE rowid = old.id;
            INSERT INTO note_fts(rowid, title, content, summary, user_id)
            VALUES (new.id, new.title, new.content, IFNULL(new.summary, ''), new.user_id);
        END
        """
    )
    # 3) 回填已有数据（仅未软删的）
    op.execute(
        """
        INSERT INTO note_fts(rowid, title, content, summary, user_id)
        SELECT id, title, content, IFNULL(summary, ''), user_id
        FROM notes
        WHERE deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS notes_ai")
    op.execute("DROP TRIGGER IF EXISTS notes_ad")
    op.execute("DROP TRIGGER IF EXISTS notes_au")
    op.execute("DROP TABLE IF EXISTS note_fts")
