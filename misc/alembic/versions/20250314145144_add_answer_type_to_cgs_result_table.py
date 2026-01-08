"""add answer type to cgs result table

Revision ID: abca7a9e16d8
Revises: 9820eb5ddafa
Create Date: 2025-03-14 14:51:44.964122

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "abca7a9e16d8"
down_revision = "803454664912"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cgs_result", sa.Column("answer_type", sa.Integer(), nullable=True, server_default=sa.text("1")))


def downgrade():
    op.drop_column("cgs_result", "answer_type")
