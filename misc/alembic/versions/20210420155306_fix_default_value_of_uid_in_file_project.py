"""fix default value of uid in file_project

Revision ID: 54e66509d704
Revises: 6dea995b45fa
Create Date: 2021-04-20 15:53:06.491926

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "54e66509d704"
down_revision = "6dea995b45fa"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("file_project", "uid", existing_type=sa.Integer, server_default=sa.text("1"))
    op.execute("update file_project set uid=1 where uid = -1 or uid is null")


def downgrade():
    op.alter_column("file_project", "uid", existing_type=sa.Integer, server_default=sa.text("-1"))
