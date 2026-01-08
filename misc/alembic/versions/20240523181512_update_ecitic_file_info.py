"""update_ecitic_file_info

Revision ID: cac4de4cc3b0
Revises: dc9b83265472
Create Date: 2024-05-23 18:15:12.938920

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "cac4de4cc3b0"
down_revision = "dc9b83265472"
branch_labels = None
depends_on = None
table = "ecitic_file_info"


def upgrade():
    op.drop_table(table)
    op.create_table(
        table,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("file_id", sa.Integer, nullable=False, index=True),
        sa.Column("version", sa.String(255)),
        sa.Column("batch_no", sa.String(255)),
        sa.Column("group_name", sa.String(255), nullable=False),
        create_array_field(
            "templates", sa.ARRAY(sa.Integer), nullable=False, server_default=sa.text("'{}'::integer[]")
        ),
        sa.Column("is_new_file", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("need_stat", sa.Boolean, nullable=False, server_default=sa.text("false")),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    pass
