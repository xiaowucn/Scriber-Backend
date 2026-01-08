"""add file id for train data

Revision ID: 8923af538902
Revises: b5363c168591
Create Date: 2022-12-26 10:27:37.892231

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field

# revision identifiers, used by Alembic.
revision = "8923af538902"
down_revision = "b5363c168591"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("training_data", create_array_field("files_ids", sa.ARRAY(sa.Integer)))


def downgrade():
    op.drop_column("training_data", "files_ids")
