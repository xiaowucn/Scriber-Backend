"""add label

Revision ID: 29b55a7b76a3
Revises: 94127c38ea57
Create Date: 2021-11-22 11:20:17.253797

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "29b55a7b76a3"
down_revision = "94127c38ea57"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cgs_result", sa.Column("is_edited", sa.Boolean, server_default=sa.text("false")))
    op.add_column("cgs_result", sa.Column("label", sa.String(255)))


def downgrade():
    op.drop_column("cgs_result", "is_edited")
    op.drop_column("cgs_result", "label")
