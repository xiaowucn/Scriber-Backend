"""update admin user permission

Revision ID: 2a207911b655
Revises: ef08a126633a
Create Date: 2020-01-06 17:01:31.911260

"""

import json
import os
import sys

from alembic import op

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from remarkable.common.constants import get_perms

# revision identifiers, used by Alembic.
revision = "2a207911b655"
down_revision = "ef08a126633a"
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
