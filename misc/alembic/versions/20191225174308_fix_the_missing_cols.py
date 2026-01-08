"""Fix the missing cols

Revision ID: ef08a126633a
Revises: 6b7b60c22425
Create Date: 2019-12-25 17:43:08.198049
Possible not applied scripts:
    20190809110135_add_public_property_in_project_and_tree.py
    20190820145906_update_admin_s_default_permission.py
    20190829103715_add_public_to_project.py
"""

import json
import os
import sys

import sqlalchemy as sa
from alembic import op

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from remarkable.common.constants import get_perms

# revision identifiers, used by Alembic.
revision = "ef08a126633a"
down_revision = "6b7b60c22425"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    for table in ("file_project", "file_tree"):
        cols = {col["name"] for col in inspector.get_columns(table)}
        if "uid" in cols:
            continue
        op.add_column(table, sa.Column("uid", sa.Integer, server_default=sa.text("-1")))

    cols = {col["name"] for col in inspector.get_columns("file_project")}
    if "public" not in cols:
        op.add_column("file_project", sa.Column("public", sa.Boolean, server_default=sa.text("true")))
    op.execute("update file_project set public=false where uid != -1")

    perms = [{"perm": perm} for perm in get_perms()]
    op.execute(
        """
        update admin_user
        set permission = '{}'
        where name = 'admin'
    """.format(json.dumps(perms))
    )


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    for table in "file_project", "file_tree":
        cols = {col["name"] for col in inspector.get_columns(table)}
        if "uid" in cols:
            op.drop_column(table, "uid")

        if table == "file_project" and "public" in cols:
            op.drop_column(table, "public")
