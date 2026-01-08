"""add_public_to_project

Revision ID: b74ae9de460a
Revises: 9ab671deb36f
Create Date: 2019-08-29 10:37:15.337618

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b74ae9de460a"
down_revision = "9ab671deb36f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file_project", sa.Column("public", sa.Boolean, server_default=sa.text("true")))
    op.execute("update file_project set public=false where uid != -1")


def downgrade():
    op.drop_column("file_project", "public")
