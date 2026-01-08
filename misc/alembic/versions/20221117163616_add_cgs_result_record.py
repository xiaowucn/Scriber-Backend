"""add_cgs_result_record

Revision ID: e767809d79c8
Revises: b5c207e9eab7
Create Date: 2022-11-17 16:36:16.142330

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "e767809d79c8"
down_revision = "b5c207e9eab7"
branch_labels = None
depends_on = None
table = "cgs_result_record"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, primary_key=True),
        create_timestamp_field(
            "created_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
        sa.Column("result_id", sa.Integer, nullable=False, index=True),
        sa.Column("user_id", sa.Integer, nullable=False, index=True),
        sa.Column("user_name", sa.String(255), nullable=False, index=True),
        sa.Column("is_compliance_from", sa.Boolean),
        sa.Column("is_compliance_to", sa.Boolean),
        sa.Column("suggestion", sa.Text),
        sa.Column("user_reason", sa.Text),
    )


def downgrade():
    op.drop_table(table)
