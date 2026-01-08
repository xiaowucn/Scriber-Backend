"""add group_tag in mold

Revision ID: 38f90ce9fbcd
Revises: 960aace38f4d
Create Date: 2020-07-21 15:29:01.494804

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field

# revision identifiers, used by Alembic.
revision = "38f90ce9fbcd"
down_revision = "960aace38f4d"
branch_labels = None
depends_on = None
table = "mold"


def upgrade():
    """
    深交所需求：schema属于某个项目组
    """
    op.add_column(table, create_array_field("group_tags", sa.ARRAY(sa.Integer)))


def downgrade():
    op.drop_column(table, "group_tags")
