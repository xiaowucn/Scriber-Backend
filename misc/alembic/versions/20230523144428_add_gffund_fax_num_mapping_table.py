"""add gffund fax num mapping table

Revision ID: 0267a3a5e25b
Revises: 56946c390c33
Create Date: 2023-05-23 14:44:28.773645

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "0267a3a5e25b"
down_revision = "56946c390c33"
branch_labels = None
depends_on = None
table_name = "gffund_fax_mapping"


def upgrade():
    op.create_table(
        table_name,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("fax", sa.String(255), index=True, unique=True, comment="fax number or email address"),
        create_array_field("model_name", sa.ARRAY(sa.String)),
        create_timestamp_field(
            "created_utc", sa.Integer, nullable=False, server_default=sa.text("extract(EPOCH FROM now())::INTEGER")
        ),
        create_timestamp_field(
            "updated_utc", sa.Integer, nullable=False, server_default=sa.text("extract(EPOCH FROM now())::INTEGER")
        ),
    )


def downgrade():
    op.drop_table(table_name)
