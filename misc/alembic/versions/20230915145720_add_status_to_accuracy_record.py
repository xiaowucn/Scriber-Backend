"""add_status_to_accuracy_record

Revision ID: 67ff4da56196
Revises: d3390c44175a
Create Date: 2023-09-15 14:57:20.176272

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "67ff4da56196"
down_revision = "d3390c44175a"
branch_labels = None
depends_on = None
table = "accuracy_record"


def upgrade():
    op.add_column(table, sa.Column("status", sa.String(255)))


def downgrade():
    op.drop_column(table, "status")
