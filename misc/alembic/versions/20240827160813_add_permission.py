"""add_permission

Revision ID: a075249a7727
Revises: bb3b536b1aca
Create Date: 2024-08-27 16:08:13.770634

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.constants import FeatureSchema
from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "a075249a7727"
down_revision = "bb3b536b1aca"
branch_labels = None
depends_on = None
table = "permission"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("name", sa.String(255), unique=True),
        sa.Column("label", sa.String(255), unique=True),
        sa.Column("description", sa.String(255)),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )

    permissions = []
    feature = FeatureSchema.from_config()
    for perm, info in feature.all_perms.items():
        permissions.append((perm, info["name"], info["definition"]))

    for permission in permissions:
        op.execute(
            f"""
            insert into permission (name, label, description)
            values {permission}
        """
        )


def downgrade():
    op.drop_table(table)
