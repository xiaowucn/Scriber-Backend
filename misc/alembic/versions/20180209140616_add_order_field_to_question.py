"""add order field to question

Revision ID: 07a5f9cde54f
Revises: b6531e156c70
Create Date: 2018-02-09 14:06:16.641056

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "07a5f9cde54f"
down_revision = "b6531e156c70"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("question", sa.Column("priority", sa.Integer, index=True, server_default="100"))


def downgrade():
    op.drop_column("question", "priority")
