"""add_sysfrom_to_file

Revision ID: b5363c168591
Revises: 879736f1b4a7
Create Date: 2022-12-14 15:38:19.731926

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b5363c168591"
down_revision = "879736f1b4a7"
branch_labels = None
depends_on = None
table = "file"


def upgrade():
    op.add_column(table, sa.Column("sysfrom", sa.String(255), index=True))


def downgrade():
    op.drop_column(table, "sysfrom")
