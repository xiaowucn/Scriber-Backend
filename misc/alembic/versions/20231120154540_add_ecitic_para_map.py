"""add_ecitic_para_map

Revision ID: 55120af0681e
Revises: 1cbcb11a92ce
Create Date: 2023-11-20 15:45:40.163956

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "55120af0681e"
down_revision = "1cbcb11a92ce"
branch_labels = None
depends_on = None
table = "ecitic_para_map"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("category", sa.String(255), nullable=False),
        sa.Column("field", sa.String(255), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("group_name", sa.String(255), nullable=False),
        create_array_field("values", sa.ARRAY(sa.String), nullable=False),
        sa.Column("to_value", sa.String(255), nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, nullable=False, server_default=sa.text("0")),
    )
    op.create_index(
        "uix_field_group_name",
        table,
        ["field", "group_name"],
        postgresql_where=sa.text(f"{table}.deleted_utc = 0"),
        unique=True,
    )


def downgrade():
    op.drop_table(table)
