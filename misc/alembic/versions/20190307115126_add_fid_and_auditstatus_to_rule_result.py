"""add_fid_and_auditstatus_to_rule_result

Revision ID: 54337fcafdcd
Revises: c461565ae980
Create Date: 2019-03-07 11:51:26.680478

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "54337fcafdcd"
down_revision = "c461565ae980"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("rule_result", sa.Column("fid", sa.Integer, nullable=False))
    op.add_column("rule_result", sa.Column("audit_status", sa.Integer, nullable=False))


def downgrade():
    op.drop_column("rule_result", "fid")
    op.drop_column("rule_result", "audit_status")
