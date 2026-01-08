"""add_answer_data_revise_suggestion

Revision ID: 1cbcb11a92ce
Revises: a573d63e87a8
Create Date: 2023-11-08 12:02:02.845331

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1cbcb11a92ce"
down_revision = "a573d63e87a8"
branch_labels = None
depends_on = None
table = "answer_data"


def upgrade():
    op.add_column(table, sa.Column("revise_suggestion", sa.Boolean, server_default=sa.text("false")))


def downgrade():
    op.drop_column(table, "revise_suggestion")
