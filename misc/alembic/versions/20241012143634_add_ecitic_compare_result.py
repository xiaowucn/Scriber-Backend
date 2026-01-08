"""add_ecitic_compare_result

Revision ID: cf59ca6ae537
Revises: d222a86c4333
Create Date: 2024-10-12 14:36:34.279242

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "cf59ca6ae537"
down_revision = "d222a86c4333"
branch_labels = None
depends_on = None

# Table names as variables
COMPARE_RESULT = "ecitic_compare_result"
COMPARE_RECORD_REF = "ecitic_compare_record_result_ref"


def upgrade():
    op.create_table(
        COMPARE_RESULT,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("is_diff", sa.Boolean, server_default=sa.text("true"), index=True),
        sa.Column("question", sa.JSON, nullable=False),
        sa.Column("std_question", sa.JSON, nullable=False),
        sa.Column("external_source", sa.String(255)),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, nullable=False, server_default=sa.text("0")),
    )

    op.create_table(
        COMPARE_RECORD_REF,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("compare_record_id", sa.Integer),
        sa.Column("compare_result_result_id", sa.Integer),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    op.drop_table(COMPARE_RECORD_REF)
    op.drop_table(COMPARE_RESULT)
