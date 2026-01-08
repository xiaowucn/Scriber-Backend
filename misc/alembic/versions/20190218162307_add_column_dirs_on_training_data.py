"""add column dirs on training_data

Revision ID: 71df5399f3e8
Revises: b136995df8b4
Create Date: 2019-02-18 16:23:07.383553

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field

from remarkable.common.migrate_util import create_array_field

# revision identifiers, used by Alembic.
revision = "71df5399f3e8"
down_revision = "b136995df8b4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("training_data", create_array_field("dirs", sa.ARRAY(sa.Integer)))


def downgrade():
    op.drop_column("training_data", "dirs")
