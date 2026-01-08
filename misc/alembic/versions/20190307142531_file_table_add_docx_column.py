"""file table add docx column

Revision ID: 73352eded5cb
Revises: c461565ae980
Create Date: 2019-03-07 14:25:31.419659

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "73352eded5cb"
down_revision = "c461565ae980"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file", sa.Column("docx", sa.String(32)))


def downgrade():
    op.drop_column("file", "docx")
