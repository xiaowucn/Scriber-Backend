"""add new column to nafmii_file_answer
Revision ID: 803454664912
Revises: b570ba455f39
Create Date: 2025-03-13 14:27:59.822757

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_jsonb_field

# revision identifiers, used by Alembic.
revision = "803454664912"
down_revision = "b570ba455f39"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("nafmii_file_answer", create_jsonb_field("diff", server_default=sa.text("'[]'")))
    op.execute("update nafmii_file_answer set diff = answer where answer != diff;")
    op.drop_column("nafmii_file_answer", "answer")

    op.add_column("nafmii_file_answer", create_jsonb_field("sensitive_word", server_default=sa.text("'[]'")))
    op.add_column("nafmii_file_answer", create_jsonb_field("keyword", server_default=sa.text("'[]'")))
    op.drop_column("nafmii_file_answer", "schema")


def downgrade():
    op.add_column("nafmii_file_answer", create_jsonb_field("answer", server_default=sa.text("'[]'")))
    op.execute("update nafmii_file_answer set answer = diff where answer != diff;")
    op.drop_column("nafmii_file_answer", "diff")

    op.drop_column("nafmii_file_answer", "sensitive_word")
    op.drop_column("nafmii_file_answer", "keyword")
    op.add_column("nafmii_file_answer", create_jsonb_field("schema", server_default=sa.text("'[]'")))
