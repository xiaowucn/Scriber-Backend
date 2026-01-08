"""add_status_for_cmf_model_file_ref

Revision ID: 6c46b6121efa
Revises: 59bc90c076b7
Create Date: 2025-01-22 11:38:57.407630

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6c46b6121efa"
down_revision = "59bc90c076b7"
branch_labels = None
depends_on = None

CMF_MODEL_FILE_REF = "cmf_model_file_ref"


def upgrade():
    op.add_column(CMF_MODEL_FILE_REF, sa.Column("status", sa.Integer, server_default=sa.text("0")))


def downgrade():
    op.drop_column(CMF_MODEL_FILE_REF, "status")
