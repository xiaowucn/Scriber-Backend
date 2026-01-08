"""create index for law check point

Revision ID: a81d4e12b9e9
Revises: 554f1625ca69
Create Date: 2025-07-08 15:24:21.129070

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "a81d4e12b9e9"
down_revision = "554f1625ca69"
branch_labels = None
depends_on = None


index_name = "ix_law_check_point_rule_id"
index_name2 = "ix_law_check_point_parent_id"
table_name = "law_check_point"
columns = ["rule_id"]
columns2 = ["parent_id"]


def upgrade():
    op.create_index(index_name, table_name, columns)
    op.create_index(index_name2, table_name, columns2)


def downgrade():
    op.drop_index(index_name, table_name)
    op.drop_index(index_name2, table_name)
