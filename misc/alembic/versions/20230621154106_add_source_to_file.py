"""add_source_to_file

Revision ID: ec171c6ce295
Revises: 152b41b74636
Create Date: 2023-06-21 15:41:06.256145

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ec171c6ce295"
down_revision = "152b41b74636"
branch_labels = None
depends_on = None
table = "file"


def upgrade():
    op.add_column(table, sa.Column("source", sa.String(255), index=True))


def downgrade():
    op.drop_column(table, "source")
