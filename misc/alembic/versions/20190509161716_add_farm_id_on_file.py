"""add_farm_id_on_file

Revision ID: 2e5f528e7713
Revises: 614f837441a0
Create Date: 2019-05-09 16:17:16.966779

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2e5f528e7713"
down_revision = "614f837441a0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file", sa.Column("farm_id", sa.Integer))


def downgrade():
    op.drop_column("file", "farm_id")
