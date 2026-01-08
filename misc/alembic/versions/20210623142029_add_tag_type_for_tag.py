"""add tag_type for tag

Revision ID: a24763642fae
Revises: 8862369e9654
Create Date: 2021-06-23 14:20:29.751523

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a24763642fae"
down_revision = "8862369e9654"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tag", sa.Column("tag_type", sa.Integer, nullable=False))


def downgrade():
    op.drop_column("tag", "tag_type")
