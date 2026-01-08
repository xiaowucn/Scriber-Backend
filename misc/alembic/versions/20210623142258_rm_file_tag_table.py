"""rm file_tag table

Revision ID: 75dcb6b35025
Revises: a24763642fae
Create Date: 2021-06-23 14:22:58.677851

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "75dcb6b35025"
down_revision = "a24763642fae"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("file_tag")


def downgrade():
    op.create_table(
        "file_tag",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        create_array_field("columns", sa.ARRAY(sa.String)),
        create_timestamp_field(
            "created_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
    )
