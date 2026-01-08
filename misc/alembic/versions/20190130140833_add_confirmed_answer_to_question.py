"""add confirmed answer to question

Revision ID: b136995df8b4
Revises: b9376eed886e
Create Date: 2019-01-30 14:08:33.528570

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b136995df8b4"
down_revision = "b9376eed886e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("question", sa.Column("confirmed_answer", sa.JSON))


def downgrade():
    op.drop_column("question", "confirmed_answer")
