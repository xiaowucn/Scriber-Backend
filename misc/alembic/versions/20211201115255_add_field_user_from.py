"""add field user from

Revision ID: 8de791a44971
Revises: 468886368ee4
Create Date: 2021-12-01 11:52:55.090422

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field

# revision identifiers, used by Alembic.

revision = "8de791a44971"
down_revision = "468886368ee4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("admin_user", create_jsonb_field("data"))
    op.add_column("admin_user", sa.Column("ext_from", sa.String(255)))


def downgrade():
    op.drop_column("admin_user", "data")
    op.drop_column("admin_user", "ext_from")
