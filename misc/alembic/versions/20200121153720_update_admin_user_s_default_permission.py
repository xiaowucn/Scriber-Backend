"""update admin user's default permission

Revision ID: 7731221ae540
Revises: 2a207911b655
Create Date: 2020-01-21 15:37:20.109485

"""

import json
import os
import sys

from alembic import op

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from remarkable.common.constants import get_perms

# revision identifiers, used by Alembic.
revision = "7731221ae540"
down_revision = "2a207911b655"
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
