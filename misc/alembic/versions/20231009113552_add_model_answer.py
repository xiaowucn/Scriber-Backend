"""add_model_answer

Revision ID: a573d63e87a8
Revises: c6902b72220c
Create Date: 2023-10-09 11:35:52.096778

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "a573d63e87a8"
down_revision = "c6902b72220c"
branch_labels = None
depends_on = None
table = "model_answer"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("vid", sa.Integer, index=True),
        sa.Column("qid", sa.Integer),
        create_jsonb_field("data"),
        create_timestamp_field(
            "created_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    op.drop_table(table)
