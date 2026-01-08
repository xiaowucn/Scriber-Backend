"""add_file_info_for_cmf_model_file_ref

Revision ID: 3722ff5b71ff
Revises: 4ce1e114a324
Create Date: 2024-12-09 11:39:38.968513

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3722ff5b71ff"
down_revision = "4ce1e114a324"
branch_labels = None
depends_on = None

# Table names as variables
CMF_FILED_FILE_INFO = "cmf_filed_file_info"


def upgrade():
    op.add_column(CMF_FILED_FILE_INFO, sa.Column("fail_info", sa.String(1024)))


def downgrade():
    op.drop_column(CMF_FILED_FILE_INFO, "fail_info")
