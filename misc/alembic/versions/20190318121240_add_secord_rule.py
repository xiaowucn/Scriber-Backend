"""add_secord_rule

Revision ID: 348d87b8d188
Revises: 451abd5fbdd9
Create Date: 2019-03-18 12:12:40.861218

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "348d87b8d188"
down_revision = "451abd5fbdd9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("rule_result", sa.Column("second_rule", sa.String(255)))
    op.add_column("rule_result", sa.Column("detail", sa.JSON))


def downgrade():
    op.drop_column("rule_result", "second_rule")
    op.drop_column("rule_result", "detail")
