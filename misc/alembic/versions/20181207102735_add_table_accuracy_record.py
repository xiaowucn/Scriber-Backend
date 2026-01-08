"""add table accuracy_record

Revision ID: 19130ed7c980
Revises: 33593585bb7c
Create Date: 2018-12-07 10:27:35.392599

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "19130ed7c980"
down_revision = "33593585bb7c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "accuracy_record",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("type", sa.Integer, nullable=False),
        sa.Column("test", sa.Integer, nullable=False),
        sa.Column("data", sa.JSON, nullable=False),
        create_timestamp_field(
            "created_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
    )


def downgrade():
    op.drop_table("accuracy_record")
