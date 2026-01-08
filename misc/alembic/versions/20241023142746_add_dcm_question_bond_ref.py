"""add_dcm_question_order_ref

Revision ID: 8579708e1bd4
Revises: db3ad876238b
Create Date: 2024-10-23 14:27:46.457285

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "8579708e1bd4"
down_revision = "db3ad876238b"
branch_labels = None
depends_on = None
table = "dcm_question_order_ref"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("question_id", sa.Integer),
        sa.Column("order_id", sa.Integer),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
    op.create_index("question_order_ref_unique", table, ["question_id", "order_id"], unique=True)


def downgrade():
    op.drop_table(table)
