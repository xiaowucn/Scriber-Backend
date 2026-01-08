"""count_answer_status

Revision ID: b8a834465a57
Revises: fe8154a78e36
Create Date: 2018-10-08 17:52:46.169722

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b8a834465a57"
down_revision = "d624e5b432f6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "question_result",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("aid", sa.Integer, nullable=False, unique=True),
        sa.Column("correct", sa.Integer, nullable=False),
        sa.Column("incorrect", sa.Integer, nullable=False),
        sa.Column("blank", sa.Integer, nullable=False),
    )


def downgrade():
    op.drop_table("question_result")
