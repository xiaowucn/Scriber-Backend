"""add_export_path_to_accuracy_record

Revision ID: d3390c44175a
Revises: f72e7760dea3
Create Date: 2023-08-17 15:12:54.860178

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d3390c44175a"
down_revision = "f72e7760dea3"
branch_labels = None
depends_on = None
table = "accuracy_record"


def upgrade():
    op.add_column(table, sa.Column("export_path", sa.String(255)))


def downgrade():
    op.drop_column(table, "export_path")
