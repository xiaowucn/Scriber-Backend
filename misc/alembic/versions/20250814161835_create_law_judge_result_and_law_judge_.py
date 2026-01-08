"""create law_judge_result and law_judge_result_record tables

Revision ID: f00934d72b09
Revises: 7eb6f53b8156
Create Date: 2025-08-14 16:18:35.879596

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "f00934d72b09"
down_revision = "7eb6f53b8156"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "law_judge_result",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255)),
        sa.Column("is_compliance", sa.Boolean, nullable=True),
        sa.Column("is_compliance_ai", sa.Boolean, nullable=True),
        sa.Column("is_compliance_user", sa.Boolean, nullable=True),
        sa.Column("is_edited", sa.Boolean, default=False, nullable=True),
        sa.Column("is_compliance_tip", sa.Boolean, nullable=True),
        sa.Column("is_noncompliance_tip", sa.Boolean, nullable=True),
        sa.Column("tip_content", sa.Text, nullable=True),
        sa.Column("order_key", sa.String(255), nullable=True),
        create_array_field("origin_contents", sa.ARRAY(sa.String), nullable=True),
        sa.Column("contract_content", sa.Text, nullable=True),
        sa.Column("reasons", sa.JSON, nullable=True),
        sa.Column("related_name", sa.Text, nullable=True),
        sa.Column("rule_type", sa.String(255), nullable=True),
        sa.Column("schema_results", sa.JSON, nullable=True),
        sa.Column("suggestion", sa.Text, nullable=True),
        sa.Column("suggestion_ai", sa.Text, nullable=True),
        sa.Column("suggestion_user", sa.Text, nullable=True),
        sa.Column("user_reason", sa.Text, nullable=True),
        sa.Column("file_id", sa.Integer),
        sa.Column("law_order_id", sa.Integer),
        sa.Column("rule_id", sa.Integer),
        sa.Column("cp_id", sa.Integer),
        sa.Column("judge_status", sa.SmallInteger, server_default=sa.text("0")),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
    op.create_index("idx_law_judge_result_file_id_cp_id", "law_judge_result", ["file_id", "cp_id"])

    op.create_table(
        "law_judge_result_record",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("result_id", sa.Integer, index=True),
        sa.Column("user_id", sa.Integer),
        sa.Column("is_compliance_from", sa.Boolean, nullable=True),
        sa.Column("is_compliance_to", sa.Boolean, nullable=True),
        sa.Column("suggestion", sa.Text, nullable=True),
        sa.Column("user_reason", sa.Text, nullable=True),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    op.drop_table("law_judge_result_record")
    op.drop_table("law_judge_result")
