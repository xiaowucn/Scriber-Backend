"""add_question_index

Revision ID: 87401c41e7d7
Revises: d40ae3bae312
Create Date: 2024-09-09 18:24:58.583863

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "87401c41e7d7"
down_revision = "d40ae3bae312"
branch_labels = None
depends_on = None
table = "question"


def upgrade():
    op.create_index("ix_question_mold", table, ["mold"])


def downgrade():
    op.drop_index("ix_question_mold", table)
