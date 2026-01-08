"""add compare_status and compare_answer to question

Revision ID: 974e147f86ab
Revises: 4e8758f73e3a
Create Date: 2024-03-19 14:31:57.933584

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field

from remarkable.common.migrate_util import create_jsonb_field

# revision identifiers, used by Alembic.
revision = "974e147f86ab"
down_revision = "4e8758f73e3a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("question", sa.Column("compare_status", sa.Integer, nullable=False, server_default=sa.text("0")))
    op.add_column("question", create_jsonb_field("compare_answer", nullable=True, server_default=sa.text("'{}'")))


def downgrade():
    op.drop_column("question", "compare_status")
    op.drop_column("question", "compare_answer")
