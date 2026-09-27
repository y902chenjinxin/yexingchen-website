"""v2.40.21 生活岛三件套：遗失物件 / 穿搭推荐 / 密码保险箱。

down_revision 指向 `b8c9d0e1f2a3`（时间胶囊），这是用 `alembic heads` 确认过的当前 head。
"""
from alembic import op
import sqlalchemy as sa

revision = "d0e1f2a3b4c5"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade():
    # ---------- 遗失物件 ----------
    op.create_table(
        "lost_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("household_id", sa.Integer(), nullable=False, server_default="1", index=True),
        sa.Column("uploader_id", sa.Integer(), nullable=False, index=True),
        sa.Column("name", sa.String(120), nullable=False, server_default=""),
        sa.Column("category", sa.String(20), server_default="其他"),
        sa.Column("lost_at", sa.Date(), nullable=True),
        sa.Column("place", sa.String(160), server_default=""),
        sa.Column("scene", sa.Text(), server_default=""),
        sa.Column("mood", sa.String(60), server_default=""),
        sa.Column("value", sa.Integer(), nullable=True),
        sa.Column("photos", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("tags", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_lost_household_deleted", "lost_items", ["household_id", "deleted_at"])

    # ---------- 穿搭推荐：单品 ----------
    op.create_table(
        "wardrobe_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("household_id", sa.Integer(), nullable=False, server_default="1", index=True),
        sa.Column("owner_member_id", sa.Integer(), nullable=True, index=True),
        sa.Column("uploader_id", sa.Integer(), nullable=False, index=True),
        sa.Column("name", sa.String(120), nullable=False, server_default=""),
        sa.Column("category", sa.String(20), server_default="上装"),
        sa.Column("color_name", sa.String(30), server_default=""),
        sa.Column("color_hex", sa.String(9), server_default=""),
        sa.Column("seasons", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("warmth", sa.Integer(), server_default="3"),
        sa.Column("formality", sa.Integer(), server_default="3"),
        sa.Column("style_tags", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("photos", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("brand", sa.String(60), server_default=""),
        sa.Column("size", sa.String(30), server_default=""),
        sa.Column("price", sa.Integer(), nullable=True),
        sa.Column("buy_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), server_default="在穿"),
        sa.Column("wear_count", sa.Integer(), server_default="0"),
        sa.Column("last_worn_at", sa.Date(), nullable=True),
        sa.Column("note", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_wardrobe_owner_status", "wardrobe_items", ["owner_member_id", "status"])

    # ---------- 穿搭推荐：人档附加信息 ----------
    op.create_table(
        "wardrobe_person_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("household_id", sa.Integer(), nullable=False, server_default="1", index=True),
        sa.Column("member_id", sa.Integer(), nullable=False, index=True),
        sa.Column("full_body_photo", sa.String(300), server_default=""),
        sa.Column("size_note", sa.String(200), server_default=""),
        sa.Column("style_note", sa.String(300), server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("member_id", name="uq_wardrobe_profile_member"),
    )

    # ---------- 穿搭推荐：搭配收藏 ----------
    op.create_table(
        "wardrobe_outfits",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("household_id", sa.Integer(), nullable=False, server_default="1", index=True),
        sa.Column("owner_member_id", sa.Integer(), nullable=True, index=True),
        sa.Column("uploader_id", sa.Integer(), nullable=False, index=True),
        sa.Column("name", sa.String(80), server_default=""),
        sa.Column("item_ids", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("temp_min", sa.Integer(), nullable=True),
        sa.Column("temp_max", sa.Integer(), nullable=True),
        sa.Column("occasion", sa.String(20), server_default=""),
        sa.Column("tryon_image", sa.String(300), server_default=""),
        sa.Column("is_favorite", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    # ---------- 密码保险箱 ----------
    op.create_table(
        "vault_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("household_id", sa.Integer(), nullable=False, server_default="1", index=True),
        sa.Column("uploader_id", sa.Integer(), nullable=False, index=True),
        sa.Column("title", sa.String(120), nullable=False, server_default=""),
        sa.Column("url", sa.String(300), server_default=""),
        sa.Column("username", sa.String(160), server_default=""),
        sa.Column("password", sa.String(300), server_default=""),
        sa.Column("note", sa.Text(), server_default=""),
        sa.Column("category", sa.String(20), server_default="网站"),
        sa.Column("tags", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_vault_household_deleted", "vault_entries", ["household_id", "deleted_at"])


def downgrade():
    op.drop_table("vault_entries")
    op.drop_table("wardrobe_outfits")
    op.drop_table("wardrobe_person_profiles")
    op.drop_table("wardrobe_items")
    op.drop_table("lost_items")
