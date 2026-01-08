"""add_cmf_china_mold_ab_compare

Revision ID: 07f9454f6a82
Revises: 72463ab32507
Create Date: 2025-05-15 10:54:03.936936

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "07f9454f6a82"
down_revision = "72463ab32507"
branch_labels = None
depends_on = None


CMF_AB_COMPARE = "cmf_ab_compare"


def upgrade():
    op.create_table(
        CMF_AB_COMPARE,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("mold_id", sa.Integer, nullable=False),
        sa.Column("url", sa.String(1024), nullable=False, server_default=""),
    )

    op.create_index("idx_cmf_ab_compare_mold_id", CMF_AB_COMPARE, ["mold_id"], unique=True)


def downgrade():
    op.drop_table(CMF_AB_COMPARE)
