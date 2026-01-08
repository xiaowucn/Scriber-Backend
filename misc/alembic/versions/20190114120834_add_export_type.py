"""add_export_type

Revision ID: b9376eed886e
Revises: d3f02bc109c8
Create Date: 2019-01-14 12:08:34.363122

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b9376eed886e"
down_revision = "d3f02bc109c8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("training_data", sa.Column("export_type", sa.String(255), server_default="json"))


def downgrade():
    op.drop_column("training_data", "export_type")
