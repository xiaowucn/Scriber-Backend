"""change chapter_answer server default array to dict

Revision ID: 5d179f4f1a6e
Revises: 8c066c56f681
Create Date: 2024-04-28 15:46:16.300264

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from remarkable.db import IS_MYSQL

# revision identifiers, used by Alembic.
revision = "5d179f4f1a6e"
down_revision = "8c066c56f681"
branch_labels = None
depends_on = None
table_name = "chinaamc_compare_task"
column_name = "chapter_answer"


def upgrade():
    if IS_MYSQL:
        return
    op.alter_column(
        table_name,
        column_name,
        type_=JSONB,
        server_default=sa.text("'{}'"),
        existing_server_default=sa.text("'[]'"),
    )
    # 将所有空数组的 chapter_answer 改为 {}
    op.execute(f"UPDATE {table_name} SET {column_name} = '{{}}' WHERE {column_name} = '[]'")


def downgrade():
    if IS_MYSQL:
        return
    op.alter_column(
        table_name,
        column_name,
        type_=JSONB,
        server_default=sa.text("'[]'"),
        existing_server_default=sa.text("'{}'"),
    )
    # 将所有空对象的 chapter_answer 改为 []
    op.execute(f"UPDATE {table_name} SET {column_name} = '[]' WHERE {column_name} = '{{}}'")
