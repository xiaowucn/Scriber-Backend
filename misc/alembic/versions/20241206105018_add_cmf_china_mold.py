"""add_cmf_china_mold

Revision ID: 6d5d07276c87
Revises: 2ffc42d5b16a
Create Date: 2024-12-06 10:50:18.580634

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "6d5d07276c87"
down_revision = "2ffc42d5b16a"
branch_labels = None
depends_on = None

# Table names as variables
CMF_CHINA_MODEL = "cmf_china_model"


def upgrade():
    op.create_table(
        CMF_CHINA_MODEL,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("mold_id", sa.Integer),
        sa.Column("uid", sa.Integer),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.String(255), nullable=False),
        sa.Column("intro", sa.String(255)),
        sa.Column("usage", sa.String(255)),
        sa.Column("enable", sa.Integer, server_default=sa.text("0")),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
    op.create_index("cmf_china_model_name_key", CMF_CHINA_MODEL, ["name"], unique=True)
    op.create_index("cmf_china_model_address_key", CMF_CHINA_MODEL, ["address"], unique=True)


def downgrade():
    op.drop_table(CMF_CHINA_MODEL)
