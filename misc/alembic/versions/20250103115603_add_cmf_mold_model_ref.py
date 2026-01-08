"""add_cmf_mold_model_ref

Revision ID: 74d090468da8
Revises: c1679c51a5d8
Create Date: 2025-01-03 11:56:03.487272

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "74d090468da8"
down_revision = "c1679c51a5d8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cmf_mold_model_ref",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("mold_id", sa.Integer, nullable=False),
        sa.Column("model_id", sa.Integer, nullable=False),
        sa.Column("enable", sa.Boolean, server_default=sa.text("false")),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
    )
    op.create_unique_constraint("cmf_mold_model_ref_unique", "cmf_mold_model_ref", ["mold_id", "model_id"])
    op.drop_column("cmf_china_model", "mold_id")
    op.drop_column("cmf_china_model", "enable")


def downgrade():
    op.drop_table("cmf_mold_model_ref")
    op.add_column("cmf_china_model", sa.Column("mold_id", sa.Integer))
    op.add_column("cmf_china_model", sa.Column("enable", sa.Integer))
