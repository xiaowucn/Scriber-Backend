"""add_ccxi_contract

Revision ID: 5b2de24f85f5
Revises: 8de791a44971
Create Date: 2022-01-12 10:02:14.427207

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "5b2de24f85f5"
down_revision = "8de791a44971"
branch_labels = None
depends_on = None
table_name = "ccxi_contract"


def upgrade():
    op.create_table(
        table_name,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("qid", sa.Integer, nullable=False),
        sa.Column("contract_no", sa.String(100)),
        sa.Column("company_name", sa.String(100)),
        sa.Column("project_name", sa.String(100)),
        sa.Column("third_party_name", sa.String(100)),
        sa.Column("area", sa.String(100)),
        sa.Column("variety", sa.String(100)),
        sa.Column("date_signed", sa.Integer),
        create_jsonb_field("meta"),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )

    op.create_index(
        "ccxi_contract_key",
        table_name,
        ["contract_no", "company_name", "project_name", "third_party_name", "area", "variety", "date_signed"],
    )


def downgrade():
    op.drop_table(table_name)
