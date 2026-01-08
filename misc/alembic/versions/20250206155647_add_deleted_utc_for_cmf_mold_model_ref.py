"""add_deleted_utc_for_cmf_mold_model_ref

Revision ID: c14e5ab50f78
Revises: ae4ca5391dd7
Create Date: 2025-02-06 15:56:47.673954

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c14e5ab50f78"
down_revision = "ae4ca5391dd7"
branch_labels = None
depends_on = None

CMF_MOLD_MODEL_REF = "cmf_mold_model_ref"


def upgrade():
    op.add_column(CMF_MOLD_MODEL_REF, sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")))


def downgrade():
    op.drop_column(CMF_MOLD_MODEL_REF, "deleted_utc")
