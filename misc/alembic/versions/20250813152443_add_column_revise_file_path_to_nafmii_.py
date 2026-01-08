"""add column revise file path to nafmii_file_info

Revision ID: 7eb6f53b8156
Revises: be72f088c336
Create Date: 2025-08-13 15:24:43.192777

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7eb6f53b8156"
down_revision = "be72f088c336"
branch_labels = None
depends_on = None


table_name = "nafmii_file_info"
column = "revise_file_path"


def upgrade():
    op.add_column(table_name, sa.Column(column, sa.String(255), nullable=True))


def downgrade():
    op.drop_column(table_name, column)
