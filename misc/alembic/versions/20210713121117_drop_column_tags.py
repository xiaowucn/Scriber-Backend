"""drop column tags

Revision ID: 4eb64a978249
Revises: 5c30147b2953
Create Date: 2021-07-13 12:11:17.611850

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field

# revision identifiers, used by Alembic.
revision = "4eb64a978249"
down_revision = "5c30147b2953"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("file", "tags")
    op.drop_column("file_project", "default_tags")
    op.drop_column("question", "tags")


def downgrade():
    op.add_column("file", create_array_field("tags", sa.ARRAY(sa.Integer)))
    op.add_column("file_project", create_array_field("default_tags", sa.ARRAY(sa.Integer)))
    op.add_column("question", create_array_field("tags", sa.ARRAY(sa.Integer)))
