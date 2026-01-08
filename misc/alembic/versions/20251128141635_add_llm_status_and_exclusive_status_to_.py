"""add llm_status and exclusive_status to question table

Revision ID: 5a719ff283c1
Revises: e6241a0824bf
Create Date: 2025-11-28 14:16:35.689928
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5a719ff283c1"
down_revision = "e6241a0824bf"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("question", sa.Column("llm_status", sa.Integer(), nullable=True))
    op.add_column("question", sa.Column("exclusive_status", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("question", "llm_status")
    op.drop_column("question", "exclusive_status")
