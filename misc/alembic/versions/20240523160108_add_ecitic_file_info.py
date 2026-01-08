"""add_ecitic_file_info

Revision ID: dc9b83265472
Revises: 634a0835f729
Create Date: 2024-05-23 16:01:08.010086

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "dc9b83265472"
down_revision = "634a0835f729"
branch_labels = None
depends_on = None
table = "ecitic_file_info"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("fid", sa.Integer, nullable=False, index=True),
        sa.Column("version", sa.String(255)),
        sa.Column("group_name", sa.String(255), nullable=False),
        create_array_field(
            "templates", sa.ARRAY(sa.Integer), nullable=False, server_default=sa.text("'{}'::integer[]")
        ),
        sa.Column("ecitic_new_file", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("ecitic_stat", sa.Boolean, nullable=False, server_default=sa.text("false")),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    op.drop_table(table)
