"""add cmf model audit accuracy table

Revision ID: cc79b11be56b
Revises: abca7a9e16d8
Create Date: 2025-03-15 12:20:25.275610

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field

# revision identifiers, used by Alembic.
revision = "cc79b11be56b"
down_revision = "abca7a9e16d8"
branch_labels = None
depends_on = None

table_name = "cmf_model_audit_accuracy"


def upgrade():
    op.create_table(
        table_name,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("model_id", sa.Integer, nullable=False),
        sa.Column("date", sa.Integer, nullable=False, index=True),
        create_jsonb_field("molds_rate"),
    )


def downgrade():
    op.drop_table(table_name)
