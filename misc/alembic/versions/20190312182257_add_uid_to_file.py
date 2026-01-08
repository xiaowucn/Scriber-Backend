"""add uid to file

Revision ID: afdc6d64506d
Revises: 152dcc8e2ebe
Create Date: 2019-03-12 18:22:57.517659

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "afdc6d64506d"
down_revision = "152dcc8e2ebe"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file", sa.Column("uid", sa.Integer))


def downgrade():
    op.drop_column("file", "uid")
