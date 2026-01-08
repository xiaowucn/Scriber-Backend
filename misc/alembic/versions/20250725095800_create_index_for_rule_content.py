"""create index for rule content

Revision ID: 18d3cbb79af6
Revises: acc6d6c86727
Create Date: 2025-07-25 09:58:00.685541

"""

# revision identifiers, used by Alembic.
revision = "18d3cbb79af6"
down_revision = "acc6d6c86727"
branch_labels = None
depends_on = None


index_name = "idx_law_rule_normalized_content"
table_name = "law_rule"


def upgrade():
    pass


def downgrade():
    pass
