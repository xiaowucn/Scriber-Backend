"""add_file_count_to_accuracy_record

Revision ID: ba47352a89be
Revises: bdc0cb71e7ca
Create Date: 2018-12-20 11:31:48.484894

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ba47352a89be"
down_revision = "bdc0cb71e7ca"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("accuracy_record", sa.Column("file_count", sa.Integer, default=0))


def downgrade():
    op.drop_column("accuracy_record", "file_count")
