"""add answer generator for quetion

Revision ID: 47c9fab0799f
Revises: bf3ca1b73eff
Create Date: 2018-09-03 14:25:24.886554

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "47c9fab0799f"
down_revision = "bf3ca1b73eff"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file_project", sa.Column("preset_answer_model", sa.String(255)))


def downgrade():
    op.drop_column("file_project", "preset_answer_model")
