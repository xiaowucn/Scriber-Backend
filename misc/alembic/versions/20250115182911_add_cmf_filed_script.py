"""cmf_filed_script

Revision ID: c6b62ef65e7c
Revises: 5bdc11e01f44
Create Date: 2025-01-15 18:29:11.066119

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "c6b62ef65e7c"
down_revision = "5bdc11e01f44"
branch_labels = None
depends_on = None

CMF_FILED_SCRIPT = "cmf_filed_script"


def upgrade():
    op.create_table(
        CMF_FILED_SCRIPT,
        sa.Column("id", sa.Integer, primary_key=True, default=1),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("script", sa.LargeBinary, nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
    )
    op.create_check_constraint("check_id_is_one", CMF_FILED_SCRIPT, "id = 1")


def downgrade():
    op.drop_table(CMF_FILED_SCRIPT)
