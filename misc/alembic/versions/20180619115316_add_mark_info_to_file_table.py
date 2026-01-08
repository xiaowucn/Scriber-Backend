"""add mark info to file table

Revision ID: bf3ca1b73eff
Revises: ca981d513a9f
Create Date: 2018-06-19 11:53:16.597087

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field

# revision identifiers, used by Alembic.
revision = "bf3ca1b73eff"
down_revision = "ca981d513a9f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file", create_array_field("mark_uids", sa.ARRAY(sa.Integer)))
    op.add_column("file", create_array_field("mark_users", sa.ARRAY(sa.String)))
    op.add_column("file", sa.Column("last_mark_utc", sa.Integer))


def downgrade():
    op.drop_column("file", "mark_uids")
    op.drop_column("file", "mark_users")
    op.drop_column("file", "last_mark_utc")
