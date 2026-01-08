"""drop callback col from rule_doc table

Revision ID: 3bcd23e18964
Revises: 6b6cce4aa98c
Create Date: 2019-04-09 11:09:26.149936

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3bcd23e18964"
down_revision = "6b6cce4aa98c"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("rule_doc", "callback")


def downgrade():
    op.add_column("rule_doc", sa.Column("callback", sa.Text))
