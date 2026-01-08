"""add index idx_question_fid

Revision ID: 634a0835f729
Revises: 5d179f4f1a6e
Create Date: 2024-05-14 17:13:27.701876

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "634a0835f729"
down_revision = "5d179f4f1a6e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_question_fid", "question", ["fid"])


def downgrade():
    op.drop_index("ix_question_fid", "question")
