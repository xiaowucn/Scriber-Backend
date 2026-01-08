"""add_fields_for_cgs_rule

Revision ID: 74e81916325f
Revises: 1f98e63f9085
Create Date: 2025-04-18 15:34:41.492930

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field

# revision identifiers, used by Alembic.
revision = "74e81916325f"
down_revision = "1f98e63f9085"
branch_labels = None
depends_on = None

CGS_RULE = "cgs_rule"


def upgrade():
    op.add_column(CGS_RULE, create_array_field("fields", sa.ARRAY(sa.Text), server_default=sa.text("array[]::text[]")))


def downgrade():
    op.drop_column(CGS_RULE, "fields")
