"""add_cmf_china_model_count

Revision ID: 46fd7e0201fc
Revises: 685e3097facb
Create Date: 2025-02-26 10:40:04.351813

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ca181024b2f5"
down_revision = "685e3097facb"
branch_labels = None
depends_on = None


CMF_CHINA_MODEL_USAGE_COUNT = "cmf_china_model_usage_count"


def upgrade():
    op.create_table(
        CMF_CHINA_MODEL_USAGE_COUNT,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("model_id", sa.Integer),
        sa.Column("date", sa.Integer, server_default="0"),
        sa.Column("success_count", sa.Integer, server_default="0"),
        sa.Column("failure_count", sa.Integer, server_default="0"),
    )


def downgrade():
    op.drop_table(CMF_CHINA_MODEL_USAGE_COUNT)
