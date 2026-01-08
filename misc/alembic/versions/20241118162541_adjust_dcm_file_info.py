"""adjust_dcm_file_info

Revision ID: 5cc2d31f1051
Revises: f0f72bef6653
Create Date: 2024-11-18 16:25:41.744087

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5cc2d31f1051"
down_revision = "f0f72bef6653"
branch_labels = None
depends_on = None
table = "dcm_file_info"
col = "email_sent_at"


def upgrade():
    op.alter_column(table, col, type_=sa.Integer, postgresql_using=f"{col}::integer", existing_type=sa.String(255))


def downgrade():
    op.alter_column(
        table, col, type_=sa.String(255), postgresql_using=f"{col}::character varying", existing_type=sa.Integer
    )
