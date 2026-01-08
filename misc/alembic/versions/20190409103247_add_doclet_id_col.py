"""add doclet_id col

Revision ID: 6b6cce4aa98c
Revises: 1874b6b6e87f
Create Date: 2019-04-09 10:32:47.626336

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6b6cce4aa98c"
down_revision = "1874b6b6e87f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("rule_doc", sa.Column("doclet_id", sa.Integer, index=True))


def downgrade():
    op.drop_column("rule_doc", "doclet_id")
