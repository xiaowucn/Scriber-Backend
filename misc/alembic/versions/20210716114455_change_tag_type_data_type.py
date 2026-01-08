"""change tag type data type

Revision ID: b9b246457beb
Revises: efc5e7a4d7b4
Create Date: 2021-07-16 11:44:55.909254

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b9b246457beb"
down_revision = "efc5e7a4d7b4"
branch_labels = None
depends_on = None
table = "tag"
col = "tag_type"


def upgrade():
    op.alter_column(table, col, type_=sa.Integer, postgresql_using=f"{col}::integer", nullable=False)


def downgrade():
    pass
