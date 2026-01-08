"""add_answer_index

Revision ID: bb3b536b1aca
Revises: 87401c41e7d7
Create Date: 2024-09-10 14:46:57.194551

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "bb3b536b1aca"
down_revision = "87401c41e7d7"
branch_labels = None
depends_on = None
table = "answer"


def upgrade():
    op.create_index("ix_answer_standard", table, ["standard"])
    op.create_index("ix_answer_updated_utc", table, ["updated_utc"])


def downgrade():
    op.drop_index("ix_answer_standard", table)
    op.drop_index("ix_answer_updated_utc", table)
