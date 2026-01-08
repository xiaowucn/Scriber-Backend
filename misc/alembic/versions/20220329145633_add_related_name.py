"""add related_name

Revision ID: e77239064967
Revises: 62887b6e8d97
Create Date: 2022-03-29 14:56:33.781357

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e77239064967"
down_revision = "62887b6e8d97"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cgs_result", sa.Column("related_name", sa.Text))
    op.execute("update cgs_result set related_name=name;")


def downgrade():
    op.drop_column("cgs_result", "related_name")
