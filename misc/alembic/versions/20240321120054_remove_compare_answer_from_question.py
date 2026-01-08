"""remove compare_answer from question

Revision ID: 62170ff57718
Revises: 47b6faeaeded
Create Date: 2024-03-21 12:00:54.909621

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field

from remarkable.common.migrate_util import create_jsonb_field

# revision identifiers, used by Alembic.
revision = "62170ff57718"
down_revision = "47b6faeaeded"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("question", "compare_answer")


def downgrade():
    op.add_column("question", create_jsonb_field("compare_answer", nullable=True, server_default=sa.text("'{}'")))
