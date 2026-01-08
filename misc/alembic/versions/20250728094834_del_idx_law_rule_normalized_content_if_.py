"""del idx_law_rule_normalized_content if exists

Revision ID: b3100f27c465
Revises: 74489846dbce
Create Date: 2025-07-28 09:48:34.581496

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b3100f27c465"
down_revision = "74489846dbce"
branch_labels = None
depends_on = None

index_name = "idx_law_rule_normalized_content"
table_name = "law_rule"


def upgrade():
    from remarkable.common.migrate_util import op_drop_index_if_exists

    op_drop_index_if_exists(op, index_name, table_name)


def downgrade():
    pass
