"""add table hkex_share_purchase_report

Revision ID: 089302ccaa6f
Revises: caf98f4af2a0
Create Date: 2018-11-02 14:39:13.737240

"""

import json

from alembic import op

# revision identifiers, used by Alembic.
revision = "089302ccaa6f"
down_revision = "caf98f4af2a0"
branch_labels = None
depends_on = None
table_name = "hkex_share_purchase_report"


def _add_comment(col, comment):
    col = "{}.{}".format(table_name, col)
    if isinstance(comment, list):
        comment = json.dumps(comment)
    op.execute("""COMMENT ON COLUMN {} IS '{}'""".format(col, comment))


def upgrade():
    pass


def downgrade():
    pass
