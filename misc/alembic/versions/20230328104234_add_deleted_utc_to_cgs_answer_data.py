"""add_deleted_utc_to_cgs_answer_data

Revision ID: 31bbce390d07
Revises: c70c103b2e85
Create Date: 2023-03-28 10:42:34.303774

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "31bbce390d07"
down_revision = "c70c103b2e85"
branch_labels = None
depends_on = None
table = "cgs_answer_data"


def upgrade():
    op.add_column(table, sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")))


def downgrade():
    op.drop_column(table, "deleted_utc")
