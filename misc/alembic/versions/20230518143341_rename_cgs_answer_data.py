"""rename_cgs_answer_data

Revision ID: 56946c390c33
Revises: 61fbd211374e
Create Date: 2023-05-18 14:33:41.115682

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "56946c390c33"
down_revision = "61fbd211374e"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("answer_data")
    op.rename_table("cgs_answer_data", "answer_data")


def downgrade():
    op.rename_table("answer_data", "cgs_answer_data")
    op.create_table("answer_data", sa.Column("id", sa.Integer, nullable=False))
