"""add_column_to_cmf_ab_compare

Revision ID: b2b21f0a004a
Revises: d2890c68da3e
Create Date: 2025-05-29 10:06:46.806246

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "b2b21f0a004a"
down_revision = "d2890c68da3e"
branch_labels = None
depends_on = None


table_name = "cmf_ab_compare"


def upgrade():
    op.add_column(table_name, sa.Column("use_llm", sa.Boolean, server_default=sa.text("false")))
    op.add_column(table_name, sa.Column("prompt", sa.Text))
    op.add_column(
        table_name,
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )

    op.add_column(
        "cmf_shared_disk",
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    op.drop_column(table_name, "use_llm")
    op.drop_column(table_name, "prompt")
    op.drop_column(table_name, "created_utc")
    op.drop_column("cmf_shared_disk", "created_utc")
