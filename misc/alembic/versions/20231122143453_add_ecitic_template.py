"""add_ecitic_template

Revision ID: 78dcce8e7c39
Revises: 55120af0681e
Create Date: 2023-11-22 14:34:53.789384

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "78dcce8e7c39"
down_revision = "55120af0681e"
branch_labels = None
depends_on = None
table = "ecitic_template"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("business_group", sa.String(255), nullable=False),
        sa.Column("mold", sa.Integer, nullable=False),
        sa.Column("fields", sa.JSON, nullable=False),
        sa.Column("uid", sa.Integer, nullable=False),
        sa.Column("is_default", sa.Boolean, server_default=sa.text("false")),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, nullable=False, server_default=sa.text("0")),
    )


def downgrade():
    op.drop_table(table)
