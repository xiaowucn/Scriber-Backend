"""add_record_id_on_zts_project_info

Revision ID: 5bdc11e01f44
Revises: 74d090468da8
Create Date: 2025-01-15 10:26:38.202004

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5bdc11e01f44"
down_revision = "74d090468da8"
branch_labels = None
depends_on = None
table = "zts_project_info"


def upgrade():
    op.add_column(table, sa.Column("record_id", sa.String(32)))


def downgrade():
    op.drop_column(table, "record_id")
