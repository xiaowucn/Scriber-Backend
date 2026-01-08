"""add_note_to_user

Revision ID: 9b95d259cbfb
Revises: ec171c6ce295
Create Date: 2023-06-27 10:54:35.101041

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9b95d259cbfb"
down_revision = "ec171c6ce295"
branch_labels = None
depends_on = None
table = "admin_user"


def upgrade():
    op.add_column(table, sa.Column("note", sa.String(255), index=True))
    op.add_column(table, sa.Column("expired_utc", sa.Integer, server_default=sa.text("0")))


def downgrade():
    op.drop_column(table, "note")
    op.drop_column(table, "expired_utc")
