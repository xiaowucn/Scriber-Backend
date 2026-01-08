"""create tables for law

Revision ID: 1ac4443bc202
Revises: 07f9454f6a82
Create Date: 2025-05-20 10:20:54.028217

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field
from remarkable.db import IS_MYSQL

# revision identifiers, used by Alembic.
revision = "1ac4443bc202"
down_revision = "07f9454f6a82"
branch_labels = None
depends_on = None


def upgrade():
    rank = "`rank`" if IS_MYSQL else "rank"

    op.create_table(
        "law_order",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("rank", sa.Integer, index=True, unique=True),
        sa.Column("name", sa.String(255), nullable=False),  # 业务长度100
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("updated_by_id", sa.Integer),
    )
    op.execute(f"""INSERT INTO law_order({rank}, name, deleted_utc, user_id) VALUES (0, '', 1, 1);""")

    op.create_table(
        "law",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("order_id", sa.Integer, index=True),
        sa.Column("name", sa.String(255), nullable=False),  # 业务长度100
        sa.Column("hash", sa.String(32)),
        sa.Column("size", sa.Integer),
        sa.Column("page", sa.Integer),
        sa.Column("docx", sa.String(32)),
        sa.Column("pdf", sa.String(32)),
        sa.Column("pdfinsight", sa.String(32)),
        sa.Column("chatdoc_unique", sa.String(255)),
        sa.Column("is_current", sa.Boolean, server_default="0"),
        sa.Column("status", sa.SmallInteger, server_default="0"),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
    )

    op.create_table(
        "law_scenario",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(30), nullable=False, index=True, unique=True),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("updated_by_id", sa.Integer),
    )

    op.create_table(
        "laws_scenarios",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("law_id", sa.Integer, nullable=False, index=True),
        sa.Column("scenario_id", sa.Integer, nullable=False, index=True),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("updated_by_id", sa.Integer),
    )


def downgrade():
    op.drop_table("laws_scenarios")
    op.drop_table("law_scenario")
    op.drop_table("law")
    op.drop_table("law_order")
