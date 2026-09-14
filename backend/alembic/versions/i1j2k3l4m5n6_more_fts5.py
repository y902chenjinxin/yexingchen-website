"""asset_fts5 / task_fts5 / feed_article_fts5 全文搜索：扩展 FTS5 覆盖 Asset / Task / FeedArticle。

- 每个表独立虚拟表，按 rowid 对齐；用 user_id UNINDEXED 做用户隔离
- 每个表 3 个触发器（AI/AD/AU）同步 INSERT / DELETE / UPDATE
- 迁移执行后回填已有未软删数据
- 业务表不存在时只建虚拟表（兼容老库 baseline）
"""
revision = "i1j2k3l4m5n6"
down_revision = "h1i2j3k4l5m6"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def _has_table(bind, name: str) -> bool:
    return bind.execute(
        sa.text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:n"),
        {"n": name},
    ).scalar() is not None


def _create_fts_and_triggers(
    table_name: str,
    virtual_table: str,
    columns: str,
    has_business_table: bool,
) -> None:
    """建虚拟表 + 触发器 + 回填。业务表不存在时只建虚拟表。"""
    op.execute(
        f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS {virtual_table} USING fts5(
            {columns},
            user_id UNINDEXED,
            tokenize = 'unicode61 remove_diacritics 2'
        )
        """
    )
    if not has_business_table:
        return
    op.execute(
        f"""
        CREATE TRIGGER IF NOT EXISTS {table_name}_ai AFTER INSERT ON {table_name} BEGIN
            INSERT INTO {virtual_table}(rowid, user_id) VALUES (new.id, new.user_id);
        END
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER IF NOT EXISTS {table_name}_ad AFTER DELETE ON {table_name} BEGIN
            DELETE FROM {virtual_table} WHERE rowid = old.id;
        END
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER IF NOT EXISTS {table_name}_au AFTER UPDATE ON {table_name} BEGIN
            DELETE FROM {virtual_table} WHERE rowid = old.id;
            INSERT INTO {virtual_table}(rowid, user_id) VALUES (new.id, new.user_id);
        END
        """
    )
    # 回填已有数据
    op.execute(
        f"""
        INSERT INTO {virtual_table}(rowid, user_id)
        SELECT id, user_id FROM {table_name}
        WHERE deleted_at IS NULL OR deleted_at IS NULL
        """
    )


def upgrade() -> None:
    bind = op.get_bind()

    # Asset: 含 title / description / url / original_filename
    has_assets = _has_table(bind, "assets")
    _create_fts_and_triggers(
        "assets",
        "asset_fts",
        "title, description, url, original_filename",
        has_assets,
    )
    # 回填 Asset 字段（不只 rowid/user_id）
    if has_assets:
        op.execute(
            """
            INSERT OR REPLACE INTO asset_fts(rowid, title, description, url, original_filename, user_id)
            SELECT id, title, description, IFNULL(url, ''), IFNULL(original_filename, ''), user_id
            FROM assets
            WHERE deleted_at IS NULL
            """
        )

    # Task: 含 title / description
    has_tasks = _has_table(bind, "tasks")
    _create_fts_and_triggers(
        "tasks",
        "task_fts",
        "title, description",
        has_tasks,
    )
    if has_tasks:
        op.execute(
            """
            INSERT OR REPLACE INTO task_fts(rowid, title, description, user_id)
            SELECT id, title, IFNULL(description, ''), user_id
            FROM tasks
            WHERE deleted_at IS NULL
            """
        )

    # FeedArticle: 含 title / title_zh / summary_zh / content_zh
    # 业务表名 xuanhuang_articles
    has_articles = _has_table(bind, "xuanhuang_articles")
    _create_fts_and_triggers(
        "xuanhuang_articles",
        "feed_article_fts",
        "title, title_zh, summary_zh, content_zh",
        has_articles,
    )
    if has_articles:
        op.execute(
            """
            INSERT OR REPLACE INTO feed_article_fts(rowid, title, title_zh, summary_zh, content_zh, user_id)
            SELECT id, title, IFNULL(title_zh, ''), IFNULL(summary_zh, ''), IFNULL(content_zh, ''), user_id
            FROM xuanhuang_articles
            """
        )


def downgrade() -> None:
    for trig in (
        "assets_ai", "assets_ad", "assets_au",
        "tasks_ai", "tasks_ad", "tasks_au",
        "xuanhuang_articles_ai", "xuanhuang_articles_ad", "xuanhuang_articles_au",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {trig}")
    op.execute("DROP TABLE IF EXISTS asset_fts")
    op.execute("DROP TABLE IF EXISTS task_fts")
    op.execute("DROP TABLE IF EXISTS feed_article_fts")
