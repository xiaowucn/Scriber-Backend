"""add_table_model_version

Revision ID: 81e3143aaa23
Revises: 7756a52ff32f
Create Date: 2019-09-11 11:35:59.764424

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "81e3143aaa23"
down_revision = "7756a52ff32f"
branch_labels = None
depends_on = None
table_name = "model_version"


def upgrade():
    op.create_table(
        table_name,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("mold", sa.Integer, nullable=False),
        sa.Column("type", sa.Integer, nullable=False),  # 1：精确定位，2：初步定位
        sa.Column("status", sa.Integer, server_default=sa.text("0")),  # 模型状态
        create_array_field("dirs", sa.ARRAY(sa.Integer)),  # 训练目录
        create_array_field("files", sa.ARRAY(sa.Integer)),  # 文件范围
        sa.Column("enable", sa.Integer, server_default=sa.text("0")),  # 0：未启用，2：启用
        create_timestamp_field(
            "created_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
    )


def downgrade():
    op.drop_table(table_name)
