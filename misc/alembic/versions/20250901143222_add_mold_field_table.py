"""add_mold_field_table

Revision ID: 0ab80d4c5b03
Revises: 71999603561c
Create Date: 2025-09-01 14:32:22.220833
"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field, create_jsonb_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "0ab80d4c5b03"
down_revision = "71999603561c"
branch_labels = None
depends_on = None

TABLE_MOLD_FIELD = "mold_field"
TABLE_CMF_MOLD_FIELD_REF = "cmf_mold_field_ref"
TABLE_ANSWER_DATA_STAT = "answer_data_stat"
TABLE_ANSWER_DATA = "answer_data"
TABLE_CGS_RULE = "cgs_rule"
TABLE_CMF_USER_CHECK_FIELDS = "cmf_china_user_check_fields"


def upgrade():
    # 新增字段表
    op.create_table(
        TABLE_MOLD_FIELD,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("mid", sa.Integer),
        sa.Column("uuid", sa.String(32), nullable=False),
        sa.Column("parent", sa.String(32), nullable=True),
        sa.Column("type", sa.String(255), nullable=True),
        sa.Column("alias", sa.String(255), nullable=True),
        sa.Column("words", sa.String(255), nullable=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("required", sa.Boolean, server_default=sa.text("false")),
        sa.Column("multi", sa.Boolean, server_default=sa.text("true")),
        sa.Column("is_leaf", sa.Boolean, server_default=sa.text("false")),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )

    op.create_table(
        TABLE_CMF_MOLD_FIELD_REF,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("mold_field_id", sa.Integer),
        sa.Column("probability", sa.DECIMAL(5, 4), server_default=sa.text("0.9")),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
    op.create_index(
        f"idx_{TABLE_CMF_MOLD_FIELD_REF}_mold_field_id_probability",
        TABLE_CMF_MOLD_FIELD_REF,
        ["mold_field_id", "probability"],
    )

    # 答案统计增加分数字段
    op.add_column(TABLE_ANSWER_DATA_STAT, sa.Column("score", sa.DECIMAL(5, 4)))

    # 答案增加字段ID
    op.add_column(TABLE_ANSWER_DATA_STAT, sa.Column("mold_field_id", sa.Integer))
    op.add_column(TABLE_ANSWER_DATA, sa.Column("mold_field_id", sa.Integer))

    # 规则增加字段ID列表
    op.add_column(
        TABLE_CGS_RULE,
        create_array_field("field_ids", sa.ARRAY(sa.Integer), server_default=sa.text("array[]::integer[]")),
    )

    # 修改用户选择列表
    op.add_column(TABLE_CMF_USER_CHECK_FIELDS, sa.Column("mold_field_id", sa.Integer))
    op.add_column(TABLE_CMF_USER_CHECK_FIELDS, sa.Column("check", sa.Boolean, server_default=sa.text("true")))
    op.drop_column(TABLE_CMF_USER_CHECK_FIELDS, "mold_id")
    op.drop_column(TABLE_CMF_USER_CHECK_FIELDS, "check_fields")


def downgrade():
    op.drop_table(TABLE_MOLD_FIELD)
    op.drop_table(TABLE_CMF_MOLD_FIELD_REF)
    op.drop_column(TABLE_ANSWER_DATA_STAT, "score")
    op.drop_column(TABLE_ANSWER_DATA_STAT, "mold_field_id")
    op.drop_column(TABLE_ANSWER_DATA, "mold_field_id")
    op.drop_column(TABLE_CGS_RULE, "field_ids")

    # 修改用户选择列表
    op.drop_column(TABLE_CMF_USER_CHECK_FIELDS, "mold_field_id")
    op.drop_column(TABLE_CMF_USER_CHECK_FIELDS, "check")
    op.add_column(TABLE_CMF_USER_CHECK_FIELDS, sa.Column("mold_id", sa.Integer))
    op.add_column(TABLE_CMF_USER_CHECK_FIELDS, create_jsonb_field("check_fields"))
