"""rename file source to meta_info

Revision ID: 6b7b60c22425
Revises: 496e99fb44c2
Create Date: 2019-12-24 17:00:05.222360

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6b7b60c22425"
down_revision = "496e99fb44c2"
branch_labels = None
depends_on = None
table = "file"


def upgrade():
    op.alter_column(table, "source", existing_type=sa.JSON, new_column_name="meta_info")


def downgrade():
    op.alter_column(table, "meta_info", existing_type=sa.JSON, new_column_name="source")
