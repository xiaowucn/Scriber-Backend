"""alter field

Revision ID: 94127c38ea57
Revises: 860331f17514
Create Date: 2021-11-17 11:57:28.108153

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "94127c38ea57"
down_revision = "860331f17514"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("cgs_result", "reason", new_column_name="reasons", existing_type=sa.JSON)


def downgrade():
    op.alter_column("cgs_result", "reasons", new_column_name="reason", existing_type=sa.JSON)
