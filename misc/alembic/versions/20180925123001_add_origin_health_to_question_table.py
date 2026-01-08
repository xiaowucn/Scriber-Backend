"""add origin health to question table

Revision ID: 3f611e20f817
Revises: fcdb529a1781
Create Date: 2018-09-25 12:30:01.242745

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "fe8154a78e36"
down_revision = "8c3c1ec8e62f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("question", sa.Column("origin_health", sa.Integer, nullable=True))
    op.alter_column("question", "status", server_default=sa.text("0"))


def downgrade():
    op.alter_column("question", "status", server_default=sa.text("1"))
    op.drop_column("question", "origin_health")
