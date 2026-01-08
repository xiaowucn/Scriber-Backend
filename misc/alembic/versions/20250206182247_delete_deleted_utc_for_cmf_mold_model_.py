"""delete_deleted_utc_for_cmf_mold_model_ref

Revision ID: 875978cc87b2
Revises: c14e5ab50f78
Create Date: 2025-02-06 18:22:47.241842

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "875978cc87b2"
down_revision = "c14e5ab50f78"
branch_labels = None
depends_on = None
CMF_MOLD_MODEL_REF = "cmf_mold_model_ref"


def upgrade():
    op.drop_column(CMF_MOLD_MODEL_REF, "deleted_utc")


def downgrade():
    op.add_column(CMF_MOLD_MODEL_REF, sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")))
