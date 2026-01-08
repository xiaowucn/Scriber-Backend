"""add answer type to cgs audit_status table

Revision ID: ece56127f917
Revises: 623958a63595
Create Date: 2025-04-11 14:19:39.943513

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ece56127f917"
down_revision = "623958a63595"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "cgs_audit_status", sa.Column("answer_type", sa.Integer(), nullable=True, server_default=sa.text("1"))
    )


def downgrade():
    op.drop_column("cgs_audit_status", "answer_type")
