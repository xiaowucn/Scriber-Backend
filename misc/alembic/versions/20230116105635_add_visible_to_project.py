"""add_visible_to_project

Revision ID: a3f43de76c01
Revises: 5e7dcb5dd300
Create Date: 2023-01-16 10:56:35.836879

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a3f43de76c01"
down_revision = "5e7dcb5dd300"
branch_labels = None
depends_on = None
table = "file_project"


def upgrade():
    op.add_column(table, sa.Column("visible", sa.Boolean, server_default=sa.text("true")))
    op.execute("update file_project set visible=true")


def downgrade():
    op.drop_column(table, "visible")
