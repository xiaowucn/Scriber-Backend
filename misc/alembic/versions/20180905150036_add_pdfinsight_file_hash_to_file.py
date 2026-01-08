"""add pdfinsight file hash to file

Revision ID: a9dc1896d241
Revises: 47c9fab0799f
Create Date: 2018-09-05 15:00:36.992959

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a9dc1896d241"
down_revision = "47c9fab0799f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file", sa.Column("pdfinsight", sa.String(32)))


def downgrade():
    op.drop_column("file", "pdfinsight")
