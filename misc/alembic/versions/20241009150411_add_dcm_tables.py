"""add_dcm_tables

Revision ID: 648403fcd88b
Revises: 461fbcc6be6a
Create Date: 2024-10-09 15:04:11.729373

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "648403fcd88b"
down_revision = "461fbcc6be6a"
branch_labels = None
depends_on = None

# Table names as variables
DCM_PROJECT = "dcm_project"
DCM_BOND_ORDER = "dcm_bond_order"
DCM_BOND_LIMIT = "dcm_bond_limit"
DCM_UNDER_WRITE_RATE = "dcm_under_write_rate"


def upgrade():
    op.create_table(
        DCM_PROJECT,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("project_id", sa.String(255)),
        sa.Column("publish_start_date", sa.String(255)),
        sa.Column("bond_shortname", sa.String(255)),
        sa.Column("product_id", sa.String(255)),
        sa.Column("project_name", sa.String(255)),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
    op.create_index("dcm_project_project_id_key", DCM_PROJECT, ["project_id"], unique=True)

    op.create_table(
        DCM_BOND_ORDER,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("project_id", sa.String(255)),
        sa.Column("project_name", sa.String(255)),
        sa.Column("publish_start_date", sa.String(255)),
        sa.Column("product_id", sa.String(255)),
        sa.Column("bond_shortname", sa.String(255)),
        sa.Column("order_no", sa.String(255)),
        sa.Column("investor_name", sa.String(255)),
        sa.Column("interest_rate", sa.String(255)),
        sa.Column("base_money", sa.String(255)),
        sa.Column("apply_scale", sa.String(255)),
        sa.Column("base_limit", sa.String(255)),
        sa.Column("scale_limit", sa.String(255)),
        sa.Column("total_amt", sa.String(255)),
        sa.Column("apply_money", sa.String(255)),
        sa.Column("limit_id", sa.String(255)),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
    op.create_index("dcm_bond_order_project_id_key", DCM_BOND_ORDER, ["project_id"], unique=True)

    op.create_table(
        DCM_BOND_LIMIT,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("limit_id", sa.String(255)),
        sa.Column("project_id", sa.String(255)),
        sa.Column("project_name", sa.String(255)),
        sa.Column("publish_start_date", sa.String(255)),
        sa.Column("product_id", sa.String(255)),
        sa.Column("bond_shortname", sa.String(255)),
        sa.Column("order_no", sa.String(255)),
        sa.Column("underwrite_name", sa.String(255)),
        sa.Column("base_money", sa.String(255)),
        sa.Column("scale", sa.String(255)),
        sa.Column("plan_circulation", sa.String(255)),
        sa.Column("book_keeper_id", sa.String(255)),
        sa.Column("order_id", sa.String(255)),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
    op.create_index("dcm_bond_limit_project_id_key", DCM_BOND_LIMIT, ["project_id"], unique=True)

    op.create_table(
        DCM_UNDER_WRITE_RATE,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("project_id", sa.String(255)),
        sa.Column("project_name", sa.String(255)),
        sa.Column("publish_start_date", sa.String(255)),
        sa.Column("underwrite_name", sa.String(255)),
        sa.Column("underwrite_role_code", sa.String(255)),
        sa.Column("entr_name", sa.String(255)),
        sa.Column("underwrite_balance_ratio", sa.String(255)),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
    op.create_index("dcm_under_write_rate_project_id_key", DCM_UNDER_WRITE_RATE, ["project_id"], unique=True)


def downgrade():
    op.drop_table(DCM_UNDER_WRITE_RATE)
    op.drop_table(DCM_BOND_LIMIT)
    op.drop_table(DCM_BOND_ORDER)
    op.drop_table(DCM_PROJECT)
