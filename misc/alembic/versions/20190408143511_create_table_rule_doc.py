"""create table rule_doc

Revision ID: 1874b6b6e87f
Revises: c32162744c79
Create Date: 2019-04-08 14:35:11.236787

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "1874b6b6e87f"
down_revision = "c32162744c79"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rule_doc",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("fid", sa.Integer, index=True, nullable=False),
        sa.Column("aid", sa.Integer, index=True, nullable=False),  # autodoc id
        sa.Column("callback", sa.Text),  # callback url
        sa.Column("status", sa.Integer, server_default=sa.text("0")),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
    )


def downgrade():
    op.drop_table("rule_doc")
