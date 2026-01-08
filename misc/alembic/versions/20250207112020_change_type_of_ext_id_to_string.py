"""change type of ext_id to string

Revision ID: f2ceaddf7354
Revises: 875978cc87b2
Create Date: 2025-02-07 11:20:20.745965

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f2ceaddf7354"
down_revision = "875978cc87b2"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("nafmii_file_info", "ext_id", type_=sa.String(255), existing_type=sa.Integer)
    op.add_column("nafmii_file_info", sa.Column("status", sa.Integer, nullable=False, server_default=sa.text("0")))


def downgrade():
    op.drop_column("nafmii_file_info", "status")
    op.alter_column(
        "nafmii_file_info", "ext_id", type_=sa.Integer, existing_type=sa.String(255), postgresql_using="ext_id::integer"
    )
