"""del idx_law_rule_normalized_content

Revision ID: 74489846dbce
Revises: 18d3cbb79af6
Create Date: 2025-07-25 18:05:28.913060

"""

# revision identifiers, used by Alembic.
revision = "74489846dbce"
down_revision = "18d3cbb79af6"
branch_labels = None
depends_on = None


index_name = "idx_law_rule_normalized_content"
table_name = "law_rule"


def upgrade():
    # op.drop_index(index_name, table_name, if_exists=True)
    pass


def downgrade():
    pass
