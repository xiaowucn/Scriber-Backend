"""add_training_info_to_mold

Revision ID: bdc0cb71e7ca
Revises: 1c93b2b267e8
Create Date: 2018-12-17 17:31:34.956192

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "bdc0cb71e7ca"
down_revision = "1c93b2b267e8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("mold", sa.Column("last_training_utc", sa.Integer, server_default=sa.text("0")))
    op.add_column("mold", sa.Column("b_training", sa.Integer, server_default=sa.text("0")))


def downgrade():
    op.drop_column("mold", "last_training_utc")
    op.drop_column("mold", "b_training")
