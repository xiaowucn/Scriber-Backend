"""add metadata column for cmf model table

Revision ID: d5cddf48a1e2
Revises: cc79b11be56b
Create Date: 2025-03-17 14:39:56.877363

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field

# revision identifiers, used by Alembic.
revision = "d5cddf48a1e2"
down_revision = "cc79b11be56b"
branch_labels = None
depends_on = None


table_name = "cmf_china_model"


def upgrade():
    op.add_column(table_name, create_jsonb_field("metadata", server_default=sa.text("'{}'::jsonb")))


def downgrade():
    op.drop_column(table_name, "metadata")
