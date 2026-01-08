"""add table tag relation

Revision ID: 1eb2ccde9a12
Revises: 4eb64a978249
Create Date: 2021-07-13 14:29:15.033733

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1eb2ccde9a12"
down_revision = "4eb64a978249"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tag_relation",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tag_id", sa.Integer, nullable=False),
        sa.Column("relational_id", sa.Integer, nullable=False),
    )


def downgrade():
    op.drop_table("tag_relation")
