"""add_status_for_training_data

Revision ID: 84095debb368
Revises: 623958a63595
Create Date: 2025-04-14 10:36:08.895169

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "84095debb368"
down_revision = "ece56127f917"
branch_labels = None
depends_on = None

TRAINING_DATA = "training_data"


def upgrade():
    op.add_column(TRAINING_DATA, sa.Column("status", sa.Integer, server_default=sa.text("1")))
    op.execute("""UPDATE training_data set status = 3 where zip_path is not null;""")


def downgrade():
    op.drop_column(TRAINING_DATA, "status")
