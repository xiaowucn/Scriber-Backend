"""add_cgs_answer_data

Revision ID: 83d45bb8ac2a
Revises: 0651c57946f2
Create Date: 2023-02-06 18:11:40.963192

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field, create_jsonb_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "83d45bb8ac2a"
down_revision = "0651c57946f2"
branch_labels = None
depends_on = None
table = "cgs_answer_data"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("qid", sa.Integer, index=True),
        sa.Column("uid", sa.Integer),
        sa.Column("key", sa.String(255)),
        create_jsonb_field("data"),
        create_array_field("value", sa.ARRAY(sa.String)),
        sa.Column("score", sa.String(255)),
        create_jsonb_field("record"),
        create_timestamp_field(
            "created_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
        ),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
    op.create_index("qid_key", table, ["qid", "key"], unique=True)


def downgrade():
    op.drop_table(table)
