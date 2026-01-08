"""upgrade for ht branch

Revision ID: f74d5b398afc
Revises: 34b3977dcd23
Create Date: 2021-09-14 14:46:40.814410

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "f74d5b398afc"
down_revision = "34b3977dcd23"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("admin_user", sa.Column("department", sa.String(255)))
    op.add_column("admin_user", sa.Column("department_id", sa.String(255)))

    op.create_table(
        "diff_cmp",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("uid", sa.Integer, nullable=False, index=True),
        sa.Column("f1_name", sa.String(255)),
        sa.Column("f1_size", sa.Integer),
        sa.Column("f1_hash", sa.String(32), index=True),
        sa.Column("f1_pdf_hash", sa.String(32)),
        sa.Column("f1_pdfinsight", sa.String(32)),
        sa.Column("f2_name", sa.String(256)),
        sa.Column("f2_size", sa.Integer),
        sa.Column("f2_hash", sa.String(32), index=True),
        sa.Column("f2_pdf_hash", sa.String(32)),
        sa.Column("f2_pdfinsight", sa.String(32)),
        sa.Column("result_hash", sa.String(32)),  # 比对结果可能超过jsonb的存储限制, 所以改为存储到本地, 数据库只存路径
        sa.Column("total_diff", sa.Integer),
        sa.Column("status", sa.Integer),
        create_timestamp_field(
            "created_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
        create_timestamp_field(
            "updated_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
        create_timestamp_field("deleted_utc", sa.Integer, server_default=sa.text("0")),
    )

    op.create_table(
        "file_template",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("hash", sa.String(32)),
        sa.Column("mold", sa.Integer),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("deleted_utc", sa.Integer, server_default=sa.text("0")),
    )

    op.create_table(
        "extract_method",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("path", sa.String(1024), nullable=False),
        sa.Column("mold", sa.Integer, nullable=False),
        sa.Column("data", sa.JSON, nullable=False),
        sa.Column("method_type", sa.Integer, nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("deleted_utc", sa.Integer, server_default=sa.text("0")),
    )

    op.create_table(
        "rule_class",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("mold", sa.Integer, nullable=False),
        sa.Column("method_type", sa.Integer, nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("deleted_utc", sa.Integer, server_default=sa.text("0")),
    )

    op.create_table(
        "rule_item",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("mold", sa.Integer, nullable=False),
        sa.Column("class", sa.Integer, nullable=False),
        sa.Column("method_type", sa.Integer, nullable=False),
        sa.Column("data", sa.JSON, nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("deleted_utc", sa.Integer, server_default=sa.text("0")),
    )

    op.create_table(
        "access_token",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("password", sa.String(255), nullable=False, unique=True),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("deleted_utc", sa.Integer, server_default=sa.text("0")),
    )


def downgrade():
    op.drop_table("access_token")
    op.drop_table("rule_item")
    op.drop_table("rule_class")
    op.drop_table("extract_method")
    op.drop_table("file_template")
    op.drop_table("diff_cmp")

    op.drop_column("admin_user", "department_id")
    op.drop_column("admin_user", "department")
