"""Change the default file attribute to admin

Revision ID: 451abd5fbdd9
Revises: 817030ae0c71
Create Date: 2019-03-18 10:07:42.870646

"""

from alembic import op

# revision identifiers, used by Alembic.
from sqlalchemy import column, select, table

revision = "451abd5fbdd9"
down_revision = "817030ae0c71"
branch_labels = None
depends_on = None


def upgrade():
    admin = table("admin_user", column("id"), column("name"))
    conn = op.get_bind()
    for row in conn.execute(select([admin.c.id, admin.c.name])):
        if row.name == "admin":
            admin_id = row.id
            break
    else:
        admin_id = 1

    op.execute("UPDATE file SET uid = {} WHERE uid IS NULL".format(admin_id))
    op.create_index("ix_file_uid", "file", ["uid"])


def downgrade():
    op.drop_index("ix_file_uid", "file")
