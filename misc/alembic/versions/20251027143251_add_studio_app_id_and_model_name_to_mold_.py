"""add studio_app_id and model_name to mold table

Revision ID: 5e1cf94c8a96
Revises: b09b415affd9
Create Date: 2025-10-27 14:32:51.409642
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5e1cf94c8a96"
down_revision = "b09b415affd9"
branch_labels = None
depends_on = None

table_name = "mold"
file_table_name = "file"


def upgrade():
    op.add_column(table_name, sa.Column("studio_app_id", sa.String(16), nullable=True))
    op.add_column(table_name, sa.Column("model_name", sa.String(128), nullable=True))
    op.add_column(file_table_name, sa.Column("studio_upload_id", sa.String(16), nullable=True))


def downgrade():
    op.drop_column(table_name, "studio_app_id")
    op.drop_column(table_name, "model_name")
    op.drop_column(file_table_name, "studio_upload_id")
