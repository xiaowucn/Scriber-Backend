"""add_fid_and_tree_id_in_ccxi_contract

Revision ID: 62887b6e8d97
Revises: 5b2de24f85f5
Create Date: 2022-01-17 11:01:49.003573

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "62887b6e8d97"
down_revision = "5b2de24f85f5"
branch_labels = None
depends_on = None
table_name = "ccxi_contract"


def upgrade():
    op.add_column(table_name, sa.Column("fid", sa.Integer))
    op.add_column(table_name, sa.Column("tree_id", sa.Integer))


def downgrade():
    op.drop_column(table_name, "fid")
    op.drop_column(table_name, "tree_id")
