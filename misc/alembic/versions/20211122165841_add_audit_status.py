"""add audit_status

Revision ID: b5fd9af58c67
Revises: 29b55a7b76a3
Create Date: 2021-11-22 16:58:41.326794

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "b5fd9af58c67"
down_revision = "29b55a7b76a3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cgs_audit_status",
        sa.Column("id", sa.Integer, primary_key=True),
        create_timestamp_field(
            "created_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
        sa.Column("status", sa.Integer),
        sa.Column("fid", sa.Integer),
        sa.Column("schema_id", sa.Integer),
    )


def downgrade():
    op.drop_table("cgs_audit_status")
