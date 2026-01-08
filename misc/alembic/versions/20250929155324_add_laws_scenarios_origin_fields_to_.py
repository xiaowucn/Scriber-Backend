"""add laws scenarios origin ids fields to table

Revision ID: b09b415affd9
Revises: a12efbf8a77b
Create Date: 2025-09-29 15:53:24.763625
"""

import sqlalchemy as sa
from alembic import op

from remarkable.db import IS_MYSQL

# revision identifiers, used by Alembic.
revision = "b09b415affd9"
down_revision = "a12efbf8a77b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("law_rules_scenarios", sa.Column("order_id", sa.Integer(), index=True))
    op.add_column("law_rules_scenarios", sa.Column("law_id", sa.Integer(), index=True))
    if IS_MYSQL:
        op.execute("""
            UPDATE law_rules_scenarios rs, law_rule lr
            SET rs.order_id = lr.order_id, rs.law_id = lr.law_id
            WHERE rs.rule_id = lr.id
        """)
    else:
        op.execute("""
            UPDATE law_rules_scenarios
            SET order_id = lr.order_id, law_id = lr.law_id
            FROM law_rule lr
            WHERE law_rules_scenarios.rule_id = lr.id
        """)

    op.add_column("law_check_point", sa.Column("law_id", sa.Integer(), index=True))
    if IS_MYSQL:
        op.execute("""
            UPDATE law_check_point lcp, law_rule lr
            SET lcp.law_id = lr.law_id
            WHERE lcp.rule_id = lr.id
        """)
    else:
        op.execute("""
            UPDATE law_check_point
            SET law_id = lr.law_id
            FROM law_rule lr
            WHERE law_check_point.rule_id = lr.id
        """)


def downgrade():
    op.drop_column("law_check_point", "law_id")

    op.drop_column("law_rules_scenarios", "law_id")
    op.drop_column("law_rules_scenarios", "order_id")
