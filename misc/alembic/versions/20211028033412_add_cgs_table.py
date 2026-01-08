"""add cgs table

Revision ID: aa280dfe08e0
Revises: f74d5b398afc
Create Date: 2021-10-28 09:24:12.067157

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
from remarkable.common.migrate_util import create_array_field, create_jsonb_field, create_timestamp_field

from remarkable.common.migrate_util import create_timestamp_field, create_jsonb_field, create_array_field

revision = "aa280dfe08e0"
down_revision = "f74d5b398afc"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cgs_rule",
        sa.Column("id", sa.Integer, primary_key=True),
        create_timestamp_field(
            "created_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("validate_company_info", sa.Boolean),
        sa.Column("validate_bond_info", sa.Boolean),
        sa.Column("tip_content", sa.Text),
        sa.Column("is_compliance_tip", sa.Boolean),
        sa.Column("is_noncompliance_tip", sa.Boolean),
        sa.Column("origin_content", sa.Text),
        sa.Column("rule_type", sa.String(255), index=True),
        create_jsonb_field("detail"),
    )

    op.create_table(
        "cgs_result",
        sa.Column("id", sa.Integer, primary_key=True),
        create_timestamp_field(
            "created_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("is_compliance_ai", sa.Boolean),
        sa.Column("is_compliance", sa.Boolean),
        sa.Column("rule_id", sa.Integer),
        create_array_field("origin_contents", sa.ARRAY(sa.String)),
        sa.Column("suggestion", sa.Text),
        sa.Column("rule_type", sa.String(255)),
        create_jsonb_field("reason"),
        sa.Column("tip_content", sa.Text),
        sa.Column("fid", sa.Integer, index=True),
        sa.Column("is_compliance_tip", sa.Boolean),
        sa.Column("is_noncompliance_tip", sa.Boolean),
        sa.Column("qid", sa.Integer, index=True),
        create_jsonb_field("schema_result"),
        sa.Column("order_key", sa.String(255)),
    )


def downgrade():
    op.drop_table("cgs_rule")
    op.drop_table("cgs_result")
