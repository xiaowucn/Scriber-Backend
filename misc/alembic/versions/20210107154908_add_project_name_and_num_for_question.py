"""add project_name and num for question

Revision ID: da53f64d93d3
Revises: 2abae5e447f2
Create Date: 2021-01-07 15:49:08.494110

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "da53f64d93d3"
down_revision = "2abae5e447f2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("question", sa.Column("name", sa.String(255), nullable=True))
    op.add_column("question", sa.Column("num", sa.String(255), nullable=True))
    op.add_column("question", sa.Column("fill_in_status", sa.Integer, nullable=True))
    op.add_column("question", sa.Column("progress", sa.String(255), nullable=True))
    op.add_column("question", sa.Column("data_updated_utc", sa.Integer, nullable=True))
    op.add_column("question", sa.Column("fill_in_user", sa.String(255), nullable=True))

    op.execute(""" CREATE INDEX idx_question_name ON question (name); """)
    op.execute(""" CREATE INDEX idx_question_num ON question (num); """)
    op.execute(""" CREATE INDEX idx_question_fill_in_status ON question (fill_in_status); """)


def downgrade():
    op.drop_index("idx_question_name", table_name="question")
    op.drop_index("idx_question_num", table_name="question")
    op.drop_index("idx_question_fill_in_status", table_name="question")
    op.drop_column("question", "fill_in_user")
    op.drop_column("question", "data_updated_utc")
    op.drop_column("question", "progress")
    op.drop_column("question", "fill_in_status")
    op.drop_column("question", "num")
    op.drop_column("question", "name")
