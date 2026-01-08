"""add ai_status to question

Revision ID: fe39b8c4f471
Revises: dea97658a66e
Create Date: 2018-11-02 15:29:25.797704

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "fe39b8c4f471"
down_revision = "dea97658a66e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("question", sa.Column("ai_status", sa.Integer, nullable=True))


def downgrade():
    op.drop_column("question", "ai_status")
