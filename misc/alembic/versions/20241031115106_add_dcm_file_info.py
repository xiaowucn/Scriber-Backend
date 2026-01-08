"""add_dcm_file_info

Revision ID: 1e697d01c76c
Revises: bf0b015ed97a
Create Date: 2024-10-31 11:51:06.601822

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "1e697d01c76c"
down_revision = "bf0b015ed97a"
branch_labels = None
depends_on = None

# Table names as variables
DCM_FILE_INFO = "dcm_file_info"


def upgrade():
    op.create_table(
        DCM_FILE_INFO,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("file_id", sa.Integer, nullable=False, index=True),
        sa.Column("email_sent_at", sa.String(255)),
        sa.Column("email_from", sa.String(255)),
        sa.Column("email_to", sa.String(255)),
        sa.Column("email_screenshot", sa.String(255)),
        sa.Column("fill_status", sa.String(255)),
        sa.Column("browse_status", sa.String(255)),
        sa.Column("edit_status", sa.String(255)),
        sa.Column("investor_name", sa.String(255)),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    op.drop_table(DCM_FILE_INFO)
