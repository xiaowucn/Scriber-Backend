"""add admin_user.ext_id

Revision ID: aa4caad00967
Revises: b9b246457beb
Create Date: 2021-07-22 14:31:53.222907

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "aa4caad00967"
down_revision = "b9b246457beb"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("admin_user", sa.Column("ext_id", sa.String(255)))
    op.execute("update admin_user set ext_id=name where length(password) = 0")


def downgrade():
    op.drop_column("admin_user", "ext_id")
