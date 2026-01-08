"""add new table nafmii_system

Revision ID: 7b921476063f
Revises: 260db1e01a54
Create Date: 2025-02-17 15:03:25.430118

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "7b921476063f"
down_revision = "260db1e01a54"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "nafmii_system",
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("registry", sa.String(255), nullable=False),
        sa.Column("partner_id", sa.String(1024), nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
    )

    op.drop_index("nafmii_file_info_ext_id_key", "nafmii_file_info")
    op.add_column("nafmii_file_info", sa.Column("ext_path", sa.String(1024), nullable=True))
    op.add_column("nafmii_file_info", sa.Column("sys_id", sa.Integer, nullable=True, index=True))
    op.add_column("nafmii_file_info", sa.Column("org_name", sa.String(255), nullable=True))
    op.add_column("nafmii_file_info", sa.Column("org_code", sa.String(255), nullable=True))


def downgrade():
    op.drop_column("nafmii_file_info", "org_code")
    op.drop_column("nafmii_file_info", "org_name")
    op.drop_column("nafmii_file_info", "sys_id")
    op.drop_column("nafmii_file_info", "ext_path")
    op.create_index("nafmii_file_info_ext_id_key", "nafmii_file_info", ["ext_id"], unique=True)
    op.drop_table("nafmii_system")
