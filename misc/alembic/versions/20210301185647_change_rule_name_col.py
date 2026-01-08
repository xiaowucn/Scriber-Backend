"""Change rule_name col

Revision ID: c272d0ff0a76
Revises: f392233cbb51
Create Date: 2021-03-01 18:56:47.345652

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c272d0ff0a76"
down_revision = "f392233cbb51"
branch_labels = None
depends_on = None
table = "file_meta"


def rename(col, new_col):
    op.drop_index(f"uq_{col}_hash", table)
    op.drop_index(f"ix_{table}_{col}", table)
    op.alter_column(
        table, column_name=col, new_column_name=new_col, existing_type=sa.String(255), existing_nullable=True
    )
    op.create_unique_constraint(f"uq_{new_col}_hash", table, [new_col, "hash"])
    op.create_index(f"ix_{table}_{new_col}", table, [new_col])


def upgrade():
    rename("rule_name", "doc_type")


def downgrade():
    rename("doc_type", "rule_name")
