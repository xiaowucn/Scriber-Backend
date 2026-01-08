"""add_mold_public

Revision ID: cd509277737c
Revises: f923170dab2e
Create Date: 2022-09-07 17:16:14.477302

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "cd509277737c"
down_revision = "f923170dab2e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("mold", sa.Column("public", sa.Boolean, server_default=sa.text("true")))
    op.execute("update mold set public=true")


def downgrade():
    op.drop_column("mold", "public")
