"""add_user_suggestion_to_cgs_result

Revision ID: 9da0ec60ae4e
Revises: e767809d79c8
Create Date: 2022-11-23 15:44:17.854729

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9da0ec60ae4e"
down_revision = "e767809d79c8"
branch_labels = None
depends_on = None
table = "cgs_result"


def upgrade():
    op.add_column(table, sa.Column("suggestion_user", sa.Text))
    op.add_column(table, sa.Column("suggestion_ai", sa.Text))


def downgrade():
    op.drop_column(table, "suggestion_user")
    op.drop_column(table, "suggestion_ai")
