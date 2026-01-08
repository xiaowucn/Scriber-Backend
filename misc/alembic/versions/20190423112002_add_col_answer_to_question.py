"""add col answer to question

Revision ID: 0a279bc49485
Revises: 82c0b7b52e98
Create Date: 2019-04-23 11:20:02.333365

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0a279bc49485"
down_revision = "c32162744c79"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("question", sa.Column("answer", sa.JSON))


def downgrade():
    op.drop_column("question", "answer")
