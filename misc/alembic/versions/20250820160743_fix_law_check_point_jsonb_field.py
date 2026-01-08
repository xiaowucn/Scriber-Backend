"""fix law_check_point jsonb field

Revision ID: 12a87a40feb7
Revises: 733e791c692c
Create Date: 2025-08-20 16:07:43.250624
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "12a87a40feb7"
down_revision = "733e791c692c"
branch_labels = None
depends_on = None

table_name = "law_judge_result"


def upgrade():
    from remarkable.common.migrate_util import create_jsonb_field

    op.drop_column(table_name, "reasons")
    op.add_column(table_name, create_jsonb_field("reasons", nullable=True))
    op.drop_column(table_name, "schema_results")
    op.add_column(table_name, create_jsonb_field("schema_results", nullable=True))


def downgrade():
    pass
