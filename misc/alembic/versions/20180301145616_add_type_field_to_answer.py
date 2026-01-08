"""add type field to answer

Revision ID: 078439197444
Revises: 8ee9b7e4411a
Create Date: 2018-03-01 14:56:16.255387

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "078439197444"
down_revision = "8ee9b7e4411a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("answer", sa.Column("type", sa.SmallInteger, nullable=False, server_default="1"))
    op.create_table(
        "admin_op",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("uid", sa.Integer, nullable=False),
        sa.Column("qid", sa.Integer, nullable=False),
        sa.Column("answer", sa.Integer, nullable=True),  # 管理员自答时产生的题目ID
        sa.Column("type", sa.SmallInteger, nullable=False),
        create_timestamp_field(
            "created_utc", sa.Integer, nullable=False, server_default=sa.text("extract(epoch from now())::int")
        ),
        create_timestamp_field(
            "updated_utc", sa.Integer, nullable=False, server_default=sa.text("extract(epoch from now())::int")
        ),
    )


def downgrade():
    op.drop_table("admin_op")
    op.drop_column("answer", "type")
