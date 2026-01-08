"""change china stock answer column type

Revision ID: 5cfccf6f540c
Revises: 7eb6f53b8156
Create Date: 2025-08-18 15:29:02.344044

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5cfccf6f540c"
down_revision = "f00934d72b09"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("china_stock_answer", "file_source", type_=sa.Text, existing_type=sa.String(255))
    op.alter_column("china_stock_answer", "product_name", type_=sa.Text, existing_type=sa.String(255))
    op.alter_column("china_stock_answer", "manager_name", type_=sa.Text, existing_type=sa.String(255))


def downgrade():
    pass
