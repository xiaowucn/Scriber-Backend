"""add_field_contract_content_to_result

Revision ID: f72e7760dea3
Revises: 375ec09b2ff6
Create Date: 2023-08-15 15:06:05.184051

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f72e7760dea3"
down_revision = "375ec09b2ff6"
branch_labels = None
depends_on = None

table = "cgs_result"


def upgrade():
    op.add_column(table, sa.Column("contract_content", sa.Text))


def downgrade():
    op.drop_column(table, "contract_content")
