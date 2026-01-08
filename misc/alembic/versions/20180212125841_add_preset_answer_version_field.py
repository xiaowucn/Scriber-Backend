"""add preset answer version field

Revision ID: 8ee9b7e4411a
Revises: 07a5f9cde54f
Create Date: 2018-02-12 12:58:41.123571

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8ee9b7e4411a"
down_revision = "07a5f9cde54f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("question", sa.Column("preset_answer_version", sa.String(64)))


def downgrade():
    op.drop_column("question", "preset_answer_version")
