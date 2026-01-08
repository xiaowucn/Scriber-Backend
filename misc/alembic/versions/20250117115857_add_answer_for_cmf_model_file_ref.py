"""add_answer_for_cmf_model_file_ref

Revision ID: 59bc90c076b7
Revises: c6b62ef65e7c
Create Date: 2025-01-17 11:58:57.397882

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_timestamp_field

# revision identifiers, used by Alembic.
revision = "59bc90c076b7"
down_revision = "c6b62ef65e7c"
branch_labels = None
depends_on = None

CMF_MODEL_FILE_REF = "cmf_model_file_ref"
CMF_FILED_SCRIPT = "cmf_filed_script"


def upgrade():
    op.add_column(CMF_MODEL_FILE_REF, sa.Column("answer", sa.JSON))
    op.drop_table(CMF_FILED_SCRIPT)
    op.create_table(
        CMF_FILED_SCRIPT,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("context", sa.Text, nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
    )


def downgrade():
    op.drop_column(CMF_MODEL_FILE_REF, "answer")
    op.drop_table(CMF_FILED_SCRIPT)
    op.create_table(
        CMF_FILED_SCRIPT,
        sa.Column("id", sa.Integer, primary_key=True, default=1),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("script", sa.LargeBinary, nullable=False),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::integer")),
    )
    op.create_check_constraint("check_id_is_one", CMF_FILED_SCRIPT, "id = 1")
