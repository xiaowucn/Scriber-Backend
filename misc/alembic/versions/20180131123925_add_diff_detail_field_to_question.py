"""add diff_detail field to question

Revision ID: b6531e156c70
Revises: 8f08a5390eca
Create Date: 2018-01-31 12:39:25.084755

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b6531e156c70"
down_revision = "8f08a5390eca"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("question", sa.Column("diff_detail", postgresql.JSON))


def downgrade():
    op.drop_column("question", "diff_detail")
