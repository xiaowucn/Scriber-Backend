"""add_columns_to_accuracy_record

Revision ID: 7f9b30218e95
Revises: 81e3143aaa23
Create Date: 2019-09-11 11:59:52.393075

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field

from remarkable.common.migrate_util import create_array_field

# revision identifiers, used by Alembic.
revision = "7f9b30218e95"
down_revision = "81e3143aaa23"
branch_labels = None
depends_on = None
table_name = "accuracy_record"


def upgrade():
    op.add_column(table_name, sa.Column("vid", sa.Integer, nullable=True))
    op.add_column(table_name, create_array_field("dirs", sa.ARRAY(sa.Integer), nullable=True))
    op.add_column(table_name, create_array_field("files", sa.ARRAY(sa.Integer), nullable=True))


def downgrade():
    op.drop_column(table_name, "vid")
    op.drop_column(table_name, "dirs")
    op.drop_column(table_name, "files")
