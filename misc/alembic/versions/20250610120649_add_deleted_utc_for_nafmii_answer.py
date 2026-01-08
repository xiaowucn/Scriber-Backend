"""add deleted utc for nafmii answer

Revision ID: db5b1076e57c
Revises: b2b21f0a004a
Create Date: 2025-06-10 12:06:49.361528

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "db5b1076e57c"
down_revision = "b2b21f0a004a"
branch_labels = None
depends_on = None

table_name = "nafmii_file_answer"


def upgrade():
    op.add_column(
        table_name,
        create_timestamp_field("deleted_utc", sa.Integer, server_default=sa.text("0")),
    )


def downgrade():
    op.drop_column(table_name=table_name, column_name="deleted_utc")
