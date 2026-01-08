"""add_cgs_answer_data_schema

Revision ID: 84ed15a816fb
Revises: 83d45bb8ac2a
Create Date: 2023-02-14 11:58:15.347143

"""

from alembic import op

from remarkable.common.migrate_util import create_jsonb_field

# revision identifiers, used by Alembic.
revision = "84ed15a816fb"
down_revision = "83d45bb8ac2a"
branch_labels = None
depends_on = None
table = "cgs_answer_data"


def upgrade():
    op.add_column(table, create_jsonb_field("schema"))


def downgrade():
    op.drop_column(table, "schema")
