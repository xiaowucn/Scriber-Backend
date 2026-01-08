"""add new table cmbchina_answer

Revision ID: ace0d163721c
Revises: c7c9b14317e5
Create Date: 2024-07-09 10:26:10.923197

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "ace0d163721c"
down_revision = "c7c9b14317e5"
branch_labels = None
depends_on = None
table = "cmbchina_answer"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("fid", sa.Integer, nullable=False),
        create_jsonb_field("answer", nullable=True),
        sa.Column("product_code", sa.String(512), nullable=True),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )

    op.create_index("cmbchina_answer_fid_product_code_key", table, ["fid", "product_code"], unique=True)


def downgrade():
    op.drop_table(table)
