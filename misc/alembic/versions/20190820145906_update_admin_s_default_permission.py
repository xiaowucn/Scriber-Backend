"""update admin's default permission

Revision ID: 9ab671deb36f
Revises: 8d3dd1c34700
Create Date: 2019-08-20 14:59:06.520650

"""

import json
import os
import sys

from alembic import op

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from remarkable.common.constants import get_perms

# revision identifiers, used by Alembic.
revision = "9ab671deb36f"
down_revision = "8d3dd1c34700"
branch_labels = None
depends_on = None


def upgrade():
    perms = [{"perm": perm} for perm in get_perms()]
    op.execute(
        """
        update admin_user
        set permission = '{}'
        where name = 'admin'
    """.format(json.dumps(perms))
    )


def downgrade():
    pass
