"""update result

Revision ID: 941c0ed9fac3
Revises: e19465080dd7
Create Date: 2021-11-12 15:44:18.469906

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "941c0ed9fac3"
down_revision = "e19465080dd7"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("cgs_result", "schema_result", new_column_name="schema_results", existing_type=sa.JSON)


def downgrade():
    op.alter_column("cgs_result", "schema_results", new_column_name="schema_result", existing_type=sa.JSON)
