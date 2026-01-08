"""add_external_source

Revision ID: 461fbcc6be6a
Revises: 61841645f5f7
Create Date: 2024-09-27 12:45:17.852453

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "461fbcc6be6a"
down_revision = "61841645f5f7"
branch_labels = None
depends_on = None
table = "ecitic_file_info"


def upgrade():
    op.add_column(table, sa.Column("external_source", sa.String(255)))


def downgrade():
    op.drop_column(table, "external_source")
