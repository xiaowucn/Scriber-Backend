"""add_dcm_project_ref

Revision ID: a09e64768533
Revises: 8579708e1bd4
Create Date: 2024-10-25 14:29:30.936919

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "a09e64768533"
down_revision = "8579708e1bd4"
branch_labels = None
depends_on = None
table = "dcm_project_file_project_ref"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("dcm_project_id", sa.Integer, nullable=False, unique=True),
        sa.Column("file_project_id", sa.Integer, nullable=False, unique=True),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    op.drop_table(table)
