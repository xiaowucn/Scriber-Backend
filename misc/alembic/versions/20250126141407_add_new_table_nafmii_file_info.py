"""add new table nafmii_file_info

Revision ID: ae4ca5391dd7
Revises: 6c46b6121efa
Create Date: 2025-01-26 14:14:07.801015

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "ae4ca5391dd7"
down_revision = "6c46b6121efa"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "nafmii_file_info",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("file_id", sa.Integer, nullable=False),
        sa.Column("ext_id", sa.Integer, nullable=True),
        sa.Column("confirm_status", sa.Integer, nullable=False, server_default=sa.text("0")),
        create_array_field("task_types", sa.ARRAY(sa.Text), nullable=True),
        create_array_field("keywords", sa.ARRAY(sa.Text), nullable=True),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
    )
    op.create_index("nafmii_file_info_ext_id_key", "nafmii_file_info", ["ext_id"], unique=True)
    op.create_index("nafmii_file_info_file_id_key", "nafmii_file_info", ["file_id"], unique=True)


def downgrade():
    op.drop_table("nafmii_file_info")
