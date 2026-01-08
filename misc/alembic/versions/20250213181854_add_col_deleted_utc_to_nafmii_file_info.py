"""add col deleted_utc to nafmii_file_info

Revision ID: 07930e245345
Revises: f2ceaddf7354
Create Date: 2025-02-13 18:18:54.397583

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "07930e245345"
down_revision = "f2ceaddf7354"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("nafmii_file_info", sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0"), nullable=False))


def downgrade():
    op.drop_column("nafmii_file_info", "deleted_utc")
