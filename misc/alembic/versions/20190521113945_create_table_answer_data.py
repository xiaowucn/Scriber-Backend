"""create table answer_data

Revision ID: 033f99cff0b1
Revises: 2e5f528e7713
Create Date: 2019-05-21 11:39:45.833334

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "033f99cff0b1"
down_revision = "2e5f528e7713"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "answer_data",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("fid", sa.Integer, unique=True),
        create_jsonb_field("data"),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )


def downgrade():
    op.drop_table("answer_data")
