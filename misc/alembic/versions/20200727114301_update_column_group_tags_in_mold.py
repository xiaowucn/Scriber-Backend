"""update column group_tags in mold

Revision ID: c9c14a55e3e5
Revises: 38f90ce9fbcd
Create Date: 2020-07-27 11:43:01.432380

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field

# revision identifiers, used by Alembic.
revision = "c9c14a55e3e5"
down_revision = "38f90ce9fbcd"
branch_labels = None
table = "mold"


def upgrade():
    """
    深交所需求：schema属于某个项目组
    """
    op.drop_column(table, "group_tags")
    op.add_column(table, create_array_field("group_tags", sa.ARRAY(sa.String)))


def downgrade():
    op.drop_column(table, "group_tags")
    op.add_column(table, create_array_field("group_tags", sa.ARRAY(sa.Integer)))
