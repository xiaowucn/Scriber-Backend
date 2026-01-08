"""add_role

Revision ID: f4fdc6836807
Revises: a075249a7727
Create Date: 2024-08-27 16:53:41.593570

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "f4fdc6836807"
down_revision = "a075249a7727"
branch_labels = None
depends_on = None
table = "role"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("name", sa.String(255), unique=True),
        sa.Column("description", sa.String(255)),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )

    roles = [
        ("普通用户", "普通用户"),
        ("管理员", "管理员"),
    ]

    for role in roles:
        op.execute(
            f"""
            insert into role (name, description)
            values {role}
        """
        )


def downgrade():
    op.drop_table(table)
