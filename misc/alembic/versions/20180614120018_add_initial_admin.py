"""add initial admin

Revision ID: ca20cb00c91c
Revises: 54c9c565a9f2
Create Date: 2018-06-14 12:00:18.441772

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "ca20cb00c91c"
down_revision = "54c9c565a9f2"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        insert into admin_user (name, password, salt, permission)
        values ('admin', md5('111111'), '',
            '[{"perm": "manage_mold"}, {"perm": "manage_user"}, {"perm": "remark"}, {"perm": "remark_management"}, {"perm": "manage_prj"}, {"perm": "browse"}]')
    """
    )


def downgrade():
    op.execute(
        """
        delete from admin_user where name = 'admin'
    """
    )
