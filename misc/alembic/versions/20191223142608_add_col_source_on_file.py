"""add col source on file

Revision ID: 496e99fb44c2
Revises: 8d7b566995db
Create Date: 2019-12-23 14:26:08.338228

"""

from alembic import op

from remarkable.common.migrate_util import create_jsonb_field

from remarkable.common.migrate_util import create_jsonb_field

# revision identifiers, used by Alembic.


revision = "496e99fb44c2"
down_revision = "8d7b566995db"
branch_labels = None
depends_on = None
table = "file"


def upgrade():
    op.add_column(table, create_jsonb_field("source"))


def downgrade():
    op.drop_column(table, "source")
