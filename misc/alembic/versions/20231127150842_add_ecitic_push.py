"""add_ecitic_push

Revision ID: 3fbfd10873c5
Revises: 78dcce8e7c39
Create Date: 2023-11-27 15:08:42.390275

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "3fbfd10873c5"
down_revision = "78dcce8e7c39"
branch_labels = None
depends_on = None
table = "ecitic_push"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("template", sa.Integer, nullable=False),
        sa.Column("system", sa.String(255), nullable=False),
        sa.Column("function", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("push_address", sa.String(255), nullable=False),
        sa.Column("uid", sa.Integer, nullable=False),
        sa.Column("enabled", sa.Boolean, server_default=sa.text("false")),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, nullable=False, server_default=sa.text("0")),
    )


def downgrade():
    op.drop_table(table)
