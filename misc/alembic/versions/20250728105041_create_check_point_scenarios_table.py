"""create check_point scenarios table

Revision ID: be72f088c336
Revises: 0e8c6392549e
Create Date: 2025-07-28 10:50:41.046908

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field
from remarkable.db import IS_MYSQL

# revision identifiers, used by Alembic.
revision = "be72f088c336"
down_revision = "0e8c6392549e"
branch_labels = None
depends_on = None


table_name = "law_check_points_scenarios"


def upgrade():
    op.create_table(
        table_name,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("cp_id", sa.Integer, nullable=False, index=True),
        sa.Column("scenario_id", sa.Integer, nullable=False, index=True),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
        sa.Column("updated_by_id", sa.Integer),
    )
    if not IS_MYSQL:
        op.execute("""INSERT INTO law_check_points_scenarios (cp_id, scenario_id, updated_by_id)
SELECT
  lcp.id as cp_id,
  lrs.scenario_id,
  lrs.updated_by_id
FROM law_rules_scenarios lrs
JOIN law_check_point lcp ON lcp.rule_id = lrs.rule_id
WHERE lrs.deleted_utc = 0
AND lcp.deleted_utc = 0;
        """)


def downgrade():
    op.drop_table(table_name)
