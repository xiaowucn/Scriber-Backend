"""add_ecitic_push_record_compare_record

Revision ID: 53a15e5b6555
Revises: 53584c2a771b
Create Date: 2024-04-07 12:30:07.841506

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "53a15e5b6555"
down_revision = "53584c2a771b"
branch_labels = None
depends_on = None
table = "ecitic_push_record"


def upgrade():
    op.add_column(table, sa.Column("compare_record", sa.Integer, nullable=True, index=True))


def downgrade():
    op.drop_column(table, "compare_record")
